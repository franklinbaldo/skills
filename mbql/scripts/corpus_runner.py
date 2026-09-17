#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Run a SQL corpus through the DuckDB->MBQL contract and expose drift."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from sqlglot import parse
from sqlglot.errors import ParseError

from conformance import Status, classify
from sql_to_mbql import ConversionError, convert_sql


@dataclass(frozen=True)
class CorpusResult:
    source: str
    index: int
    sql: str
    status: str
    features: tuple[str, ...]
    converted: bool
    error: str | None = None


STATUS_RANK = {
    Status.SUPPORTED: 0,
    Status.AMBIGUOUS: 1,
    Status.UNSUPPORTED: 2,
}


def _effective_status(sql: str) -> tuple[Status, tuple[str, ...]]:
    features = classify(sql)
    if not features:
        return Status.UNSUPPORTED, ("unclassified",)
    status = max((item.status for item in features), key=STATUS_RANK.__getitem__)
    return status, tuple(item.feature for item in features)


def iter_sql_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for candidate in sorted(path.rglob("*.sql")):
        if candidate.is_file():
            yield candidate


def run_file(path: Path, *, database: str, schema: str | None = "main") -> list[CorpusResult]:
    text = path.read_text(encoding="utf-8")
    try:
        expressions = parse(text, read="duckdb")
    except ParseError as exc:
        return [
            CorpusResult(
                source=str(path),
                index=0,
                sql=text,
                status="parse_error",
                features=(),
                converted=False,
                error=str(exc),
            )
        ]

    rows: list[CorpusResult] = []
    for index, expression in enumerate(expressions, start=1):
        sql = expression.sql(dialect="duckdb")
        status, features = _effective_status(sql)
        converted = False
        error: str | None = None
        if status is Status.SUPPORTED:
            try:
                convert_sql(sql, database=database, schema=schema)
                converted = True
            except ConversionError as exc:
                # This is a contract bug, not an ordinary unsupported query: the
                # feature matrix said every feature was supported.
                status_text = "contract_gap"
                error = str(exc)
            else:
                status_text = status.value
        else:
            status_text = status.value
        rows.append(
            CorpusResult(
                source=str(path),
                index=index,
                sql=sql,
                status=status_text,
                features=features,
                converted=converted,
                error=error,
            )
        )
    return rows


def run_corpus(path: Path, *, database: str, schema: str | None = "main") -> dict[str, object]:
    results = [row for file in iter_sql_files(path) for row in run_file(file, database=database, schema=schema)]
    counts: dict[str, int] = {}
    for row in results:
        counts[row.status] = counts.get(row.status, 0) + 1
    return {
        "source": str(path),
        "statements": len(results),
        "counts": counts,
        "contract_gaps": sum(row.status == "contract_gap" for row in results),
        "results": [asdict(row) for row in results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help=".sql file or directory tree")
    parser.add_argument("--database", required=True, help="portable Metabase database name")
    parser.add_argument("--schema", default="main")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)

    payload = run_corpus(args.path, database=args.database, schema=args.schema or None)
    print(json.dumps(payload, ensure_ascii=False, indent=None if args.compact else 2))
    return 1 if payload["contract_gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
