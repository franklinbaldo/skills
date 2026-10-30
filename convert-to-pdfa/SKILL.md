---
name: convert-to-pdfa
description: Convert PDFs to archival PDF/A-1b, PDF/A-2b, or PDF/A-3b across Windows, WSL, macOS, and Linux. Use when a user asks for PDF/A, archival PDF, ISO 19005 conversion, or a PDF accepted by SEI, PJe, courts, and document-management validators.
compatibility: >-
  Requires Python/uv. The default pikepdf path uses Python dependencies installed by uv, including
  bundled qpdf on supported wheel platforms. Ghostscript is optional and used
  only with an explicitly selected alternative backend. Official
  veraPDF CLI is optional unless normative validation is required. Locked-down Windows without a supported wheel may need the documented
  adaptation route.
---

# Convert to PDF/A

Create a separate, validated PDF/A copy. Default to PDF/A-2b: it preserves
modern PDF features better than PDF/A-1b while targeting visual fidelity.

## Contract

- Preserve the original; never convert in place.
- Prefer vector conversion so text, links, and geometry survive.
- Treat XMP as a claim, not proof. A conforming file also needs the applicable
  PDF/A rules, including an ICC-backed OutputIntent.
- Use `pikepdf.pdfa` by default and fail clearly when its validator blocks.
  Never silently switch to Ghostscript. PyMuPDF alone is not a general PDF/A writer.
- Call a result “veraPDF compliant” only when veraPDF actually reports
  `isCompliant="true"`. Otherwise say “structurally verified”.
- Expect any full rewrite to invalidate digital signatures. The script refuses
  signature fields unless `--allow-signed` is explicitly supplied.

## Before converting: is PDF/A the problem?

When a court system rejects a file, check size against the destination's limit
first. In the case behind `franklinbaldo/pink#454`, three documents refused by
the TJRO MNI with "serviço não respondeu" were too large, not non-PDF/A, and
conversion would not have helped. Convert when the destination asks for PDF/A:
the PDPJ Portal's upload form, for instance, refuses a PDF without XMP
metadata (`xmp:createdate`), which this conversion adds.

## Backends

- **pikepdf (default)**: `pikepdf.pdfa.prepare` repairs
  structure and metadata (output intent, XMP, annotation flags, JavaScript)
  without touching page content, preserving page drawing operations.
  No Ghostscript is required; `uv` installs Python dependencies on supported platforms. The written file is
  re-checked by `validate_written`.
- **When it fails**: any `violation`, and any `unsupported` finding. pikepdf reports some real ISO rules as
  `unsupported` (a non-embedded font is one), so those block too. Unknown schema keys also block: unrecognized constructs cannot prove
  conformance. pikepdf does not embed fonts,
  convert colour or flatten transparency; Ghostscript does.
- **CreationDate**: `prepare` writes `xmp:CreateDate` only from
  `/CreationDate`, which Google Docs exports lack, and the PDPJ portal refuses
  a PDF without `xmp:createdate`. The pikepdf path fills a missing
  `/CreationDate`/`/ModDate` (now, or `--creation-date`) before `prepare`.
- **Ghostscript (`native`/`wsl`)**: optional, explicitly requested rewrite.
  `--backend auto` explicitly opts into pikepdf followed by Ghostscript; it is
  not the default.

## Workflow

1. Identify the input and a distinct output path. If the user did not name the
   output, let the script create `<name>-PDFA.pdf` beside the source.

2. Run strict, non-raster conversion:

   ```bash
   uv run <skill-dir>/scripts/convert_to_pdfa.py "/path/input.pdf" --part 2
   ```

   The report names the backend used. Unsupported input fails clearly without
   invoking Ghostscript. Select an alternative backend only intentionally.

3. Read the final report. Completion requires the same page count and page
   dimensions, a PDF/A-Xb XMP identifier, ICC OutputIntent, no material
   searchable-text loss, and either pikepdf's `validate_written` without
   blocking findings or a successful Ghostscript parse.

4. If the official veraPDF CLI is installed, it runs automatically. For a
   filing that requires normative validation, add `--require-verapdf`; absence
   or rejection must fail the task.

5. Only if strict conversion fails because of incompatible source content,
   explain the loss and retry with:

   ```bash
   uv run <skill-dir>/scripts/convert_to_pdfa.py "/path/input.pdf" \
     --part 2 --rasterize --dpi 300
   ```

   Rasterization is a last resort: it removes searchable text, links,
   accessibility structure, forms, and signature validity.

