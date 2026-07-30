#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash run_colab_opf.sh INPUT.{md,txt} [OUTPUT_PREFIX]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
input_path="$(realpath "$1")"
input_name="$(basename "$input_path")"
input_stem="${input_name%.*}"
output_prefix="${2:-./$input_stem}"
session_name="${COLAB_SESSION:-opf-anonymization}"
gpu="${COLAB_GPU:-T4}"
session_started=false

case "${input_path##*.}" in
  md|txt) ;;
  *)
    echo "Input must be Markdown or plain text." >&2
    exit 2
    ;;
esac

cleanup() {
  if [[ "$session_started" == true ]]; then
    colab stop -s "$session_name" || true
  fi
}
trap cleanup EXIT

mkdir -p "$(dirname "$output_prefix")"
for suffix in tagged.md anon.md opf-report.json execution.ipynb; do
  if [[ -e "$output_prefix.$suffix" ]]; then
    echo "Refusing to overwrite existing output: $output_prefix.$suffix" >&2
    exit 1
  fi
done

colab new -s "$session_name" --gpu "$gpu"
session_started=true

if [[ "${COLAB_DRIVE_CACHE:-0}" == "1" ]]; then
  colab drivemount -s "$session_name"
fi

colab exec -s "$session_name" \
  -f "$script_dir/setup_colab_opf.py" --timeout 1200
colab restart-kernel -s "$session_name"
colab upload -s "$session_name" \
  "$input_path" "/content/input/$input_name"
colab exec -s "$session_name" \
  -f "$script_dir/anonimizar_opf.py" --timeout 3600
colab download -s "$session_name" \
  "/content/output/$input_stem.tagged.md" "$output_prefix.tagged.md"
colab download -s "$session_name" \
  "/content/output/$input_stem.anon.md" "$output_prefix.anon.md"
colab download -s "$session_name" \
  "/content/output/$input_stem.opf-report.json" "$output_prefix.opf-report.json"
colab log -s "$session_name" -o "$output_prefix.execution.ipynb"

echo "Tagged review copy: $output_prefix.tagged.md"
echo "Anonymized copy: $output_prefix.anon.md"
echo "Redaction report: $output_prefix.opf-report.json"
