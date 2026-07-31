#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash run_colab.sh INPUT.{pdf,png,jpg,...} [OUTPUT.md]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
input_path="$(realpath "$1")"
output_path="${2:-./result.md}"
session_name="${COLAB_SESSION:-paddleocr}"
gpu="${COLAB_GPU:-T4}"
extension=".${input_path##*.}"
remote_input="/content/input/document${extension}"
session_started=false

cleanup() {
  if [[ "$session_started" == true ]]; then
    colab stop -s "$session_name" || true
  fi
}
trap cleanup EXIT

mkdir -p "$(dirname "$output_path")"
colab new -s "$session_name" --gpu "$gpu"
session_started=true

colab exec -s "$session_name" -f "$script_dir/setup_colab_gpu.py" --timeout 1200
colab restart-kernel -s "$session_name"
colab upload -s "$session_name" "$input_path" "$remote_input"
colab exec -s "$session_name" -f "$script_dir/ocr.py" --timeout 1800
colab download -s "$session_name" /content/output/result.md "$output_path"
colab download -s "$session_name" \
  /content/output/result.metrics.json "${output_path%.*}.metrics.json"
colab log -s "$session_name" -o "${output_path%.*}.execution.ipynb"

echo "OCR result: $output_path"