6. Return the output path, PDF/A part/conformance, page count, text-preservation
   result, and whether validation was veraPDF or structural.

## Options

- `--output PATH`: explicit destination.
- `--part {1,2,3}`: create PDF/A-1b, 2b, or 3b; default `2`.
- `--backend {auto,pikepdf,native,wsl}`: `pikepdf` is the default and fails on
  blocking findings without invoking Ghostscript. `auto` explicitly opts into
  pikepdf then Ghostscript;
  `native`/`wsl` force Ghostscript.
- `--creation-date ISO`: `/CreationDate` to write when the source has none
  (pikepdf path); default now, local time with offset.
- `--compatibility-policy 2`: strict default; abort on incompatible content.
- `--compatibility-policy 1`: allow Ghostscript to omit incompatible
  operations with warnings; use only after reviewing the loss.
- `--rasterize --dpi 300`: image-only fallback.
- `--require-verapdf`: require normative veraPDF success.
- `--allow-signed`: acknowledge signature invalidation.
- `--force`: replace an existing output only after the new candidate validates.

## Dependencies

The default path needs only Python/uv and its declared Python dependencies;
no Ghostscript executable is required. Install Ghostscript only if you choose
an optional `native`, `wsl`, or `auto` backend:

- Debian/Ubuntu: `sudo apt-get install ghostscript`
- Fedora: `sudo dnf install ghostscript`
- Arch: `sudo pacman -S ghostscript`
- macOS: `brew install ghostscript`
- Windows: install the official 64-bit Ghostscript build and add
  `gswin64c.exe` to `PATH`, or install `ghostscript` inside WSL.
- Windows with Scoop (no admin): `scoop install ghostscript`. The `gswin64c`
  on `PATH` is a Scoop shim; the script follows its `.shim` file to the real
  install, where `lib\PDFA_def.ps` and `iccprofiles\srgb.icc` live.

**No admin rights on Windows? Try extraction before WSL or LiteBox.** The
official Windows installer (`gs<version>w64.exe` from
[`ArtifexSoftware/ghostpdl-downloads`](https://github.com/ArtifexSoftware/ghostpdl-downloads/releases))
is a plain NSIS package. Running it needs elevation, but *unpacking* it does
not:

```powershell
& "C:\Program Files\7-Zip\7z.exe" x gs10071w64.exe -o<dest_dir>
```

This produces a working `bin\gswin64c.exe` plus the `lib\`, `Resource\`, and
`iccprofiles\` directories it needs — no install, no UAC prompt. Add
`<dest_dir>\bin` to `PATH` (a user-level `PATH` edit needs no admin either)
so `_native_ghostscript()`'s `shutil.which` lookup finds it, or pass
`--backend native` after exporting `PATH` for the current session. Confirmed
working end-to-end (including a real `-dPDFA=2` conversion) on Windows
without any elevated action, with 7-Zip already present; if 7-Zip itself
isn't installed, it also installs without admin (portable build, or
`winget install 7zip.7zip --scope user` where available).

Only fall back to WSL or the `litebox` adaptation lesson (see
[Ghostscript recipe](../litebox/references/task-recipes.md)) when this
extraction route is unavailable — e.g. no way to run 7-Zip or an equivalent
archive tool on the target machine. LiteBox changes how Ghostscript runs; it
does not relax any conformance check, and needs a real Linux ELF build +
packaging step that a native Windows binary makes unnecessary.

For normative validation, install the official Java-based veraPDF CLI and add
`verapdf` (`verapdf.bat` on Windows) to `PATH`. `uvx pdfa-parser` is a
third-party Alpha wrapper, not the official veraPDF distribution; do not use it
as the default or sole validator.

Ghostscript supports PDF/A parts 1–3 at conformance level **b**. Do not promise
`a` or `u` output from this workflow.

## Tests

Run the self-contained regression suite. Real pikepdf tests run without
Ghostscript. Only the optional Ghostscript integration tests skip when neither
a native executable nor WSL Ghostscript is available.

```bash
uv run <skill-dir>/scripts/test_convert_to_pdfa.py -v
uv run <skill-dir>/scripts/test_pikepdf_backend.py -v
```

Authoritative references:
[pikepdf PDF/A](https://pikepdf.readthedocs.io/),
[Ghostscript PDF/A creation](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html#creating-a-pdf-a-document)
and [veraPDF CLI validation](https://docs.verapdf.org/cli/validation/).

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
