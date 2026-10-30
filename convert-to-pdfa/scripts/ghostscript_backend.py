# /// script
# requires-python = ">=3.11"
# ///
"""Find and run Ghostscript for PDF/A conversion: native, Scoop shim, or WSL.

Holds everything that depends on where Ghostscript lives: backend choice, the
PDF/A definition and sRGB ICC lookup, and the conversion call itself.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

Backend = Literal["native", "wsl"]

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
        encoding="utf-8",
        errors="replace",
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


def _scoop_target(executable: Path) -> Path:
    """Follow a Scoop shim (`gswin64c.exe` + `gswin64c.shim`) to the real install's executable."""
    shim = executable.with_suffix(".shim")
    if not shim.is_file():
        return executable
    for line in shim.read_text(encoding="utf-8", errors="replace").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "path" and value.strip():
            return Path(value.strip().strip('"'))
    return executable


def _native_support_files(ghostscript: str) -> tuple[Path, Path]:
    """Locate Ghostscript's PDF/A definition and an sRGB ICC profile."""
    version = _run([ghostscript, "--version"]).stdout.strip()
    executable = _scoop_target(Path(ghostscript).resolve())
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

