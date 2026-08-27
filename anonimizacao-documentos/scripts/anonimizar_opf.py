#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "opf @ git+https://github.com/openai/privacy-filter.git@f7f00ca7fb869683eb732c010299d901457f19c3",
#     "torch",
# ]
# ///
"""Detect PII with OpenAI Privacy Filter and create reviewed/anonymized copies."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anonimizar import anonymize_tagged_text

DEFAULT_INPUT_DIR = Path("/content/input")
DEFAULT_OUTPUT_DIR = Path("/content/output")
DRIVE_CACHE_MARKER = Path("/content/.opf-use-drive-cache")
DRIVE_CHECKPOINT = Path(
    "/content/drive/MyDrive/.cache/openai/privacy-filter",
)
DEFAULT_CHECKPOINT = Path.home() / ".opf" / "privacy_filter"
SUPPORTED_SUFFIXES = {".md", ".txt"}

MODEL_LABEL_TO_TYPE = {
    "account_number": "identificador_conta",
    "private_address": "endereco",
    "private_email": "contato_email",
    "private_person": "nome_pessoa",
    "private_phone": "contato_telefone",
    "private_url": "url_privada",
    "private_date": "data_privada",
    "secret": "segredo",
}
CPF_PATTERN = re.compile(
    r"(?<!\d)(?:\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\*{3}\.\d{3}\.\d{3}\.\*{2})(?!\d)"
)
CNJ_PATTERN = re.compile(r"(?<!\d)\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}(?!\d)")


class OpfAnonymizationError(RuntimeError):
    """Raised when model-assisted anonymization cannot be applied safely."""


@dataclass(frozen=True)
class Span:
    """One detected character span."""

    start: int
    end: int
    pii_type: str
    source: str
    score: float = 1.0

    def overlaps(self, other: Span) -> bool:
        return self.start < other.end and other.start < self.end


def find_colab_input() -> Path:
    candidates = sorted(
        path
        for path in DEFAULT_INPUT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if len(candidates) != 1:
        names = ", ".join(path.name for path in candidates) or "none"
        raise OpfAnonymizationError(
            f"Expected exactly one Markdown/text file in {DEFAULT_INPUT_DIR}; found {names}."
        )
    return candidates[0]


def load_hf_token_from_colab_secret() -> None:
    """Load an optional HF token without printing or persisting it."""
    if os.environ.get("HF_TOKEN"):
        return
    try:
        from google.colab import userdata
    except ImportError:
        return
    try:
        token = userdata.get("HF_TOKEN")
    except Exception:  # noqa: BLE001 - Colab secret backends vary by runtime.
        return
    if token:
        os.environ["HF_TOKEN"] = token


def checkpoint_is_complete(path: Path) -> bool:
    return (path / "config.json").is_file() and any(path.glob("*.safetensors"))


def select_checkpoint(explicit: Path | None) -> tuple[Path | None, bool]:
    """Choose an existing checkpoint and whether to cache the first download."""
    if explicit is not None:
        if not checkpoint_is_complete(explicit):
            raise OpfAnonymizationError(f"Incomplete OPF checkpoint: {explicit}")
        return explicit, False
    if DRIVE_CACHE_MARKER.is_file() and checkpoint_is_complete(DRIVE_CHECKPOINT):
        return DRIVE_CHECKPOINT, False
    should_cache = DRIVE_CACHE_MARKER.is_file() and DRIVE_CHECKPOINT.parent.is_dir()
    return None, should_cache


def cache_default_checkpoint() -> None:
    """Copy a complete first-use download to Drive for later Colab sessions."""
    if checkpoint_is_complete(DRIVE_CHECKPOINT):
        return
    if not checkpoint_is_complete(DEFAULT_CHECKPOINT):
        raise OpfAnonymizationError(
            f"Cannot cache incomplete default checkpoint: {DEFAULT_CHECKPOINT}"
        )

    DRIVE_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    partial = DRIVE_CHECKPOINT.with_name(
        f"{DRIVE_CHECKPOINT.name}.partial-{uuid.uuid4().hex}"
    )
    try:
        shutil.copytree(DEFAULT_CHECKPOINT, partial)
        if DRIVE_CHECKPOINT.exists():
            raise OpfAnonymizationError(
                f"Drive checkpoint appeared during copy: {DRIVE_CHECKPOINT}"
            )
        partial.replace(DRIVE_CHECKPOINT)
    except (OSError, OpfAnonymizationError):
        shutil.rmtree(partial, ignore_errors=True)
        raise


def deterministic_spans(text: str) -> list[Span]:
    spans: list[Span] = []
    for match in CPF_PATTERN.finditer(text):
        spans.append(Span(match.start(), match.end(), "cpf", "regex"))
    for match in CNJ_PATTERN.finditer(text):
        spans.append(Span(match.start(), match.end(), "processo_judicial", "regex"))
    return spans


def model_spans(result: Any) -> list[Span]:
    spans: list[Span] = []
    for detected in result.detected_spans:
        pii_type = MODEL_LABEL_TO_TYPE.get(detected.label)
        if pii_type is None:
            continue
        spans.append(
            Span(
                start=int(detected.start),
                end=int(detected.end),
                pii_type=pii_type,
                source="opf",
            )
        )
    return spans


def merge_spans(candidates: list[Span]) -> list[Span]:
    """Prefer deterministic identifiers, then longer model spans."""
    priority = {"regex": 1, "opf": 0}
    ranked = sorted(
        candidates,
        key=lambda span: (
            priority.get(span.source, 0),
            span.score,
            span.end - span.start,
        ),
        reverse=True,
    )
    accepted: list[Span] = []
    for candidate in ranked:
        if candidate.start < 0 or candidate.end <= candidate.start:
            continue
        if not any(candidate.overlaps(existing) for existing in accepted):
            accepted.append(candidate)
    return sorted(accepted, key=lambda span: (span.start, span.end))


def tag_text(text: str, spans: list[Span]) -> tuple[str, Counter[str]]:
    """Wrap non-overlapping spans and assign stable references by value."""
    counter_by_type: Counter[str] = Counter()
    reference_by_value: dict[tuple[str, str], int] = {}
    replacements: list[tuple[int, int, str]] = []

    for span in spans:
        raw_value = text[span.start : span.end]
        normalized_value = " ".join(raw_value.casefold().split())
        key = (span.pii_type, normalized_value)
        if key not in reference_by_value:
            counter_by_type[span.pii_type] += 1
            reference_by_value[key] = counter_by_type[span.pii_type]
        reference = reference_by_value[key]
        tagged = f"<pii tipo='{span.pii_type}' ref='{reference}'>{raw_value}</pii>"
        replacements.append((span.start, span.end, tagged))

    tagged_text = text
    for start, end, replacement in reversed(replacements):
        tagged_text = f"{tagged_text[:start]}{replacement}{tagged_text[end:]}"
    counts = Counter(span.pii_type for span in spans)
    return tagged_text, counts


def output_paths(input_path: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    base = input_path.stem
    return (
        output_dir / f"{base}.tagged.md",
        output_dir / f"{base}.anon.md",
        output_dir / f"{base}.opf-report.json",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect PII with OpenAI Privacy Filter and preserve review artifacts."
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input or find_colab_input()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if input_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise OpfAnonymizationError(f"Unsupported input type: {input_path.suffix}")

    output_dir = args.output_dir
    if output_dir is None:
        output_dir = (
            DEFAULT_OUTPUT_DIR
            if input_path.parent == DEFAULT_INPUT_DIR
            else input_path.parent
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    tagged_path, anonymized_path, report_path = output_paths(input_path, output_dir)
    for path in (tagged_path, anonymized_path, report_path):
        if path.exists() and not args.force:
            raise FileExistsError(f"Output already exists: {path}")

    load_hf_token_from_colab_secret()
    try:
        import torch
        from opf import OPF
    except ImportError as error:
        raise OpfAnonymizationError(
            "Install the official OPF package before running this script."
        ) from error

    device = args.device
    if device == "cuda" and not torch.cuda.is_available():
        raise OpfAnonymizationError("CUDA requested, but PyTorch cannot access a GPU.")
    if device == "cpu":
        print(
            "WARNING: OPF on CPU is much slower than GPU and may require substantial RAM.",
            file=sys.stderr,
        )

    checkpoint, should_cache = select_checkpoint(args.checkpoint)
    redactor = OPF(
        model=str(checkpoint) if checkpoint else None,
        device=device,
        output_mode="typed",
    )
    text = input_path.read_text(encoding="utf-8")
    result = redactor.redact(text)
    if isinstance(result, str):
        raise OpfAnonymizationError("OPF returned text-only output unexpectedly.")
    if result.warning:
        raise OpfAnonymizationError(
            f"Tokenizer round-trip mismatch; refusing offset replacement: {result.warning}"
        )
    if result.text != text:
        raise OpfAnonymizationError(
            "OPF changed the input during tokenization; refusing offset replacement."
        )

    spans = merge_spans([*deterministic_spans(text), *model_spans(result)])
    tagged_text, counts = tag_text(text, spans)
    anonymized_text, substitutions = anonymize_tagged_text(tagged_text)
    tagged_path.write_text(tagged_text, encoding="utf-8")
    anonymized_path.write_text(anonymized_text, encoding="utf-8")

    if should_cache:
        cache_default_checkpoint()

    report = {
        "model": "openai/privacy-filter",
        "device": device,
        "input": str(input_path),
        "tagged_output": str(tagged_path),
        "anonymized_output": str(anonymized_path),
        "span_count": len(spans),
        "substitution_count": substitutions,
        "by_type": dict(sorted(counts.items())),
        "checkpoint": str(checkpoint) if checkpoint else str(DEFAULT_CHECKPOINT),
        "drive_cache_written": should_cache,
        "warning": (
            "Detection aid only; review false negatives and over-redaction manually."
        ),
    }
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (
        FileExistsError,
        FileNotFoundError,
        OSError,
        OpfAnonymizationError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
