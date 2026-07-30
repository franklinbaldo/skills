#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run_colab.sh INPUT_AUDIO [OUTPUT_PREFIX] [options]

Options:
  --session NAME   Colab session name (default: generated)
  --reuse          Reuse an existing named session
  --keep           Keep the session after downloads
  --threads N      Inference threads; 0 selects automatically (default: 0)
  --context TEXT   Hotwords/context passed to asr_infer
  -h, --help       Show this help
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

session="vibeasr-$(date +%Y%m%d-%H%M%S)-$$"
session_explicit=0
reuse=0
keep=0
threads=0
context=""

while [[ $# -gt 0 ]]; do
  case "$1" in
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

config_file=$(mktemp)
input_name=$(basename -- "$input")
ext=""
if [[ $input_name == *.* ]]; then
  raw_ext=${input_name##*.}
  if [[ $raw_ext =~ ^[A-Za-z0-9]+$ ]]; then
    ext=".$raw_ext"
  fi
fi
remote_input="/content/vibevoice-input${ext}"

python3 - "$config_file" "$remote_input" "$threads" "$context" <<'PY'
import json
import sys

path, audio, threads, context = sys.argv[1:]
config = {
    "audio": audio,
    "threads": int(threads),
    "context": context,
    "greedy": True,
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(config, handle, ensure_ascii=False)
PY

created=0
cleanup() {
  status=$?
  trap - EXIT INT TERM
  rm -f -- "$config_file"
  if [[ $created -eq 1 && $keep -eq 0 ]]; then
    colab_cli stop -s "$session" >/dev/null 2>&1 || true
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

if [[ $reuse -eq 0 ]]; then
  colab_cli new -s "$session"
  created=1
else
  colab_cli status -s "$session" >/dev/null
  created=1
fi

colab_cli upload -s "$session" "$input" "$remote_input"
colab_cli upload -s "$session" "$config_file" /content/vibevoice-job.json
colab_cli exec -s "$session" -f "$script_dir/colab_job.py"

colab_cli download -s "$session" \
  /content/vibevoice-transcript.txt "${output_prefix}.txt"
colab_cli download -s "$session" \
  /content/vibevoice-metadata.json "${output_prefix}.metadata.json"
colab_cli download -s "$session" \
  /content/vibevoice-stderr.log "${output_prefix}.stderr.log"

printf 'Transcript: %s\n' "${output_prefix}.txt"
printf 'Metadata:   %s\n' "${output_prefix}.metadata.json"
printf 'Log:        %s\n' "${output_prefix}.stderr.log"
if [[ $keep -eq 1 ]]; then
  printf 'Session kept: %s\n' "$session"
fi
