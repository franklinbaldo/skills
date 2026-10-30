#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pymupdf",
#     "cyclopts>=3.0",
#     "pikepdf[pdfa]>=10.17",
# ]
# ///
"""Convert a PDF to PDF/A-1b, PDF/A-2b, or PDF/A-3b.

pikepdf.pdfa promotes the file first (no Ghostscript); when its validator
reports a violation, Ghostscript performs the conversion. PyMuPDF provides
preflight checks, an explicit raster fallback, and structural verification.
veraPDF is used when its official CLI is available.
"""

from __future__ import annotations

import difflib
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import cyclopts
import pymupdf
from cyclopts import Parameter
from ghostscript_backend import (  # noqa: F401 - _scoop_target re-exported for tests
    Backend,
    PdfaError,
    _convert_native,
    _convert_wsl,
    _run,
    _scoop_target,
    _select_backend,
    _wsl_available,
    _wsl_path,
)
from pikepdf_backend import convert_pikepdf

BackendChoice = Literal["auto", "pikepdf", "native", "wsl"]

SUPPORTED_PARTS = (1, 2, 3)
PAGE_SIZE_TOLERANCE = 0.05
TEXT_SIMILARITY_FLOOR = 0.98


@dataclass(frozen=True)
class Verification:
    """Verification facts reported after conversion."""

    pages: int
    pdf_format: str
    text_similarity: float | None
    verapdf: str
    backend: str = "unknown"
    unchecked: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def _default_output(input_path: Path) -> Path:
    """Return a non-destructive output name next to the source."""
    return input_path.with_name(f"{input_path.stem}-PDFA.pdf")


def _resolve_paths(
    input_value: str, output_value: str | None, *, force: bool
) -> tuple[Path, Path]:
    """Resolve and validate input/output paths before any conversion starts."""
    input_path = Path(input_value).expanduser().resolve()
    output_path = (
        Path(output_value).expanduser().resolve()
        if output_value
        else _default_output(input_path)
    )
    if not input_path.is_file():
        msg = f"Input PDF not found: {input_path}"
        raise PdfaError(msg)
    if input_path.suffix.lower() != ".pdf":
        msg = f"Input must be a PDF: {input_path}"
        raise PdfaError(msg)
    if input_path == output_path:
        raise PdfaError("Refusing in-place conversion; choose a different output path.")
    if output_path.exists() and not force:
        msg = f"Output already exists: {output_path}. Pass --force to replace it after validation."
        raise PdfaError(msg)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return input_path, output_path


def _preflight(
    input_path: Path,
    *,
    allow_signed: bool,
) -> tuple[int, list[tuple[float, float]], str]:
    """Read the source once and capture invariants used after conversion."""
    with pymupdf.open(input_path) as document:
        if document.needs_pass:
            raise PdfaError(
                "Encrypted/password-protected PDFs must be decrypted before conversion."
            )
        if document.page_count == 0:
            raise PdfaError("The input PDF has no pages.")
        if document.get_sigflags() in {1, 3} and not allow_signed:
            raise PdfaError(
                "The PDF contains signature fields. Conversion can invalidate signatures; "
                "preserve the signed original and pass --allow-signed only after accepting that."
            )
        sizes = [(page.rect.width, page.rect.height) for page in document]
        text = "".join(page.get_text() for page in document)
        return document.page_count, sizes, text


def _rasterize(input_path: Path, output_path: Path, *, dpi: int) -> None:
    """Flatten every page to a lossless RGB bitmap at the requested DPI."""
    scale = dpi / 72
    matrix = pymupdf.Matrix(scale, scale)
    with pymupdf.open(input_path) as source, pymupdf.open() as target:
        for source_page in source:
            page = target.new_page(
                width=source_page.rect.width, height=source_page.rect.height
            )
            pixmap = source_page.get_pixmap(
                matrix=matrix, colorspace=pymupdf.csRGB, alpha=False
            )
            page.insert_image(page.rect, pixmap=pixmap)
        target.save(output_path, garbage=4, deflate=True)


