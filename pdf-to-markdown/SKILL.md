---
name: pdf-to-markdown
description: |
  Converts court/process PDF documents (from PJe, SEI, Kanoê, or other systems) into clean, structured Markdown.
  Organizes the output in a directory named after the case (CNJ or NUP) where each document or section of the case
  becomes a separate .md file. Prefers `markitdown` via `uvx` / `uv run` with custom options, falling back to PyMuPDF.
---

# PDF-to-Markdown Court Document Conversion

Use this skill when you need to convert, extract, or organize judicial processes or court files (typically in PDF format from systems like PJe, SEI, Kanoê, or court portals) into readable Markdown.

## When to Trigger
- "Converta este PDF/processo para markdown"
- "Extraia os documentos deste processo/PDF"
- "Organize o PDF do PJe/SEI em arquivos md"
- "Traduza o processo X para uma pasta de md"

## CLI and Library Options
The conversion tool (`convert_pdf.py`) supports specific options to control how `markitdown` converts the files:

1. **`--keep-data-uris`**:
   - *Use when:* The PDF contains embedded diagrams, graphs, or small images that are relevant to the case, and you want them preserved as base64 data URIs in the Markdown.
   - *Behavior:* Prevents `markitdown` from truncating raw image data URLs.

2. **`--docintel-endpoint <URL>`**:
   - *Use when:* The PDF is a scanned image (non-searchable text) and requires advanced cloud-based OCR.
   - *Behavior:* Uses Azure Document Intelligence to run OCR and layout analysis instead of local text extraction. Requires setting Azure credentials in the environment.

3. **`--cu-endpoint <URL>`**:
   - *Use when:* The PDF contains complex multi-media elements or requires Azure Content Understanding.

4. **PyMuPDF Fallback**:
   - *Use when:* Offline, or when no cloud credentials are provided, or when `markitdown` fails. This fallback executes local extraction via PyMuPDF (`fitz`), which is extremely fast and reliable for text-searchable court PDFs.

## Core Workflow

### 1. Identify Case Metadata
Determine the case number (CNJ like `7000834-57.2017.8.22.0014` or NUP like `0016650-48.2014.8.22.0001`) from the file name, the file content, or by querying the database.

### 2. Set Up Output Directory
Create a directory named after the case number under the target workspace (e.g. `<workspace>/<case-number>`).

### 3. Convert Documents
Run the python utility `convert_pdf.py` provided in the skill scripts with the appropriate options:
```bash
uv run --no-project --with pymupdf,markitdown \
  <skill-dir>/scripts/convert_pdf.py \
  --input "path/to/process.pdf" \
  --outdir "path/to/output-directory" \
  [--keep-data-uris] [--docintel-endpoint <URL>]
```

> `<skill-dir>` is resolved at install time by `skills.sh` (e.g. `~/skills/pdf-to-markdown`).

The script will:
- Check if `uvx markitdown` is available and run it with the specified options.
- Fall back to PyMuPDF (`fitz`) if local conversion fails.
- Detect document boundaries inside merged PDFs (common in PJe downloads) using page-break titles (e.g. "SENTENÇA", "DECISÃO", "DESPACHO", "PETIÇÃO INICIAL").
- Save each distinct document into a separate `.md` file named after the document type and sequence (e.g., `01_peticao_inicial.md`, `02_despacho.md`, `03_sentenca.md`).
- Clean up repeating artifacts like headers, footers, page numbers, and system barcodes.

### 4. Generate Case Index
Generate an `INDEX.md` file in the case directory containing:
- Case number, court, and metadata.
- A table listing all extracted documents with a summary and a clickable link to each `.md` file.

## Best Practices
- **Clean Layouts:** Ensure tables are properly converted to Markdown tables.
- **Maintain Metadata:** Preserve date, time, authors, and signature metadata at the top of each document.
- **Keep Original PDF Link:** Provide a link back to the original PDF for reference.
