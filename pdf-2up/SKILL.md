---
name: pdf-2up
description: >-
  Combine two pages of a PDF side-by-side (2-up layout) into a single page in a new PDF, preserving vector text layers.
---

# PDF 2-Up Layout Converter

## Overview
This skill allows combining consecutive pages of a PDF side-by-side into a single landscape page (2-up). It is highly useful for printing presentations, slides, or saving page count, and operates entirely in vector space to keep text layers searchable.

## Quick Start
Run the helper script using `uv run` to generate the 2-up PDF:

```bash
uv run --no-project --with pymupdf <skill-dir>/scripts/2up.py --input <input.pdf> --output <output.pdf>
```

> `<skill-dir>` is the directory where this skill is installed.

## Options
- `--input` (required): Absolute path to the source PDF.
- `--output` (required): Absolute path to save the 2-up PDF.
