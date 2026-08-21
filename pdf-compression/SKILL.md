---
name: pdf-compression
description: >-
  Optimize and compress large image-heavy or scanned PDFs by downscaling images and re-encoding them using CCITT Group 4 (black and white) or JPEG (grayscale/color).
  Use when compressing scanned PDFs, splitting large court PDFs by bookmarks, applying N-up (2-up/4-up) layouts, or when the user says "compress this PDF" / "PDF muito grande".
compatibility: >-
  Requires Python/uv; core compression installs PyMuPDF/Pillow dynamically.
  OpenCV/numpy are optional enhancements. JBIG2 mode additionally requires a
  `jbig2`/jbig2enc system binary; native Windows may need WSL or LiteBox for it.
---

# PDF Compression

For PDF/A or ISO 19005 conversion, use
[`convert-to-pdfa`](../convert-to-pdfa/SKILL.md). Compression and archival
conformance are separate workflows.

## Overview

This skill allows the agent to compress and optimize large, scanned, or image-heavy PDF files. It works by extracting images from the PDF, downscaling them to a reasonable resolution for reading, and re-encoding them with high-efficiency formats (specifically 1-bit CCITT Group 4 TIFF for black & white text, or compressed JPEG for grayscale and color images).

## Quick Start

Run the helper script using `uv run` to compress a PDF. It dynamically installs the required libraries (`pymupdf` and `pillow`) so they don't have to be pre-installed globally.

```bash
uv run --no-project --with pymupdf,pillow <skill-dir>/scripts/compress.py --input <input.pdf> --output <output.pdf> --mode bw
```

> `<skill-dir>` is resolved by `skills.sh` to the *installed* skill directory (e.g. `~/.claude/skills/pdf-compression`), not the source repo checkout. Run `skills.sh` from the repo root to install with the placeholder resolved automatically.

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
- `--jbig2`: For `bw`-mode pages, also try JBIG2 lossless encoding (generic-region coder only — no symbol/text-region matching, no refinement) and use it instead of CCITT G4 whenever it verifies bit-exact via a MuPDF roundtrip decode *and* the size it will actually occupy in the saved PDF beats CCITT G4's real saved size (not the intermediate TIFF container size — see Format Alternatives below). Requires the `jbig2` binary on `PATH`. **If it's missing and you (the agent) have shell access, just install it** — it's a normal OS package, not something that needs bundling or special handling: `apt-get install -y jbig2` on Debian/Ubuntu, `brew install jbig2enc` on macOS. Fedora's and Arch's *official* repos don't package the encoder at all (only Fedora's `jbig2dec` decoder, or Arch's AUR) — `compress.py` prints accurate build-from-source/AUR guidance for those rather than a command that would just fail. **On Windows** there's no native `jbig2` package to fall back on; if WSL2/Hyper-V aren't options, use the [`litebox`](../litebox/SKILL.md) skill as the adaptation lesson for carrying the Linux binary into Windows userland, then apply the same bit-exact roundtrip and size checks. It is not wired into `compress.py` automatically. See Licensing below for why this backend was safe to add.

### `process_pdf.py`

This script splits a large PDF based on its bookmarks (Table of Contents), applies a customizable N-up layout, compresses each split document (with binarization, downscaling, grayscale, and rasterization fallbacks), and re-merges the optimized parts back into a single PDF with rebuilt bookmarks.

Options:

- `--input` (required): Absolute path to the source PDF file.
- `--output-dir` (required): Absolute path to the directory to save the split PDFs.
- `--mode`: Compression mode (same as `compress.py`). For documents whose bookmark contains "autos digitalizados" or "digitalizado", B&W mode is automatically forced.
- `--threshold-kb` (default: 150): The size limit in KB per page. If a split PDF exceeds this limit after standard compression, it is automatically rasterized to bypass vector/form bloating.
- `--nup` (default: 1): Combine N pages from the original PDF into a grid on each page of the output PDF (e.g. 2, 4, 8, etc.).

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

**3. Split, N-up (2-up), compress, and re-merge a PDF (with dynamic rasterization fallback for heavy parts):**

```bash
uv run --no-project --with pymupdf,pillow,opencv-python,numpy \
  <skill-dir>/scripts/process_pdf.py \
  --input "/path/to/document.pdf" --output-dir "/path/to/split_dir" --threshold-kb 150 --nup 2
```

**4. Combine pages side-by-side (2-up layout) of a single PDF file directly:**

```bash
uv run --no-project --with pymupdf <skill-dir>/scripts/2up.py \
  --input "/path/to/document.pdf" --output "/path/to/2up_document.pdf"
```

**5. Compress a scanned document, preferring JBIG2 over CCITT G4 when it's smaller:**

