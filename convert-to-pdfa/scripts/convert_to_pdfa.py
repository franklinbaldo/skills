"""Convert a PDF to PDF/A-1b, PDF/A-2b, or PDF/A-3b.

Ghostscript performs the standards-aware conversion. PyMuPDF provides
preflight checks, an explicit raster fallback, and structural verification.
veraPDF is used when its official CLI is available.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pymupdf

if TYPE_CHECKING:
    from collections.abc import Sequence

Backend = Literal["native", "wsl"]
SUPPORTED_PARTS = (1, 2, 3)
PAGE_SIZE_TOLERANCE = 0.05
TEXT_SIMILARITY_FLOOR = 0.98
WSL_GS_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail

input=$1
output=$2
part=$3
policy=$4

version="$(gs --version)"
pdfa_def=""
for candidate in \
  "/usr/share/ghostscript/$version/lib/PDFA_def.ps" \
  "/usr/local/share/ghostscript/$version/lib/PDFA_def.ps" \
  "/opt/homebrew/share/ghostscript/$version/lib/PDFA_def.ps"; do
  if [[ -f "$candidate" ]]; then
    pdfa_def="$candidate"
    break
  fi
done

icc=""
for candidate in \
  "/usr/share/color/icc/ghostscript/srgb.icc" \
  "/usr/local/share/color/icc/ghostscript/srgb.icc" \
  "/opt/homebrew/share/color/icc/ghostscript/srgb.icc" \
  "/usr/share/ghostscript/$version/iccprofiles/default_rgb.icc"; do
  if [[ -f "$candidate" ]]; then
    icc="$candidate"
    break
  fi
done

if [[ -z "$pdfa_def" || -z "$icc" ]]; then
  echo "Ghostscript PDF/A resources not found (PDFA_def.ps and sRGB ICC)." >&2
  exit 4
fi

prefix="$(mktemp --suffix=.ps)"
trap 'rm -f "$prefix"' EXIT
sed \
  -e '/\[ \/Title (Title)/,/\/DOCINFO pdfmark/d' \
  -e "s|/ICCProfile ([^)]*)|/ICCProfile ($icc)|" \
  "$pdfa_def" >"$prefix"

gs \
  "-dPDFA=$part" \
  -dBATCH \
  -dNOPAUSE \
  -dNOOUTERSAVE \
  -dAutoRotatePages=/None \
  -dEmbedAllFonts=true \
  -dSubsetFonts=true \
  -sDEVICE=pdfwrite \
  "-dPDFACompatibilityPolicy=$policy" \
  -sColorConversionStrategy=RGB \
  -sProcessColorModel=DeviceRGB \
  "-sOutputFile=$output" \
  "--permit-file-read=$icc" \
  "$prefix" \
  "$input"
"""


class PdfaError(RuntimeError):
    """Raised when conversion or validation cannot complete safely."""


@dataclass(frozen=True)
class Verification:
    """Verification facts reported after conversion."""

    pages: int
    pdf_format: str
    text_similarity: float | None
    verapdf: str


