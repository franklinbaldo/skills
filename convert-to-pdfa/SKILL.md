---
name: convert-to-pdfa
description: Convert PDFs to archival PDF/A-1b, PDF/A-2b, or PDF/A-3b across Windows, WSL, macOS, and Linux. Use when a user asks for PDF/A, archival PDF, ISO 19005 conversion, or a PDF accepted by SEI, PJe, courts, and document-management validators.
---

# Convert to PDF/A

Create a separate, validated PDF/A copy. Default to PDF/A-2b: it preserves
modern PDF features better than PDF/A-1b while targeting visual fidelity.

## Contract

- Preserve the original; never convert in place.
- Prefer vector conversion so text, links, and geometry survive.
- Treat XMP as a claim, not proof. A conforming file also needs the applicable
  PDF/A rules, including an ICC-backed OutputIntent.
- Use Ghostscript for conversion. PyMuPDF alone is not a general PDF/A writer.
- Call a result “veraPDF compliant” only when veraPDF actually reports
  `isCompliant="true"`. Otherwise say “structurally verified”.
- Expect any full rewrite to invalidate digital signatures. The script refuses
  signature fields unless `--allow-signed` is explicitly supplied.

## Workflow

1. Identify the input and a distinct output path. If the user did not name the
   output, let the script create `<name>-PDFA.pdf` beside the source.
2. Run strict, non-raster conversion:

   ```bash
   uv run --no-project --with pymupdf \
     <skill-dir>/scripts/convert_to_pdfa.py "/path/input.pdf" --part 2
   ```

   On Windows, the script prefers native `gswin64c.exe` and automatically uses
   Ghostscript in WSL when no native executable exists.
3. Read the final report. Completion requires the same page count and page
   dimensions, a PDF/A-Xb XMP identifier, ICC OutputIntent, successful
   Ghostscript parse, and no material searchable-text loss.
4. If the official veraPDF CLI is installed, it runs automatically. For a
   filing that requires normative validation, add `--require-verapdf`; absence
   or rejection must fail the task.
5. Only if strict conversion fails because of incompatible source content,
   explain the loss and retry with:

   ```bash
   uv run --no-project --with pymupdf \
     <skill-dir>/scripts/convert_to_pdfa.py "/path/input.pdf" \
     --part 2 --rasterize --dpi 300
   ```

   Rasterization is a last resort: it removes searchable text, links,
   accessibility structure, forms, and signature validity.
6. Return the output path, PDF/A part/conformance, page count, text-preservation
   result, and whether validation was veraPDF or structural.

## Options

- `--output PATH`: explicit destination.
- `--part {1,2,3}`: create PDF/A-1b, 2b, or 3b; default `2`.
- `--backend {auto,native,wsl}`: choose Ghostscript execution path.
- `--compatibility-policy 2`: strict default; abort on incompatible content.
- `--compatibility-policy 1`: allow Ghostscript to omit incompatible
  operations with warnings; use only after reviewing the loss.
- `--rasterize --dpi 300`: image-only fallback.
- `--require-verapdf`: require normative veraPDF success.
- `--allow-signed`: acknowledge signature invalidation.
- `--force`: replace an existing output only after the new candidate validates.

## Dependencies

Install Ghostscript when neither a native executable nor WSL backend is
available:

- Debian/Ubuntu: `sudo apt-get install ghostscript`
- Fedora: `sudo dnf install ghostscript`
- Arch: `sudo pacman -S ghostscript`
- macOS: `brew install ghostscript`
- Windows: install the official 64-bit Ghostscript build and add
  `gswin64c.exe` to `PATH`, or install `ghostscript` inside WSL.

On locked-down x86-64 Windows without WSL or permission to install software,
consult the [`litebox`](../litebox/SKILL.md) adaptation lesson and its
[Ghostscript recipe](../litebox/references/task-recipes.md). It teaches the
agent to package Linux Ghostscript, bridge the source and result, and validate
the PDF/A output. LiteBox changes how Ghostscript runs; it does not relax any
conformance check.

For normative validation, install the official Java-based veraPDF CLI and add
`verapdf` (`verapdf.bat` on Windows) to `PATH`. `uvx pdfa-parser` is a
third-party Alpha wrapper, not the official veraPDF distribution; do not use it
as the default or sole validator.

Ghostscript supports PDF/A parts 1–3 at conformance level **b**. Do not promise
`a` or `u` output from this workflow.

## Tests

Run the self-contained regression suite. Real conversion tests skip only when
neither native Ghostscript nor WSL Ghostscript is available.

```bash
uv run --no-project --with pymupdf \
  <skill-dir>/scripts/test_convert_to_pdfa.py -v
```

Authoritative references:
[Ghostscript PDF/A creation](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html#creating-a-pdf-a-document)
and [veraPDF CLI validation](https://docs.verapdf.org/cli/validation/).
