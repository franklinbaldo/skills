#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
# ]
# ///
"""Install PaddleOCR with GPU support in a dedicated Google Colab VM."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PADDLE_INDEX = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"
PADDLE_VERSION = "3.3.0"
PADDLEOCR_SPEC = "paddleocr>=3.7,<4"


def main() -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required; current Colab runtimes include it.")

    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--system",
            "--index-url",
            PADDLE_INDEX,
            f"paddlepaddle-gpu=={PADDLE_VERSION}",
        ],
        check=True,
    )
    subprocess.run(
        [uv, "pip", "install", "--system", PADDLEOCR_SPEC],
        check=True,
    )

    # Paddle's CUDA wheel can replace NCCL with a build incompatible with
    # Colab's PyTorch. PaddleOCR's native engine does not require PyTorch, but
    # an optional ModelScope probe imports it whenever it is installed.
    subprocess.run(
        [
            uv,
            "pip",
            "uninstall",
            "--system",
            "torch",
            "torchvision",
            "torchaudio",
        ],
        check=False,
    )

    Path("/content/input").mkdir(parents=True, exist_ok=True)
    Path("/content/output").mkdir(parents=True, exist_ok=True)
    print("PaddleOCR GPU stack installed. Restart the kernel before OCR.")


if __name__ == "__main__":
    main()