```bash
uv run --no-project --with pymupdf,pillow <skill-dir>/scripts/compress.py \
  --input "/path/to/document.pdf" --output "/path/to/compressed.pdf" --mode bw --jbig2
```

## Format Alternatives

The default `bw` path encodes to a CCITT Group 4 TIFF via Pillow, but that
TIFF is only a transport container into PyMuPDF: `Page.replace_image()`
decodes it back to a raw bitmap immediately, and `doc.save(..., deflate=True)`
re-encodes that raw bitmap as `/FlateDecode` — the G4-compressed bytes never
reach the saved PDF. Concretely, a 1200×1600 text page's TIFF/G4 container
can be ~15 KB while the actual saved stream ends up ~9.5 KB (Flate on the
raw bitmap compresses better than that TIFF's own G4 payload plus header).
Passing `--jbig2` also tries `jbig2enc`'s lossless generic-region coder,
which typically beats that *real* saved size, not just the TIFF's — it's
still per-image (no cross-page symbol dictionary), so the win comes from
the coder itself, not symbol sharing. Each JBIG2 candidate is (1) decoded
back via MuPDF's own JBIG2Decode support and compared pixel-for-pixel
against the binarized image, and (2) measured by actually saving both the
JBIG2 and CCITT-G4-via-`replace_image` candidates in a throwaway one-page
PDF with the exact same save flags as the real output, so the size
comparison reflects bytes-on-disk rather than an intermediate container.
The script keeps CCITT G4 whenever the roundtrip fails, the binary is
missing, or JBIG2 doesn't win that real comparison.

## Licensing

`jbig2enc` is Apache-2.0 (its main dependency, Leptonica, is BSD-2-Clause)
— permissive, redistributable, no copyleft, and calling it as a subprocess
(as this skill does) doesn't link it into anything. JBIG2's US patents are
documented as expired (jbig2enc's own `doc/PATENTS`, corroborated by
OCRmyPDF's install docs); there's no way to rule out an unknown patent in
some jurisdiction, but that's true of any codec. No licensing blocker to
using it here. One operational caveat from jbig2enc's own README:
refinement coding crashes Acrobat — this skill never enables it (generic
region coder only, no `-s`/symbol matching, no `-r`/refinement).

## Testing

`scripts/test_compress_jbig2.py` is a self-contained regression suite for
the `--jbig2` backend (xref dict normalization when reusing an existing
image object, the real-saved-size comparison, install-hint accuracy per
package manager, and an end-to-end pixel-identity check against the G4
path). Run it with:

```bash
uv run --no-project --with pymupdf,pillow <skill-dir>/scripts/test_compress_jbig2.py
```

Tests that need the real `jbig2` binary are skipped (not failed) when it's
not on `PATH`.

## Common Mistakes

- **Running with standard Python instead of `uv run`:** Standard python invocation might fail if `pymupdf` or `pillow` are not installed in the global environment. Always run using `uv run --no-project --with pymupdf,pillow`.
- **Skipping `process_pdf.py`'s optional dependencies:** `process_pdf.py` can also use `opencv-python` and `numpy` for adaptive thresholding. If they're missing, it falls back automatically to plain Pillow thresholding (with a warning) rather than failing — add `uv run --no-project --with pymupdf,pillow,opencv-python,numpy` only if you want the OpenCV-based enhancement.
- **Using `bw` mode for photos/color-heavy figures:** If the PDF has high-resolution colored graphs, photos, or diagrams where color is critical, `bw` mode will binarize them into high-contrast black and white, making them unreadable. Use `color` or `gray` mode for these files.
- **Giving up when `--jbig2` falls back to CCITT G4:** the `jbig2` CLI is a system package, not a PyPI dependency `uv run --with` can install, so `compress.py` prints a warning and transparently falls back to CCITT G4 when it's missing rather than failing the whole run. That warning includes accurate install guidance for the current machine — just follow it and re-run `compress.py --jbig2`, the same way you'd install any other missing CLI tool. Don't treat the fallback as a hard limitation.
- **Assuming every package manager has a one-line `jbig2enc` install:** it doesn't. Fedora's and Arch's official repos don't package the encoder at all — only `apt-get` (Debian/Ubuntu) and `brew` (macOS) do. `_jbig2_install_hint()` in `compress.py` reflects this; don't "fix" it to always print a single `<pkg-manager> install jbig2enc` command, that would just print commands that fail on those distros.

## Real-use postmortem

After any material use of this skill, perform a brief self-postmortem before ending the task:
assess whether routing was correct, whether the skill materially improved/neutral/degraded the
result, what concrete instruction mattered, and any friction or workaround. Routine success
stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and add
evidence to an existing matching issue or open a sanitized **Skill use feedback** issue. Never
publish secrets, private/confidential facts, credentials, or personal data, and do not interrupt
the user's task merely to report feedback.
