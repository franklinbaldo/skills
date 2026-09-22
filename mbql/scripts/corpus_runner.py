#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3.0", "sqlglot>=27,<29"]
# ///
"""Run SQL and DuckDB SQLLogicTest corpora through the MBQL contract."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cyclopts
from sqlglot import parse, parse_one
from sqlglot.errors import ParseError

from conformance import Status, classify, required_driver_features
from sql_to_mbql import ConversionError, convert_sql


@dataclass(frozen=True)
class CorpusResult:
    source: str
    index: int
    sql: str
    status: str
    features: tuple[str, ...]
    converted: bool
    driver_features: tuple[str, ...] = ()
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


def iter_corpus_files(path: Path) -> Iterable[Path]:
    """Yield plain SQL plus DuckDB SQLLogicTest files recursively."""
    if path.is_file():
        yield path
        return
    for pattern in ("*.sql", "*.test", "*.test_slow"):
        for candidate in sorted(path.rglob(pattern)):
            if candidate.is_file():
                yield candidate


def extract_sqllogictest_queries(text: str) -> list[str]:
    """Extract successful `query ...` SQL bodies from a SQLLogicTest file.

    DuckDB's `.test` files mix setup `statement` blocks, query SQL, and expected
    result rows. Only query bodies are relevant to a SELECT/relational converter;
    setup statements are deliberately ignored.
    """
    lines = text.splitlines()
    queries: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("query "):
            i += 1
            continue

        i += 1
        sql_lines: list[str] = []
        while i < len(lines):
            current = lines[i]
            stripped = current.strip()
            if stripped == "----":
                break
            if stripped.startswith("query ") or stripped.startswith("statement "):
                # Defensive handling for a malformed/no-result-separator block.
                break
            sql_lines.append(current)
            i += 1

        sql = "\n".join(sql_lines).strip()
        if sql:
            queries.append(sql)

        # Skip expected output until the blank line before the next directive.
        if i < len(lines) and lines[i].strip() == "----":
            i += 1
            while i < len(lines):
                if not lines[i].strip():
                    i += 1
                    break
                i += 1

    return queries


def _expressions_from_file(path: Path) -> tuple[list[str], str | None]:
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".test", ".test_slow"} or path.name.endswith(".test_slow"):
        statements = extract_sqllogictest_queries(text)
        normalized: list[str] = []
        for sql in statements:
            try:
                normalized.append(parse_one(sql, read="duckdb").sql(dialect="duckdb"))
            except Exception:
                # Corpus fuzzing must preserve parser-internal failures as
                # parse_error rows rather than aborting the whole audit.
                normalized.append(sql)
        return normalized, None

    try:
        expressions = parse(text, read="duckdb")
    except ParseError as exc:
        return [], str(exc)
    return [expression.sql(dialect="duckdb") for expression in expressions], None


def _run_sql(sql: str, *, source: str, index: int, database: str, schema: str | None) -> CorpusResult:
    try:
        # Parse once here so SQLLogicTest extraction failures are visible rather
        # than becoming misleading `unclassified` results.
        parse_one(sql, read="duckdb")
    except Exception as exc:
        return CorpusResult(
            source=source,
            index=index,
            sql=sql,
            status="parse_error",
            features=(),
            converted=False,
            error=str(exc),
        )

    status, features = _effective_status(sql)
    driver_features = tuple(sorted(required_driver_features(sql)))
    converted = False
    error: str | None = None
    try:
        convert_sql(sql, database=database, schema=schema)
        converted = True
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    if status is Status.SUPPORTED:
        status_text = status.value if converted else "contract_gap"
    elif converted:
        # The implementation has outrun the feature matrix. This is useful
        # progress, but leaving the classifier stale would make coverage lie.
        status_text = "classification_gap"
        error = None
    else:
        status_text = status.value

    return CorpusResult(
        source=source,
        index=index,
        sql=sql,
        status=status_text,
        features=features,
        converted=converted,
        driver_features=driver_features,
        error=error,
    )


def run_file(path: Path, *, database: str, schema: str | None = "main") -> list[CorpusResult]:
    statements, file_error = _expressions_from_file(path)
    if file_error is not None:
        return [
            CorpusResult(
                source=str(path),
                index=0,
                sql=path.read_text(encoding="utf-8"),
                status="parse_error",
                features=(),
                converted=False,
                error=file_error,
            )
        ]

    return [
        _run_sql(sql, source=str(path), index=index, database=database, schema=schema)
        for index, sql in enumerate(statements, start=1)
    ]


def run_corpus(path: Path, *, database: str, schema: str | None = "main") -> dict[str, object]:
    results = [row for file in iter_corpus_files(path) for row in run_file(file, database=database, schema=schema)]
    counts: dict[str, int] = {}
    feature_counts: dict[str, int] = {}
    driver_feature_counts: dict[str, int] = {}
    for row in results:
        counts[row.status] = counts.get(row.status, 0) + 1
        for feature in row.features:
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
        for feature in row.driver_features:
            driver_feature_counts[feature] = driver_feature_counts.get(feature, 0) + 1
    return {
        "source": str(path),
        "statements": len(results),
        "counts": counts,
        "feature_counts": dict(sorted(feature_counts.items())),
        "driver_feature_counts": dict(sorted(driver_feature_counts.items())),
        "contract_gaps": sum(row.status == "contract_gap" for row in results),
        "classification_gaps": sum(row.status == "classification_gap" for row in results),
        "parse_errors": sum(row.status == "parse_error" for row in results),
        "results": [asdict(row) for row in results],
    }


app = cyclopts.App(name="mbql-corpus", help=__doc__)


@app.default
def main(
    path: Path,
    *,
    database: str,
    schema: str = "main",
    compact: bool = False,
) -> int:
    """Classify a .sql/.test file or directory tree."""
    payload = run_corpus(path, database=database, schema=schema or None)
    print(json.dumps(payload, ensure_ascii=False, indent=None if compact else 2))
    return 1 if payload["contract_gaps"] or payload["classification_gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(app())
