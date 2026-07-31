#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run_colab.sh INPUT_AUDIO [OUTPUT_PREFIX] [options]

Options:
  --model MODEL           bitnet or full (default: bitnet)
  --gpu GPU               GPU requested for full mode (default: A100)
  --fallback-bitnet       Fall back to BitNet if full allocation/inference fails
  --no-fallback-bitnet    Disable fallback explicitly (the default)
  --session NAME          Colab session name (default: generated)
  --reuse                 Reuse an existing named session
  --keep                  Keep the session after downloads
  --threads N             BitNet inference threads; 0 selects automatically (default: 0)
  --context TEXT          Hotwords/context passed to the selected model
  --max-tokens N          Maximum generated tokens (default: 16384)
  --acoustic-chunk-size N Full-model tokenizer chunk in samples (default: 1440000)
  --upload-format FORMAT  mp3 or original (default: mp3)
  --mp3-bitrate RATE      MP3 bitrate used for upload staging (default: 128k)
  -h, --help              Show this help
USAGE
}

if [[ $# -eq 1 && ( $1 == "-h" || $1 == "--help" ) ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi

input=$1
shift

if [[ ! -f "$input" ]]; then
  echo "Input file not found: $input" >&2
  exit 2
fi

output_prefix="${input%.*}"
if [[ $# -gt 0 && $1 != --* ]]; then
  output_prefix=$1
  shift
fi

model="bitnet"
gpu="A100"
fallback_bitnet=0
session="vibeasr-$(date +%Y%m%d-%H%M%S)-$$"
session_explicit=0
reuse=0
keep=0
threads=0
context=""
max_tokens=16384
acoustic_chunk_size=1440000
upload_format="mp3"
mp3_bitrate="128k"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      [[ $# -ge 2 ]] || { echo "--model requires a value" >&2; exit 2; }
      model=$2
      [[ $model == "bitnet" || $model == "full" ]] || {
        echo "--model must be 'bitnet' or 'full'" >&2
        exit 2
      }
      shift 2
      ;;
    --gpu)
      [[ $# -ge 2 ]] || { echo "--gpu requires a value" >&2; exit 2; }
      gpu=$2
      [[ $gpu =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Invalid --gpu value" >&2; exit 2; }
      shift 2
      ;;
    --fallback-bitnet)
      fallback_bitnet=1
      shift
      ;;
    --no-fallback-bitnet)
      fallback_bitnet=0
      shift
      ;;
    --session)
      [[ $# -ge 2 ]] || { echo "--session requires a value" >&2; exit 2; }
      session=$2
      session_explicit=1
      shift 2
      ;;
    --reuse)
      reuse=1
      shift
      ;;
    --keep)
      keep=1
      shift
      ;;
    --threads)
      [[ $# -ge 2 ]] || { echo "--threads requires a value" >&2; exit 2; }
      threads=$2
      [[ $threads =~ ^[0-9]+$ ]] || { echo "--threads must be a non-negative integer" >&2; exit 2; }
      shift 2
      ;;
    --context)
      [[ $# -ge 2 ]] || { echo "--context requires a value" >&2; exit 2; }
      context=$2
      shift 2
      ;;
    --max-tokens)
      [[ $# -ge 2 ]] || { echo "--max-tokens requires a value" >&2; exit 2; }
      max_tokens=$2
      [[ $max_tokens =~ ^[1-9][0-9]*$ ]] || { echo "--max-tokens must be a positive integer" >&2; exit 2; }
      shift 2
      ;;
    --acoustic-chunk-size)
      [[ $# -ge 2 ]] || { echo "--acoustic-chunk-size requires a value" >&2; exit 2; }
      acoustic_chunk_size=$2
      [[ $acoustic_chunk_size =~ ^[1-9][0-9]*$ ]] || {
        echo "--acoustic-chunk-size must be a positive integer" >&2
        exit 2
      }
      if (( acoustic_chunk_size % 3200 != 0 )); then
        echo "--acoustic-chunk-size must be a multiple of 3200" >&2
        exit 2
      fi
      shift 2
      ;;
    --upload-format)
      [[ $# -ge 2 ]] || { echo "--upload-format requires a value" >&2; exit 2; }
      upload_format=$2
      [[ $upload_format == "mp3" || $upload_format == "original" ]] || {
        echo "--upload-format must be 'mp3' or 'original'" >&2
        exit 2
      }
      shift 2
      ;;
    --mp3-bitrate)
      [[ $# -ge 2 ]] || { echo "--mp3-bitrate requires a value" >&2; exit 2; }
      mp3_bitrate=$2
      [[ $mp3_bitrate =~ ^[0-9]+k$ ]] || {
        echo "--mp3-bitrate must look like 96k or 128k" >&2
        exit 2
      }
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ $reuse -eq 1 && $session_explicit -eq 0 ]]; then
  echo "--reuse requires an explicit --session NAME" >&2
  exit 2
fi

if command -v colab >/dev/null 2>&1; then
  colab_cli() { colab "$@"; }
elif command -v uvx >/dev/null 2>&1; then
  colab_cli() { uvx --from google-colab-cli colab "$@"; }
else
  echo "Neither 'colab' nor 'uvx' is available." >&2
  exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p -- "$(dirname -- "$output_prefix")"

temp_dir=$(mktemp -d)
created=0
cleanup() {
  status=$?
  trap - EXIT INT TERM
  rm -rf -- "$temp_dir"
  if [[ $created -eq 1 && $keep -eq 0 ]]; then
    colab_cli stop -s "$session" >/dev/null 2>&1 || true
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

input_name=$(basename -- "$input")
upload_file=$input
upload_encoding="original"
remote_input=""

lower_name=$(printf '%s' "$input_name" | tr '[:upper:]' '[:lower:]')
if [[ $upload_format == "mp3" ]]; then
  remote_input="/content/vibevoice-input.mp3"
  if [[ $lower_name == *.mp3 ]]; then
    upload_encoding="existing-mp3"
  else
    if ! command -v ffmpeg >/dev/null 2>&1; then
      echo "ffmpeg is required for the default MP3 upload staging." >&2
      echo "Install ffmpeg or pass --upload-format original." >&2
      exit 2
    fi
    upload_file="$temp_dir/vibevoice-upload.mp3"
    ffmpeg -hide_banner -loglevel error -y \
      -i "$input" -vn -ac 1 -ar 24000 \
      -c:a libmp3lame -b:a "$mp3_bitrate" \
      "$upload_file"
    upload_encoding="mp3-${mp3_bitrate}-mono-24khz"
  fi
else
  ext=""
  if [[ $input_name == *.* ]]; then
    raw_ext=${input_name##*.}
    if [[ $raw_ext =~ ^[A-Za-z0-9]+$ ]]; then
      ext=".$raw_ext"
    fi
  fi
  remote_input="/content/vibevoice-input${ext}"
fi

requested_model=$model
effective_model=$model
fallback_reason=""

write_config() {
  local config_file=$1
  local selected_model=$2
  local reason=$3
  python3 - "$config_file" "$remote_input" "$threads" "$context" \
    "$input_name" "$upload_encoding" "$requested_model" "$selected_model" \
    "$reason" "$gpu" "$max_tokens" "$acoustic_chunk_size" <<'PY'
import json
import sys

(
    path,
    audio,
    threads,
    context,
    source_name,
    upload_encoding,
    requested_model,
    effective_model,
    fallback_reason,
    gpu_requested,
    max_tokens,
    acoustic_chunk_size,
) = sys.argv[1:]
config = {
    "audio": audio,
    "threads": int(threads),
    "context": context,
    "greedy": True,
    "source_input_name": source_name,
    "upload_encoding": upload_encoding,
    "model_requested": requested_model,
    "model_effective": effective_model,
    "fallback_reason": fallback_reason or None,
    "gpu_requested": gpu_requested if requested_model == "full" else None,
    "max_tokens": int(max_tokens),
    "acoustic_tokenizer_chunk_size": int(acoustic_chunk_size),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(config, handle, ensure_ascii=False)
PY
}

run_remote_job() {
  local selected_model=$1
  local reason=$2
  local config_file="$temp_dir/job-${selected_model}.json"
  local job_script

  write_config "$config_file" "$selected_model" "$reason" || return $?
  colab_cli upload -s "$session" "$config_file" /content/vibevoice-job.json || return $?
  if [[ $selected_model == "full" ]]; then
    job_script="$script_dir/colab_job_full.py"
  else
    job_script="$script_dir/colab_job_bitnet.py"
  fi
  colab_cli exec -s "$session" -f "$job_script" || return $?
}

if [[ $reuse -eq 0 ]]; then
  if [[ $model == "full" ]]; then
    echo "Requesting Colab GPU: $gpu"
    if colab_cli new -s "$session" --gpu "$gpu"; then
      created=1
    elif [[ $fallback_bitnet -eq 1 ]]; then
      echo "GPU allocation failed; falling back to BitNet on a CPU session." >&2
      colab_cli stop -s "$session" >/dev/null 2>&1 || true
      effective_model="bitnet"
      fallback_reason="gpu-allocation-failed"
      colab_cli new -s "$session"
      created=1
    else
      echo "Unable to allocate GPU '$gpu' for full mode." >&2
      exit 1
    fi
  else
    colab_cli new -s "$session"
    created=1
  fi
else
  colab_cli status -s "$session" >/dev/null
  created=1
fi

printf 'Upload audio: %s (%s)\n' "$upload_file" "$upload_encoding"
colab_cli upload -s "$session" "$upload_file" "$remote_input"

if [[ $effective_model == "full" ]]; then
  if ! run_remote_job "full" ""; then
    if [[ $fallback_bitnet -eq 1 ]]; then
      echo "Full-model job failed; retrying with BitNet in the same session." >&2
      effective_model="bitnet"
      fallback_reason="full-job-failed"
      run_remote_job "bitnet" "$fallback_reason"
    else
      echo "Full-model job failed and fallback is disabled." >&2
      exit 1
    fi
  fi
else
  run_remote_job "bitnet" "$fallback_reason"
fi

colab_cli download -s "$session" \
  /content/vibevoice-transcript.txt "${output_prefix}.txt"
colab_cli download -s "$session" \
  /content/vibevoice-metadata.json "${output_prefix}.metadata.json"
colab_cli download -s "$session" \
  /content/vibevoice-stderr.log "${output_prefix}.stderr.log"

printf 'Requested model: %s\n' "$requested_model"
printf 'Effective model: %s\n' "$effective_model"
if [[ -n $fallback_reason ]]; then
  printf 'Fallback reason: %s\n' "$fallback_reason"
fi
printf 'Transcript: %s\n' "${output_prefix}.txt"
printf 'Metadata:   %s\n' "${output_prefix}.metadata.json"
printf 'Log:        %s\n' "${output_prefix}.stderr.log"
if [[ $keep -eq 1 ]]; then
  printf 'Session kept: %s\n' "$session"
fi
