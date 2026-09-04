#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
# ]
# ///
"""Create a private Kaggle GPU script job without overwriting user files."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import cyclopts

OWNER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")


class KaggleJobError(ValueError):
    """Raised when a safe Kaggle job cannot be created."""


def validate_slug(value: str, label: str) -> str:
    if not SLUG_PATTERN.fullmatch(value):
        raise KaggleJobError(
            f"{label} must use lowercase letters, digits, and hyphens: {value!r}"
        )
    return value


def validate_owner(value: str) -> str:
    if not OWNER_PATTERN.fullmatch(value):
        raise KaggleJobError(
            f"owner must use letters, digits, underscores, and hyphens: {value!r}"
        )
    return value


def build_metadata(
    *,
    owner: str,
    slug: str,
    title: str,
    code_file: str,
    accelerator: str,
    internet: bool,
) -> dict[str, object]:
    return {
        "id": f"{owner}/{slug}",
        "title": title,
        "code_file": code_file,
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": internet,
        "machine_shape": accelerator,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }


app = cyclopts.App(name="create-kaggle-job", help=__doc__)


@app.default
def main(
    script: Path,
    *,
    owner: str,
    slug: str,
    output_dir: Path,
    title: str | None = None,
    accelerator: str = "NvidiaTeslaT4",
    internet: bool = False,
) -> int:
    """Create the job directory.

    Parameters
    ----------
    script
        The single Python script to run on Kaggle.
    owner
        Kaggle username that owns the kernel.
    slug
        Kernel slug.
    output_dir
        Directory to create; must not exist yet.
    title
        Kernel title (defaults to the slug, title-cased).
    accelerator
        Kaggle accelerator name.
    internet
        Enable internet access for the kernel.
    """
    if not script.is_file() or script.suffix.lower() != ".py":
        raise KaggleJobError("The input must be one Python script.")
    owner = validate_owner(owner)
    slug = validate_slug(slug, "slug")
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing job directory: {output_dir}"
        )

    output_dir.mkdir(parents=True)
    code_path = output_dir / "job.py"
    metadata_path = output_dir / "kernel-metadata.json"
    shutil.copy2(script, code_path)
    metadata = build_metadata(
        owner=owner,
        slug=slug,
        title=title or slug.replace("-", " ").title(),
        code_file=code_path.name,
        accelerator=accelerator,
        internet=internet,
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Kaggle job: {output_dir}")
    print(f"Kernel: {owner}/{slug}")
    print(
        "Push with: uvx --from kaggle kaggle kernels push "
        f'-p "{output_dir}" --accelerator {accelerator}'
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(app())
    except (FileExistsError, KaggleJobError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
