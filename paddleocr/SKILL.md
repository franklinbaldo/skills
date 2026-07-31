---
name: paddleocr
description: Run PaddleOCR on PDFs and images, locally or through the Google Colab CLI. Use when extracting scanned documents to Markdown, choosing between GPU and CPU OCR, benchmarking OCR speed or confidence, or replacing slower generative document OCR with a deterministic pipeline.
---

# PaddleOCR

Extract PDFs and images with PP-OCRv6, preserving the source and reporting the
device, timings, page count, and confidence. Prefer GPU for multi-page work.

## Route the run

1. Check whether a PDF already has a usable text layer. Prefer native
   extraction unless the user explicitly requests OCR.
2. Choose one branch:
   - Local NVIDIA GPU: use `scripts/ocr.py --device gpu:0`.
   - No local GPU and a short document: offer `--device cpu` with a prominent
     warning that CPU is much slower.
   - No local GPU and a multi-page document: prefer
     `scripts/run_colab.sh`, which creates and releases a Colab GPU.
3. Read [references/installation.md](references/installation.md) before the
   local branch or when diagnosing CUDA/package compatibility.

The branch is selected when the device and execution environment are explicit.

## Run through Colab CLI

On Windows, invoke the wrapper from WSL:

```bash
cd /mnt/c/path/to/skills/paddleocr
bash scripts/run_colab.sh /mnt/c/path/document.pdf /mnt/c/path/document-ocr.md
```

Optional variables:

```bash
COLAB_GPU=L4 COLAB_SESSION=paddleocr-job \
  bash scripts/run_colab.sh INPUT.pdf OUTPUT.md
```

The wrapper creates a dedicated VM, installs with `uv`, uploads the source,
runs OCR, downloads Markdown, metrics, and an execution notebook, then stops
the VM even after failure. It does not need Google Drive or a Hugging Face
token.

The setup removes PyTorch only inside that disposable VM because Paddle's CUDA
wheel can replace NCCL with a version incompatible with Colab's preinstalled
PyTorch. Never run `setup_colab_gpu.py` in a shared runtime that still needs
PyTorch.

## Run locally

After installing the matching environment from
[references/installation.md](references/installation.md):

```bash
python scripts/ocr.py INPUT.pdf OUTPUT.md --device gpu:0
```

CPU fallback:

```bash
python scripts/ocr.py INPUT.pdf OUTPUT.md --device cpu
```

Always tell the user before a CPU run that it can be much slower than a Colab
T4, especially for long PDFs. Do not present CPU and GPU timings as a
like-for-like model comparison.

Useful options:

- `--lang pt`: recognition language; Portuguese is the default.
- `--ocr-version PP-OCRv6`: OCR family used by default.
- `--min-confidence 0.0`: omit recognitions below a chosen score.
- `--json-dir DIR`: retain per-page raw PaddleOCR JSON.
- `--warm-benchmark`: run a second pass to measure warm inference.

## Validate the result

Verify all of the following before completion:

1. Output page count matches the input.
2. Markdown is non-empty and has content from the beginning, middle, and end.
3. No page is duplicated or missing.
4. Legal identifiers receive spot checks, especially `§`, `º`, dates, values,
   and Roman numerals such as `II` versus `Il`.
5. Report device, initialization time, total inference time, mean time per
   page, and output paths.

Confidence scores are diagnostic, not proof of textual accuracy. For legal or
official documents, describe the output as OCR pending comparison with the
authoritative source.
