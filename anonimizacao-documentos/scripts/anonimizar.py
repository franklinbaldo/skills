#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
# ]
# ///
"""Replace reviewed PII tags with deterministic canonical markers."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CANONICAL_TYPES = {
    "assinatura_signatario": "ASSINATURA_SIGNATARIO",
    "contato": "CONTATO",
    "contato_email": "CONTATO_EMAIL",
    "contato_telefone": "CONTATO_TELEFONE",
    "cpf": "CPF",
    "dado_saude": "DADO_SAUDE",
    "data_nascimento": "DATA_NASCIMENTO",
    "data_privada": "DATA_PRIVADA",
    "endereco": "ENDERECO",
    "identificador_conta": "IDENTIFICADOR_CONTA",
    "matricula_servidor": "MATRICULA_SERVIDOR",
    "nome_pessoa": "NOME_PESSOA",
    "oab": "OAB",
    "processo_judicial": "PROCESSO_JUDICIAL",
    "rg": "RG",
    "segredo": "SEGREDO",
    "url_privada": "URL_PRIVADA",
}
TAG_TOKEN_PATTERN = re.compile(r"</?pii\b[^>]*>", re.IGNORECASE)
PII_PATTERN = re.compile(
    r"<pii\b(?P<attrs>[^>]*)>(?P<value>.*?)</pii\s*>",
    re.DOTALL | re.IGNORECASE,
)
ATTRIBUTE_PATTERN = re.compile(
    r"\b(?P<name>tipo|ref)\s*=\s*['\"](?P<value>[^'\"]+)['\"]",
    re.IGNORECASE,
)


class AnonymizationError(ValueError):
    """Raised when reviewed PII markup is structurally unsafe."""


def normalize_type(raw_type: str) -> str:
    """Return the canonical uppercase marker type."""
    normalized = raw_type.strip().lower()
    if normalized in CANONICAL_TYPES:
        return CANONICAL_TYPES[normalized]
    return re.sub(r"[^A-Z0-9]+", "_", normalized.upper()).strip("_") or "PII"


def validate_tag_structure(text: str) -> None:
    """Reject nested, unbalanced, or incomplete PII tags."""
    open_tag: re.Match[str] | None = None
    for token in TAG_TOKEN_PATTERN.finditer(text):
        is_closing = token.group(0).lower().startswith("</")
        if is_closing:
            if open_tag is None:
                raise AnonymizationError("Found a closing PII tag without an opener.")
            open_tag = None
        elif open_tag is not None:
            raise AnonymizationError("Nested PII tags are not allowed.")
        else:
            open_tag = token
    if open_tag is not None:
        raise AnonymizationError("Found an opening PII tag without a closing tag.")


def anonymize_tagged_text(text: str) -> tuple[str, int]:
    """Replace PII tags while keeping type/reference assignments consistent."""
    validate_tag_structure(text)
    marker_by_key: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}

    def replace_tag(match: re.Match[str]) -> str:
        attributes = {
            item.group("name").lower(): item.group("value")
            for item in ATTRIBUTE_PATTERN.finditer(match.group("attrs"))
        }
        raw_type = attributes.get("tipo")
        reference = attributes.get("ref")
        if not raw_type or not reference:
            raise AnonymizationError(
                "Every PII tag requires quoted tipo and ref attributes."
            )

        canonical_type = normalize_type(raw_type)
        key = (canonical_type, reference.strip())
        if key not in marker_by_key:
            counters[canonical_type] = counters.get(canonical_type, 0) + 1
            marker_by_key[key] = f"_{canonical_type}_{counters[canonical_type]}_"
        return marker_by_key[key]

    anonymized, count = PII_PATTERN.subn(replace_tag, text)
    if TAG_TOKEN_PATTERN.search(anonymized):
        raise AnonymizationError("At least one malformed PII tag was not replaced.")
    return anonymized, count


def default_output_path(input_path: Path) -> Path:
    """Build a non-destructive .anon.md sibling path."""
    name = input_path.name
    if name.endswith(".tagged.md"):
        return input_path.with_name(f"{name.removesuffix('.tagged.md')}.anon.md")
    if name.endswith(".md"):
        return input_path.with_name(f"{name.removesuffix('.md')}.anon.md")
    return input_path.with_name(f"{name}.anon.md")


def input_files(input_path: Path) -> list[Path]:
    """Resolve one file or all reviewed tagged Markdown files in a directory."""
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(input_path.rglob("*.tagged.md"))
    raise FileNotFoundError(input_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace reviewed PII tags with deterministic markers."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path; valid only when --input is one file.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = input_files(args.input)
    if args.output and len(files) != 1:
        raise AnonymizationError("--output requires a single input file.")
    if not files:
        raise AnonymizationError("No *.tagged.md files found.")

    for input_path in files:
        output_path = args.output or default_output_path(input_path)
        if input_path.resolve() == output_path.resolve():
            raise AnonymizationError("Refusing to overwrite the input file.")
        if output_path.exists() and not args.force:
            raise FileExistsError(f"Output already exists: {output_path}")

        text = input_path.read_text(encoding="utf-8")
        anonymized, substitutions = anonymize_tagged_text(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(anonymized, encoding="utf-8")
        print(f"{input_path} -> {output_path} ({substitutions} substitutions)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AnonymizationError, FileExistsError, FileNotFoundError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