def _ghostscript_parse(
    backend: Backend, ghostscript: str | None, output_path: Path
) -> None:
    """Ask Ghostscript to parse every output page and stop on PDF errors."""
    arguments = ["-q", "-dBATCH", "-dNOPAUSE", "-dPDFSTOPONERROR", "-sDEVICE=nullpage"]
    if backend == "native":
        if ghostscript is None:
            raise PdfaError(
                "Internal error: native backend selected without Ghostscript."
            )
        _run([ghostscript, *arguments, str(output_path)])
    else:
        _run(["wsl.exe", "-e", "gs", *arguments, _wsl_path(output_path)])


def _pdfa_claim(xml: str, part: int) -> bool:
    """Check both XMP attribute and element forms of the PDF/A identifier."""
    part_pattern = (
        rf"(?:pdfaid:part=['\"]{part}['\"]|<pdfaid:part>\s*{part}\s*</pdfaid:part>)"
    )
    b_pattern = (
        r"(?:pdfaid:conformance=['\"]B['\"]|"
        r"<pdfaid:conformance>\s*B\s*</pdfaid:conformance>)"
    )
    return (
        re.search(part_pattern, xml, flags=re.IGNORECASE) is not None
        and re.search(
            b_pattern,
            xml,
            flags=re.IGNORECASE,
        )
        is not None
    )


def _normalized_text(text: str) -> str:
    """Normalize whitespace only, preserving the extracted character sequence."""
    return " ".join(text.split())


def _structural_verify(
    output_path: Path,
    *,
    expected_pages: int,
    expected_sizes: list[tuple[float, float]],
    input_text: str,
    part: int,
    rasterized: bool,
) -> Verification:
    """Verify the output's PDF/A claim, output intent, geometry, and text."""
    with pymupdf.open(output_path) as document:
        if document.needs_pass or document.is_encrypted:
            raise PdfaError("PDF/A output must not be encrypted.")
        if document.page_count != expected_pages:
            msg = f"Page count changed: {expected_pages} -> {document.page_count}"
            raise PdfaError(msg)
        output_sizes = [(page.rect.width, page.rect.height) for page in document]
        for page_number, (expected, actual) in enumerate(
            zip(expected_sizes, output_sizes, strict=True),
            start=1,
        ):
            if any(
                abs(left - right) > PAGE_SIZE_TOLERANCE
                for left, right in zip(expected, actual)
            ):
                msg = f"Page {page_number} dimensions changed: {expected} -> {actual}"
                raise PdfaError(msg)
        xml = document.get_xml_metadata()
        if not _pdfa_claim(xml, part):
            raise PdfaError(f"Output does not declare PDF/A-{part}b in XMP metadata.")
        kind, value = document.xref_get_key(document.pdf_catalog(), "OutputIntents")
        if kind != "array" or value.strip() == "[]":
            raise PdfaError(
                "Output has no PDF/A OutputIntent with an embedded ICC profile."
            )
        output_text = "".join(page.get_text() for page in document)
        similarity: float | None = None
        if input_text and not rasterized:
            similarity = difflib.SequenceMatcher(
                None,
                _normalized_text(input_text),
                _normalized_text(output_text),
                autojunk=False,
            ).ratio()
            if similarity < TEXT_SIMILARITY_FLOOR:
                msg = (
                    f"Searchable text changed materially (similarity {similarity:.3f})."
                )
                raise PdfaError(msg)
        return Verification(
            pages=document.page_count,
            pdf_format=document.metadata.get("format", "unknown"),
            text_similarity=similarity,
            verapdf="not run",
        )


def _native_verapdf() -> str | None:
    """Find the official veraPDF launcher on PATH."""
    names = (
        ("verapdf.bat", "verapdf.cmd", "verapdf")
        if sys.platform == "win32"
        else ("verapdf",)
    )
    return next((path for name in names if (path := shutil.which(name))), None)


