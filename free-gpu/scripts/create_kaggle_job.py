"""Create a private Kaggle GPU script job without overwriting user files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--accelerator", default="NvidiaTeslaT4")
    parser.add_argument("--internet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.script.is_file() or args.script.suffix.lower() != ".py":
        raise KaggleJobError("The input must be one Python script.")
    owner = validate_owner(args.owner)
    slug = validate_slug(args.slug, "slug")
    if args.output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing job directory: {args.output_dir}"
        )

    args.output_dir.mkdir(parents=True)
    code_path = args.output_dir / "job.py"
    metadata_path = args.output_dir / "kernel-metadata.json"
    shutil.copy2(args.script, code_path)
    metadata = build_metadata(
        owner=owner,
        slug=slug,
        title=args.title or slug.replace("-", " ").title(),
        code_file=code_path.name,
        accelerator=args.accelerator,
        internet=args.internet,
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Kaggle job: {args.output_dir}")
    print(f"Kernel: {owner}/{slug}")
    print(
        "Push with: uvx --from kaggle kaggle kernels push "
        f'-p "{args.output_dir}" --accelerator {args.accelerator}'
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (FileExistsError, KaggleJobError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
