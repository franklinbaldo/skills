#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "markitdown[pdf]",
#     "pymupdf",
# ]
# ///
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import cyclopts
from cyclopts import Parameter

# Marcadores que abrem um novo documento dentro do PDF único do processo.
DOC_MARKERS = (
    "INTIMAÇÃO",
    "SENTENÇA",
    "DECISÃO",
    "DESPACHO",
    "PETIÇÃO",
    "CONTRARRAZÕES",
    "PROCURAÇÃO",
    "ATA DE DISTRIBUIÇÃO",
    "CERTIDÃO",
    "PARECER",
    "MANIFESTAÇÃO",
    "OFÍCIO",
)
MARKER_REGEX = re.compile(
    r"^\s*(" + "|".join(DOC_MARKERS) + r")\b", re.IGNORECASE | re.MULTILINE
)
DEFAULT_TITLE = "Documento_Geral"
TITLE_SCAN_CHARS = 300


def clean_text(text):
    """Clean repeating headers, footers and typical system stamps from court documents."""
    # Remove ComunicaAPI URLs and Certidão stamps
    text = re.sub(r'https://comunicaapi\.pje\.jus\.br/api/v1/comunicacao/\S+', '', text)
    text = re.sub(r'Código da certidão:\s*\S+', '', text)
    
    # Remove repeating page headers/footers from DJEN/STJ
    text = re.sub(r'Poder Judiciário\s*Superior Tribunal de Justiça\s*Diário de Justiça Eletrônico Nacional de \d\d/\d\d/\d\d\d\d\s*Certidão de publicação \d+', '', text)
    
    # Remove double newlines/whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

@dataclass(frozen=True)
class Document:
    """Um documento do processo, já delimitado dentro do PDF original."""

    title: str
    chunks: list[str]
    first_chunk_number: int
    paginated: bool

    def render(self) -> str:
        """O corpo do documento, com marcador de página só quando há páginas reais."""
        if not self.paginated:
            return clean_text("\n\n".join(self.chunks))
        numbered = [
            f"<!-- Page {self.first_chunk_number + offset} -->\n{chunk}"
            for offset, chunk in enumerate(self.chunks)
        ]
        return clean_text("\n\n".join(numbered))

    def filename(self, sequence: int) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_]", "_", self.title.strip().replace(" ", "_")).lower()
        return f"{sequence:02d}_{slug[:40]}.md"


@dataclass(frozen=True)
class Extraction:
    """Texto extraído de um PDF, na granularidade que o extrator realmente entrega.

    `paginated` é falso quando o extrator devolve o documento inteiro como um
    único fluxo (markitdown): nesse caso não há número de página a informar, e
    fabricar um seria mentir sobre a origem do texto.
    """

    chunks: list[str]
    paginated: bool

    def into_documents(self) -> list[Document]:
        documents: list[Document] = []
        title = DEFAULT_TITLE
        pending: list[str] = []
        first_number = 1

        for number, chunk in enumerate(self.chunks, start=1):
            match = MARKER_REGEX.search(chunk[:TITLE_SCAN_CHARS])
            if match:
                if pending:
                    documents.append(Document(title, pending, first_number, self.paginated))
                title = title_from_match(chunk[:TITLE_SCAN_CHARS], match)
                pending = []
                first_number = number
            pending.append(chunk)

        if pending:
            documents.append(Document(title, pending, first_number, self.paginated))
        return documents


def title_from_match(head: str, match: re.Match[str]) -> str:
    """O título é a linha inteira que contém o marcador, normalizada."""
    matched_line = next(
        (line.strip() for line in head.splitlines() if match.group(1).lower() in line.lower()),
        "",
    )
    title = re.sub(r"\s+", " ", re.sub(r"[\r\n\t]", " ", matched_line)).strip(":- ")
    return title or match.group(1).title()


def split_on_markers(text: str) -> list[str]:
    """Corta um fluxo sem páginas nos pontos onde um novo documento começa."""
    cuts = [match.start() for match in MARKER_REGEX.finditer(text)]
    if not cuts:
        return [text]
    if cuts[0] != 0:
        cuts.insert(0, 0)
    bounds = cuts + [len(text)]
    # `^\s*` come a quebra de linha anterior ao marcador; o lstrip devolve o
    # chunk começando no próprio marcador, que é o que a titulação espera.
    chunks = [text[bounds[i]:bounds[i + 1]].lstrip() for i in range(len(bounds) - 1)]
    return [chunk for chunk in chunks if chunk]


def save_documents(documents: list[Document], outdir: str, base_pdf_name: str) -> None:
    """Grava um arquivo por documento e o INDEX.md do processo."""
    index_entries = []
    for sequence, document in enumerate(documents, start=1):
        content = document.render()
        if not content:
            continue
        filename = document.filename(sequence)
        with open(os.path.join(outdir, filename), "w", encoding="utf-8") as handle:
            handle.write(f"# {document.title.upper()}\n\n")
            handle.write(content)
        print(f"  Saved: {filename} ({len(content)} chars)")
        snippet = content[:150].replace("\n", " ") + "..."
        index_entries.append((sequence, document.title, filename, snippet))

    generate_index(outdir, base_pdf_name, index_entries)


