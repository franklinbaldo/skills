#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "cyclopts>=3.0",
#   "httpx>=0.28",
#   "sqlglot>=27,<29",
# ]
# ///
"""Validate and differentially execute DuckDB SQL as portable MBQL on Metabase."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import cyclopts
import httpx
from sqlglot import parse_one

from conformance import required_driver_features
from sql_to_mbql import ConversionError, convert_sql


class LiveConformanceError(RuntimeError):
    """Raised when the live Metabase oracle rejects or disagrees with a query."""


def _read_sql(value: str | None, file: Path | None) -> str:
    if value and file:
        raise LiveConformanceError("Use SQL posicional ou --file, não os dois.")
    if file:
        return file.read_text(encoding="utf-8")
    if value:
        return value
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise LiveConformanceError("Informe SQL como argumento, --file, ou stdin.")


def _headers(api_key: str) -> dict[str, str]:
    return {"Content-Type": "application/json", "X-API-Key": api_key}


def _post(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    try:
        body = response.json()
    except ValueError as exc:
        raise LiveConformanceError(f"Metabase devolveu resposta não JSON em {path}: HTTP {response.status_code}") from exc
    if response.status_code >= 400:
        raise LiveConformanceError(f"Metabase rejeitou {path}: HTTP {response.status_code}: {body}")
    if isinstance(body, dict) and body.get("status") == "failed":
        raise LiveConformanceError(f"Metabase falhou em {path}: {body.get('error', body)}")
    if not isinstance(body, dict):
        raise LiveConformanceError(f"Resposta inesperada de {path}: {body!r}")
    return body


def _get(client: httpx.Client, path: str) -> dict[str, Any]:
    response = client.get(path)
    try:
        body = response.json()
    except ValueError as exc:
        raise LiveConformanceError(
            f"Metabase devolveu resposta não JSON em {path}: HTTP {response.status_code}"
        ) from exc
    if response.status_code >= 400:
        raise LiveConformanceError(f"Metabase rejeitou {path}: HTTP {response.status_code}: {body}")
    if not isinstance(body, dict):
        raise LiveConformanceError(f"Resposta inesperada de {path}: {body!r}")
    return body


def fetch_database_features(client: httpx.Client, database_id: int) -> set[str]:
    body = _get(client, f"/api/database/{database_id}")
    features = body.get("features")
    if not isinstance(features, list) or not all(isinstance(item, str) for item in features):
        raise LiveConformanceError(
            f"Database {database_id} não devolveu lista de features utilizável: {body}"
        )
    return set(features)


def ensure_driver_features(required: set[str], available: set[str]) -> None:
    missing = sorted(required - available)
    if missing:
        raise LiveConformanceError(
            "Driver do database não suporta capabilities exigidas pela query: "
            + ", ".join(missing)
        )


def normalize_rows(rows: list[list[Any]] | list[tuple[Any, ...]]) -> list[list[Any]]:
    """Normalize row containers while preserving cell values."""
    return [list(row) for row in rows]


def _row_key(row: list[Any]) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def construct(client: httpx.Client, mbql: dict[str, Any]) -> str:
    body = _post(client, "/api/agent/v2/construct-query", {"query": mbql})
    query = body.get("query")
    if not isinstance(query, str) or not query:
        raise LiveConformanceError(f"construct-query não devolveu query opaca: {body}")
    return query


def execute_mbql(client: httpx.Client, query: str) -> dict[str, Any]:
    return _post(client, "/api/agent/v1/execute", {"query": query})


def execute_sql(client: httpx.Client, *, database_id: int, sql: str) -> dict[str, Any]:
    return _post(client, "/api/agent/v1/execute-sql", {"database_id": database_id, "sql": sql})


def compare_results(native: dict[str, Any], mbql: dict[str, Any], *, ordered: bool) -> None:
    """Compare relational results, respecting that row order is undefined without ORDER BY."""
    native_data = native.get("data") or {}
    mbql_data = mbql.get("data") or {}
    native_rows = normalize_rows(native_data.get("rows") or [])
    mbql_rows = normalize_rows(mbql_data.get("rows") or [])

    if ordered:
        equivalent = native_rows == mbql_rows
    else:
        equivalent = Counter(map(_row_key, native_rows)) == Counter(map(_row_key, mbql_rows))

    if not equivalent:
        raise LiveConformanceError(
            "semantic mismatch DuckDB SQL != MBQL\n"
            + json.dumps(
                {"ordered": ordered, "native_rows": native_rows, "mbql_rows": mbql_rows},
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )


def _sql_has_order_by(sql: str) -> bool:
    node = parse_one(sql, read="duckdb")
    return bool(node.args.get("order"))


def run_live(
    sql: str,
    *,
    url: str,
    api_key: str,
    database: str,
    schema: str | None = "main",
    execute: bool = False,
    compare_native: bool = False,
    database_id: int | None = None,
) -> dict[str, Any]:
    mbql = convert_sql(sql, database=database, schema=schema)
    required_features = required_driver_features(sql)
    with httpx.Client(base_url=url.rstrip("/"), headers=_headers(api_key), timeout=60.0) as client:
        result: dict[str, Any] = {
            "sql": sql,
            "mbql": mbql,
            "required_driver_features": sorted(required_features),
        }
        if database_id is not None:
            available_features = fetch_database_features(client, database_id)
            ensure_driver_features(required_features, available_features)
            result["driver_features_checked"] = True
        opaque = construct(client, mbql)
        result["construct"] = "ok"
        if execute or compare_native:
            mbql_result = execute_mbql(client, opaque)
            result["mbql_execution"] = {
                "status": mbql_result.get("status"),
                "row_count": mbql_result.get("row_count"),
            }
        if compare_native:
            if database_id is None:
                raise LiveConformanceError("--compare-native exige --database-id.")
            native_result = execute_sql(client, database_id=database_id, sql=sql)
            ordered = _sql_has_order_by(sql)
            compare_results(native_result, mbql_result, ordered=ordered)
            result["semantic_equivalence"] = True
            result["order_sensitive"] = ordered
        return result


app = cyclopts.App(name="mbql-live-conformance", help=__doc__)


@app.default
def main(
    sql: str | None = None,
    *,
    database: str,
    file: Path | None = None,
    url: str | None = os.environ.get("METABASE_URL"),
    api_key: str | None = os.environ.get("METABASE_API_KEY"),
    database_id: int | None = None,
    schema: str = "main",
    execute: bool = False,
    compare_native: bool = False,
) -> int:
    """Validate and optionally execute/diff one DuckDB SQL query against Metabase."""
    try:
        if not url or not api_key:
            raise LiveConformanceError("Defina --url/METABASE_URL e --api-key/METABASE_API_KEY.")
        source = _read_sql(sql, file)
        payload = run_live(
            source,
            url=url,
            api_key=api_key,
            database=database,
            database_id=database_id,
            schema=schema or None,
            execute=execute,
            compare_native=compare_native,
        )
    except (ConversionError, LiveConformanceError, OSError, httpx.HTTPError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(app())
