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
uv run --no-project --with pymupdf,pillow C:\Users\frank\workspace\skills\pdf-compression\scripts\compress.py --input <input_pdf> --output <output_pdf> --mode bw
```

## Utility Scripts

### `compress.py`
The CLI script provides several options to control the compression style and target size:

- `--input` (required): Absolute path to the source PDF file.
- `--output` (required): Absolute path to save the compressed/optimized PDF file.
- `--mode`: The compression algorithm to use:
  - `bw` (default): Converts images to 1-bit Black & White and compresses using CCITT Group 4. This is extremely efficient for scanned text documents (often reducing size by 90%+).
  - `gray`: Converts images to 8-bit grayscale and compresses with JPEG.
  - `color`: Preserves image colors and compresses with JPEG.
- `--max-dim` (default: 1200): Downscale any image whose width or height exceeds this value, maintaining aspect ratio.
- `--quality` (default: 50): JPEG compression quality (1-100) for `gray` and `color` modes.
- `--skip-small` (default: 150): Do not compress images with both dimensions smaller than this threshold (useful to protect logos, icons, and small vector graphics from compression artifacts).

### Example Commands:

**1. Compress a scanned text document to minimum size (Black & White):**
```bash
uv run --no-project --with pymupdf,pillow C:\Users\frank\workspace\skills\pdf-compression\scripts\compress.py --input "C:\path\to\document.pdf" --output "C:\path\to\compressed.pdf" --mode bw
```

**2. Compress a document while preserving colors:**
```bash
uv run --no-project --with pymupdf,pillow C:\Users\frank\workspace\skills\pdf-compression\scripts\compress.py --input "C:\path\to\document.pdf" --output "C:\path\to\compressed.pdf" --mode color --quality 55 --max-dim 1200
```

## Common Mistakes

- **Running with standard Python instead of `uv run`:** Standard python invocation might fail if `pymupdf` or `pillow` are not installed in the global environment. Always run using `uv run --no-project --with pymupdf,pillow`.
- **Using `bw` mode for photos/color-heavy figures:** If the PDF has high-resolution colored graphs, photos, or diagrams where color is critical, `bw` mode will binarize them into high-contrast black and white, making them unreadable. Use `color` or `gray` mode for these files.