def generate_index(outdir, base_pdf_name, index_entries):
    index_path = os.path.join(outdir, "INDEX.md")
    case_number = base_pdf_name.replace(".pdf", "")
    
    # Simple formatting of case number if it fits standard CNJ pattern
    formatted_case = case_number
    if len(case_number) == 20 and case_number.isdigit():
        formatted_case = f"{case_number[0:7]}-{case_number[7:9]}.{case_number[9:13]}.{case_number[13:14]}.{case_number[14:16]}.{case_number[16:20]}"
        
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"# Processo Judicial: {formatted_case}\n\n")
        f.write(f"Documentos extraídos do arquivo original: `{base_pdf_name}`\n\n")
        f.write("## Índice de Documentos\n\n")
        f.write("| # | Documento | Arquivo | Resumo / Início |\n")
        f.write("|---|-----------|---------|-----------------|\n")
        for seq, title, filename, snippet in index_entries:
            f.write(f"| {seq} | **{title}** | [{filename}](./{filename}) | {snippet} |\n")
            
    print("  Generated INDEX.md successfully.")

def load_markitdown() -> Any | None:
    """A classe MarkItDown, ou None quando o pacote não está disponível.

    Isolado numa função para que a indisponibilidade do extrator seja um caso
    de negócio (cai no PyMuPDF) e não uma exceção atravessando a conversão.
    """
    try:
        from markitdown import MarkItDown
    except ImportError:
        print("markitdown is not installed in this environment.", file=sys.stderr)
        return None
    return MarkItDown


def extract_with_markitdown(
    pdf_path: Path,
    *,
    keep_data_uris: bool = False,
    docintel_endpoint: str | None = None,
    cu_endpoint: str | None = None,
) -> Extraction | None:
    """Extrai o PDF com markitdown; None quando o extrator falha ou não existe.

    markitdown devolve um único fluxo markdown, sem fronteiras de página — por
    isso a Extraction resultante nunca é paginada, e os documentos são
    delimitados pelos próprios marcadores do texto.
    """
    markitdown = load_markitdown()
    if markitdown is None:
        return None

    options: dict[str, Any] = {}
    if docintel_endpoint:
        options["docintel_endpoint"] = docintel_endpoint
    if cu_endpoint:
        options["cu_endpoint"] = cu_endpoint

    print("Attempting high-fidelity conversion using markitdown...")
    try:
        result = markitdown(**options).convert(str(pdf_path), keep_data_uris=keep_data_uris)
    except Exception as error:  # fronteira com biblioteca de terceiro
        print(f"markitdown failed: {error!r}", file=sys.stderr)
        return None

    text = (result.text_content or "").strip()
    if not text:
        print("markitdown returned no text.", file=sys.stderr)
        return None
    print("Successfully converted PDF with markitdown.")
    return Extraction(chunks=split_on_markers(text), paginated=False)


def extract_with_pymupdf(pdf_path: Path) -> Extraction | None:
    """Extrai o PDF com PyMuPDF, uma página por chunk; None quando falha."""
    print("Falling back to PyMuPDF (fitz) for conversion...")
    try:
        import fitz

        with fitz.open(str(pdf_path)) as document:
            pages = [page.get_text() for page in document]
    except Exception as error:  # fronteira com biblioteca de terceiro
        print(f"PyMuPDF extraction failed: {error!r}", file=sys.stderr)
        return None

    if not pages:
        return None
    print(f"Successfully extracted {len(pages)} pages using PyMuPDF.")
    return Extraction(chunks=pages, paginated=True)


app = cyclopts.App(name="convert-pdf", help="Convert court process PDFs into clean structured Markdown folders.")


@app.default
def main(
    *,
    input_path: Annotated[Path, Parameter(name=["--input"])],
    outdir: Path,
    keep_data_uris: bool = False,
    docintel_endpoint: str | None = None,
    cu_endpoint: str | None = None,
):
    """Convert one PDF into a structured Markdown folder.

    Parameters
    ----------
    input_path
        Path to the input PDF file.
    outdir
        Directory to save the markdown files.
    keep_data_uris
        Keep data URIs in output.
    docintel_endpoint
        Azure Document Intelligence endpoint URL.
    cu_endpoint
        Azure Content Understanding endpoint URL.
    """
    pdf_path = os.path.abspath(input_path)
    outdir = os.path.abspath(outdir)

    if not os.path.exists(pdf_path):
        print(f"Error: Input file does not exist: {pdf_path}")
        sys.exit(1)

    os.makedirs(outdir, exist_ok=True)
    base_pdf_name = os.path.basename(pdf_path)

    print(f"Processing: {base_pdf_name}")
    print(f"Output directory: {outdir}")

    # markitdown primeiro (melhor fidelidade); PyMuPDF quando ele não serve.
    extraction = extract_with_markitdown(
        Path(pdf_path),
        keep_data_uris=keep_data_uris,
        docintel_endpoint=docintel_endpoint,
        cu_endpoint=cu_endpoint,
    ) or extract_with_pymupdf(Path(pdf_path))

    if extraction is None:
        print("Error: All conversion methods failed.")
        sys.exit(1)

    save_documents(extraction.into_documents(), outdir, base_pdf_name)
    print("\nConversion finished successfully!")


if __name__ == "__main__":
    app()
