---
name: pdf-compression
description: >-
  Optimize and compress large image-heavy or scanned PDFs by downscaling images and re-encoding them using CCITT Group 4 (black and white) or JPEG (grayscale/color).
---

# PDF Compression

## Overview
This skill allows the agent to compress and optimize large, scanned, or image-heavy PDF files. It works by extracting images from the PDF, downscaling them to a reasonable resolution for reading, and re-encoding them with high-efficiency formats (specifically 1-bit CCITT Group 4 TIFF for black & white text, or compressed JPEG for grayscale and color images).

## Quick Start
Run the helper script using `uv run` to compress a PDF. It dynamically installs the required libraries (`pymupdf` and `pillow`) so they don't have to be pre-installed globally.

```bash
uv run --no-project --with pymupdf,pillow <skill-dir>/scripts/compress.py --input <input.pdf> --output <output.pdf> --mode bw
```

> `<skill-dir>` is the directory where this skill was installed from (e.g. `~/skills/pdf-compression`). Run `skills.sh` from the repo root to install with correct paths resolved automatically.

## Utility Scripts

### `compress.py`
The CLI script provides several options to control the compression style and target size:

- `--input` (required): Absolute path to the source PDF file.
- `--output` (required): Absolute path to save the compressed/optimized PDF file.
- `--mode`: The compression algorithm to use:
  - `auto` (default): Automatically detects scanned pages vs. native digital pages. Scanned pages are binarized using `bw` mode (CCITT Group 4) to achieve max compression. Native digital pages preserve color/grayscale images to prevent degradation of charts, logos, and diagrams.
  - `bw`: Converts images to 1-bit Black & White and compresses using CCITT Group 4.
  - `gray`: Converts images to 8-bit grayscale and compresses with JPEG.
  - `color`: Preserves image colors and compresses with JPEG.
- `--max-dim` (default: 1200): Downscale any image whose width or height exceeds this value, maintaining aspect ratio.
- `--quality` (default: 50): JPEG compression quality (1-100) for `gray` and `color` modes.
- `--skip-small` (default: 150): Do not compress images with both dimensions smaller than this threshold (useful to protect logos, icons, and small vector graphics from compression artifacts).

### `split_and_compress.py`
This script splits a large PDF based on its bookmarks (Table of Contents) and compresses each split document. It also includes an automatic rasterization fallback for heavy vector or form-heavy pages that exceed a specific KB-per-page limit.

Options:
- `--input` (required): Absolute path to the source PDF file.
- `--output-dir` (required): Absolute path to the directory to save the split PDFs.
- `--mode`: Compression mode (same as `compress.py`). For documents whose bookmark contains "autos digitalizados" or "digitalizado", B&W mode is automatically forced.
- `--threshold-kb` (default: 150): The size limit in KB per page. If a split PDF exceeds this limit after standard compression, it is automatically rasterized to bypass vector/form bloating.

### `2up.py`
This script combines consecutive pages of a PDF side-by-side (2-up layout) into a single landscape page in a new PDF, keeping text layers fully searchable.

Options:
- `--input` (required): Absolute path to the source PDF file.
- `--output` (required): Absolute path to save the 2-up PDF file.

### Example Commands:

**1. Compress a scanned text document to minimum size (Black & White):**
```bash
uv run --no-project --with pymupdf,pillow <skill-dir>/scripts/compress.py \
  --input "/path/to/document.pdf" --output "/path/to/compressed.pdf" --mode bw
```

**2. Compress a document while preserving colors:**
```bash
uv run --no-project --with pymupdf,pillow <skill-dir>/scripts/compress.py \
  --input "/path/to/document.pdf" --output "/path/to/compressed.pdf" \
  --mode color --quality 55 --max-dim 1200
```

**3. Split a PDF by chapters and compress each part (with dynamic rasterization fallback for heavy parts):**
```bash
uv run --no-project --with pymupdf,pillow,opencv-python,numpy \
  <skill-dir>/scripts/split_and_compress.py \
  --input "/path/to/document.pdf" --output-dir "/path/to/split_dir" --threshold-kb 150
```

**4. Combine pages side-by-side (2-up layout):**
```bash
uv run --no-project --with pymupdf <skill-dir>/scripts/2up.py \
  --input "/path/to/document.pdf" --output "/path/to/2up_document.pdf"
```


## Common Mistakes

- **Running with standard Python instead of `uv run`:** Standard python invocation might fail if `pymupdf` or `pillow` are not installed in the global environment. Always run using `uv run --no-project --with pymupdf,pillow`.
- **Using `bw` mode for photos/color-heavy figures:** If the PDF has high-resolution colored graphs, photos, or diagrams where color is critical, `bw` mode will binarize them into high-contrast black and white, making them unreadable. Use `color` or `gray` mode for these files.
