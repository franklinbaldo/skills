#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
# ]
# ///
"""Install a pinned OpenAI Privacy Filter package in a Colab runtime."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

OPF_COMMIT = "f7f00ca7fb869683eb732c010299d901457f19c3"
OPF_SPEC = f"opf @ git+https://github.com/openai/privacy-filter.git@{OPF_COMMIT}"
DRIVE_ROOT = Path("/content/drive/MyDrive")
DRIVE_CACHE_MARKER = Path("/content/.opf-use-drive-cache")


def main() -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required; current Colab runtimes include it.")
    subprocess.run(
        [uv, "pip", "install", "--system", OPF_SPEC],
        check=True,
    )
    Path("/content/input").mkdir(parents=True, exist_ok=True)
    Path("/content/output").mkdir(parents=True, exist_ok=True)
    if DRIVE_ROOT.is_dir():
        DRIVE_CACHE_MARKER.touch()
        print("Google Drive checkpoint cache enabled.")
    print(f"Installed OpenAI Privacy Filter from commit {OPF_COMMIT}.")


if __name__ == "__main__":
    main()