def _run(
    command: Sequence[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess without a shell and retain diagnostic output."""
    result = subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        details = "\n".join(
            part.strip() for part in (result.stdout, result.stderr) if part.strip()
        )
        msg = f"Command failed ({result.returncode}): {' '.join(command)}"
        if details:
            msg = f"{msg}\n{details}"
        raise PdfaError(msg)
    return result


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


def _native_ghostscript() -> str | None:
    """Find a native Ghostscript executable."""
    names = ("gswin64c", "gswin32c", "gs") if sys.platform == "win32" else ("gs",)
    return next((path for name in names if (path := shutil.which(name))), None)


def _wsl_available() -> bool:
    """Return whether Windows has WSL with Ghostscript installed."""
    if sys.platform != "win32" or shutil.which("wsl.exe") is None:
        return False
    result = _run(
        ["wsl.exe", "-e", "sh", "-lc", "command -v gs >/dev/null 2>&1"],
        check=False,
    )
    return result.returncode == 0


def _select_backend(requested: str) -> tuple[Backend, str | None]:
    """Choose native Ghostscript first, then WSL on Windows."""
    native = _native_ghostscript()
    if requested == "native":
        if native is None:
            raise PdfaError(_ghostscript_install_hint())
        return "native", native
    if requested == "wsl":
        if not _wsl_available():
            raise PdfaError(
                "WSL is unavailable or its distribution does not have `gs` installed."
            )
        return "wsl", None
    if native is not None:
        return "native", native
    if _wsl_available():
        return "wsl", None
    raise PdfaError(_ghostscript_install_hint())


def _ghostscript_install_hint() -> str:
    """Return platform-specific installation guidance."""
    if sys.platform == "win32":
        return (
            "Ghostscript was not found. Install the official 64-bit Windows build and add "
            "`gswin64c.exe` to PATH, or install it in WSL with "
            "`sudo apt-get update && sudo apt-get install -y ghostscript`."
        )
    if sys.platform == "darwin":
        return "Ghostscript was not found. Install it with `brew install ghostscript`."
    return (
        "Ghostscript was not found. Install it with your package manager, for example "
        "`sudo apt-get install ghostscript`, `sudo dnf install ghostscript`, or "
        "`sudo pacman -S ghostscript`."
    )


def _native_support_files(ghostscript: str) -> tuple[Path, Path]:
    """Locate Ghostscript's PDF/A definition and an sRGB ICC profile."""
    version = _run([ghostscript, "--version"]).stdout.strip()
    executable = Path(ghostscript).resolve()
    install_root = executable.parent.parent
    roots = [
        install_root,
        Path("/usr/share/ghostscript") / version,
        Path("/usr/local/share/ghostscript") / version,
        Path("/opt/homebrew/share/ghostscript") / version,
    ]
    pdfa_candidates = [root / "lib" / "PDFA_def.ps" for root in roots]
    icc_candidates = [
        install_root / "iccprofiles" / "srgb.icc",
        install_root / "iccprofiles" / "default_rgb.icc",
        Path("/usr/share/color/icc/ghostscript/srgb.icc"),
        Path("/usr/local/share/color/icc/ghostscript/srgb.icc"),
        Path("/opt/homebrew/share/color/icc/ghostscript/srgb.icc"),
    ]
    pdfa_def = next((path for path in pdfa_candidates if path.is_file()), None)
    icc = next((path for path in icc_candidates if path.is_file()), None)
    if pdfa_def is None or icc is None:
        raise PdfaError(
            "Ghostscript is installed, but PDFA_def.ps or an sRGB ICC profile was not found."
        )
    return pdfa_def, icc


def _postscript_path(path: Path) -> str:
    """Encode an absolute path for a PostScript string."""
    return path.as_posix().replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _patched_pdfa_definition(pdfa_def: Path, icc: Path, destination: Path) -> None:
    """Create a temporary PDFA_def.ps with a fully qualified ICC path."""
    text = pdfa_def.read_text(encoding="latin-1")
    text, replacements = re.subn(
        r"/ICCProfile\s+\([^)]*\)",
        f"/ICCProfile ({_postscript_path(icc)})",
        text,
        count=1,
    )
    if replacements != 1:
        raise PdfaError(f"Could not patch ICCProfile in {pdfa_def}")
    text = re.sub(
        r"\[\s*/Title\s+\(Title\).*?/DOCINFO\s+pdfmark",
        "",
        text,
        count=1,
        flags=re.DOTALL,
    )
    destination.write_text(text, encoding="latin-1", newline="\n")


def _convert_native(
    ghostscript: str,
    input_path: Path,
    output_path: Path,
    *,
    part: int,
    policy: int,
) -> None:
    """Convert through a native Ghostscript installation."""
    pdfa_def, icc = _native_support_files(ghostscript)
    with tempfile.TemporaryDirectory(prefix="convert_to_pdfa_") as temp_dir:
        prefix = Path(temp_dir) / "PDFA_def.ps"
        _patched_pdfa_definition(pdfa_def, icc, prefix)
        _run(
            [
                ghostscript,
                f"-dPDFA={part}",
                "-dBATCH",
                "-dNOPAUSE",
                "-dNOOUTERSAVE",
                "-dAutoRotatePages=/None",
                "-dEmbedAllFonts=true",
                "-dSubsetFonts=true",
                "-sDEVICE=pdfwrite",
                f"-dPDFACompatibilityPolicy={policy}",
                "-sColorConversionStrategy=RGB",
                "-sProcessColorModel=DeviceRGB",
                f"-sOutputFile={output_path}",
                f"--permit-file-read={icc}",
                str(prefix),
                str(input_path),
            ]
        )


def _wsl_path(path: Path) -> str:
    """Translate a Windows path for the default WSL distribution."""
    result = _run(["wsl.exe", "-e", "wslpath", "-a", "-u", str(path)])
    return result.stdout.strip()


def _convert_wsl(
    input_path: Path,
    output_path: Path,
    *,
    part: int,
    policy: int,
) -> None:
    """Convert through Ghostscript installed in WSL."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".sh",
        prefix="convert_to_pdfa_",
        encoding="utf-8",
        newline="\n",
        delete=False,
    ) as script_file:
        script_file.write(WSL_GS_SCRIPT)
        script_path = Path(script_file.name)
    try:
        _run(
            [
                "wsl.exe",
                "-e",
                "bash",
                _wsl_path(script_path),
                _wsl_path(input_path),
                _wsl_path(output_path),
                str(part),
                str(policy),
            ]
        )
    finally:
        script_path.unlink(missing_ok=True)


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


def convert(
    input_path: Path,
    output_path: Path,
    *,
    part: int,
    policy: int,
    backend: Backend,
    ghostscript: str | None,
    rasterize: bool,
    dpi: int,
    require_verapdf: bool,
    allow_signed: bool,
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
            if backend == "native":
                if ghostscript is None:
                    raise PdfaError("Internal error: missing native Ghostscript path.")
                _convert_native(
                    ghostscript, source, candidate, part=part, policy=policy
                )
            else:
                _convert_wsl(source, candidate, part=part, policy=policy)
            _ghostscript_parse(backend, ghostscript, candidate)
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
            )
        finally:
            candidate.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="source PDF")
    parser.add_argument("--output", help="destination; defaults to <name>-PDFA.pdf")
    parser.add_argument("--part", type=int, choices=SUPPORTED_PARTS, default=2)
    parser.add_argument(
        "--backend",
        choices=("auto", "native", "wsl"),
        default="auto",
        help="Ghostscript backend; auto prefers native and falls back to WSL on Windows",
    )
    parser.add_argument(
        "--compatibility-policy",
        type=int,
        choices=(1, 2),
        default=2,
        help="2 aborts on incompatible content; 1 drops incompatible operations with warnings",
    )
    parser.add_argument(
        "--rasterize",
        action="store_true",
        help="flatten pages before conversion; destroys searchable text, links, and signatures",
    )
    parser.add_argument(
        "--dpi", type=int, default=300, help="raster fallback resolution"
    )
    parser.add_argument(
        "--require-verapdf",
        action="store_true",
        help="fail unless the official veraPDF CLI confirms compliance",
    )
    parser.add_argument(
        "--allow-signed",
        action="store_true",
        help="convert despite signature fields; the new file will not retain signature validity",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output after validation",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = _parser().parse_args(argv)
    try:
        if args.dpi < 72 or args.dpi > 600:
            raise PdfaError("--dpi must be between 72 and 600.")
        input_path, output_path = _resolve_paths(
            args.input, args.output, force=args.force
        )
        backend, ghostscript = _select_backend(args.backend)
        verification = convert(
            input_path,
            output_path,
            part=args.part,
            policy=args.compatibility_policy,
            backend=backend,
            ghostscript=ghostscript,
            rasterize=args.rasterize,
            dpi=args.dpi,
            require_verapdf=args.require_verapdf,
            allow_signed=args.allow_signed,
        )
    except (PdfaError, pymupdf.FileDataError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Created: {output_path}")
    print(f"Format: PDF/A-{args.part}b ({verification.pdf_format})")
    print(f"Pages: {verification.pages}")
    if args.rasterize:
        print(
            f"Text: rasterized at {args.dpi} DPI (search layer intentionally removed)"
        )
    elif verification.text_similarity is None:
        print("Text: source had no extractable text")
    else:
        print(f"Text similarity: {verification.text_similarity:.3f}")
    print(f"veraPDF: {verification.verapdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