def _wsl_verapdf_available() -> bool:
    """Return whether the default WSL distribution exposes veraPDF."""
    if not _wsl_available():
        return False
    result = _run(
        ["wsl.exe", "-e", "sh", "-lc", "command -v verapdf >/dev/null 2>&1"],
        check=False,
    )
    return result.returncode == 0


def _run_verapdf(output_path: Path, *, part: int, required: bool) -> str:
    """Validate with veraPDF when present and parse its compliance result."""
    flavour = f"{part}b"
    launcher = _native_verapdf()
    if launcher is not None:
        command = [launcher, "-f", flavour, str(output_path)]
        if Path(launcher).suffix.lower() in {".bat", ".cmd"}:
            command = ["cmd.exe", "/d", "/s", "/c", *command]
        result = _run(command, check=False)
    elif _wsl_verapdf_available():
        result = _run(
            ["wsl.exe", "-e", "verapdf", "-f", flavour, _wsl_path(output_path)],
            check=False,
        )
    else:
        if required:
            raise PdfaError(
                "veraPDF is required but was not found. Install the official Java CLI and add "
                "`verapdf` (`verapdf.bat` on Windows) to PATH."
            )
        return "not installed; structural checks only"

    report = f"{result.stdout}\n{result.stderr}"
    if 'isCompliant="true"' not in report:
        raise PdfaError(f"veraPDF rejected PDF/A-{flavour}:\n{report.strip()}")
    return f"compliant with PDF/A-{flavour}"


def _try_pikepdf(
    source: Path,
    candidate: Path,
    *,
    part: int,
    backend: BackendChoice,
    creation_date: datetime | None,
) -> tuple[str | None, tuple[str, ...], tuple[str, ...]]:
    """Promote with pikepdf; return (backend used or None to fall back, unchecked, notes)."""
    if backend not in ("auto", "pikepdf"):
        return None, (), ()
    try:
        result = convert_pikepdf(source, candidate, part=part, creation_date=creation_date)
    except Exception as error:  # noqa: BLE001 - any pikepdf failure means "use Ghostscript"
        if backend == "pikepdf":
            raise PdfaError(f"pikepdf promotion failed: {error}") from error
        candidate.unlink(missing_ok=True)
        return None, (), (f"pikepdf failed ({error}); fell back to Ghostscript",)
    if result.blocking:
        candidate.unlink(missing_ok=True)
        listing = "\n".join(f"  - {finding}" for finding in result.blocking)
        if backend == "pikepdf":
            raise PdfaError(f"pikepdf found PDF/A-{part}b violations or undecided rules:\n{listing}")
        note = f"pikepdf found {len(result.blocking)} blocking finding(s); fell back to Ghostscript:\n{listing}"
        return None, (), (note,)
    return "pikepdf (no Ghostscript)", result.unchecked, result.changes


def convert(
    input_path: Path,
    output_path: Path,
    *,
    part: int,
    policy: int,
    backend: BackendChoice,
    ghostscript: str | None,
    rasterize: bool,
    dpi: int,
    require_verapdf: bool,
    allow_signed: bool,
    creation_date: datetime | None = None,
) -> Verification:
    """Convert atomically and expose the final file only after verification."""
    pages, sizes, input_text = _preflight(input_path, allow_signed=allow_signed)
    with tempfile.TemporaryDirectory(prefix="convert_to_pdfa_") as temp_dir_value:
        temp_dir = Path(temp_dir_value)
        source = input_path
        if rasterize:
            source = temp_dir / "rasterized.pdf"
            _rasterize(input_path, source, dpi=dpi)
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent,
            prefix=f".{output_path.stem}.",
            suffix=".candidate.pdf",
            delete=False,
        ) as candidate_file:
            candidate = Path(candidate_file.name)
        candidate.unlink()
        try:
            used, unchecked, notes = _try_pikepdf(
                source, candidate, part=part, backend=backend, creation_date=creation_date
            )
            if used is None:
                gs_backend: Backend
                if backend in ("auto", "pikepdf"):
                    gs_backend, ghostscript = _select_backend("auto")
                else:
                    gs_backend = backend
                if gs_backend == "native":
                    if ghostscript is None:
                        raise PdfaError("Internal error: missing native Ghostscript path.")
                    _convert_native(
                        ghostscript, source, candidate, part=part, policy=policy
                    )
                else:
                    _convert_wsl(source, candidate, part=part, policy=policy)
                _ghostscript_parse(gs_backend, ghostscript, candidate)
                used = f"ghostscript ({gs_backend})"
            verification = _structural_verify(
                candidate,
                expected_pages=pages,
                expected_sizes=sizes,
                input_text=input_text,
                part=part,
                rasterized=rasterize,
            )
            verapdf = _run_verapdf(candidate, part=part, required=require_verapdf)
            candidate.replace(output_path)
            return Verification(
                pages=verification.pages,
                pdf_format=verification.pdf_format,
                text_similarity=verification.text_similarity,
                verapdf=verapdf,
                backend=used,
                unchecked=unchecked,
                notes=notes,
            )
        finally:
            candidate.unlink(missing_ok=True)


app = cyclopts.App(name="convert-to-pdfa", help=__doc__)


@app.default
def main(
    input_path: Annotated[Path, Parameter(name=["INPUT", "--input"])],
    *,
    output: Path | None = None,
    part: Literal[1, 2, 3] = 2,
    backend: BackendChoice = "auto",
    compatibility_policy: Literal[1, 2] = 2,
    rasterize: bool = False,
    dpi: int = 300,
    require_verapdf: bool = False,
    allow_signed: bool = False,
    force: bool = False,
    creation_date: str | None = None,
) -> int:
    """Convert one PDF to PDF/A.

    Parameters
    ----------
    input_path
        source PDF.
    output
        destination; defaults to <name>-PDFA.pdf.
    part
        PDF/A part to target.
    backend
        auto tries pikepdf first and falls back to Ghostscript (native, then WSL) on violations;
        pikepdf fails instead of falling back; native/wsl force Ghostscript.
    compatibility_policy
        2 aborts on incompatible content; 1 drops incompatible operations with warnings.
    rasterize
        flatten pages before conversion; destroys searchable text, links, and signatures.
    dpi
        raster fallback resolution.
    require_verapdf
        fail unless the official veraPDF CLI confirms compliance.
    allow_signed
        convert despite signature fields; the new file will not retain signature validity.
    force
        replace an existing output after validation.
    creation_date
        ISO 8601 date written as /CreationDate when the source has none (pikepdf path); default now.
    """
    try:
        if dpi < 72 or dpi > 600:
            raise PdfaError("--dpi must be between 72 and 600.")
        resolved_input, output_path = _resolve_paths(
            str(input_path), str(output) if output else None, force=force
        )
        when = datetime.fromisoformat(creation_date) if creation_date else None
        ghostscript = None
        if backend in ("native", "wsl"):
            backend, ghostscript = _select_backend(backend)
        verification = convert(
            resolved_input,
            output_path,
            part=part,
            policy=compatibility_policy,
            backend=backend,
            ghostscript=ghostscript,
            rasterize=rasterize,
            dpi=dpi,
            require_verapdf=require_verapdf,
            allow_signed=allow_signed,
            creation_date=when,
        )
    except (PdfaError, ValueError, pymupdf.FileDataError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Created: {output_path}")
    print(f"Backend: {verification.backend}")
    for note in verification.notes:
        print(f"Note: {note}")
    for item in verification.unchecked:
        print(f"Não verificado pelo pikepdf: {item}")
    print(f"Format: PDF/A-{part}b ({verification.pdf_format})")
    print(f"Pages: {verification.pages}")
    if rasterize:
        print(
            f"Text: rasterized at {dpi} DPI (search layer intentionally removed)"
        )
    elif verification.text_similarity is None:
        print("Text: source had no extractable text")
    else:
        print(f"Text similarity: {verification.text_similarity:.3f}")
    print(f"veraPDF: {verification.verapdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(app() or 0)
