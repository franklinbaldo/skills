#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.28",
#   "sqlglot>=27,<29",
# ]
# ///
"""Validate and differentially execute DuckDB SQL as portable MBQL on Metabase."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from sqlglot import parse_one

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
    with httpx.Client(base_url=url.rstrip("/"), headers=_headers(api_key), timeout=60.0) as client:
        opaque = construct(client, mbql)
        result: dict[str, Any] = {"sql": sql, "mbql": mbql, "construct": "ok"}
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql", nargs="?", help="DuckDB SQL SELECT")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--url", default=os.environ.get("METABASE_URL"), help="Metabase base URL or METABASE_URL")
    parser.add_argument("--api-key", default=os.environ.get("METABASE_API_KEY"), help="API key or METABASE_API_KEY")
    parser.add_argument("--database", required=True, help="exact Metabase database name used in portable FKs")
    parser.add_argument("--database-id", type=int, help="numeric database id for --compare-native")
    parser.add_argument("--schema", default="main")
    parser.add_argument("--execute", action="store_true", help="execute resolved MBQL after validation")
    parser.add_argument("--compare-native", action="store_true", help="execute SQL and MBQL and require equivalent rows")
    args = parser.parse_args(argv)

    try:
        if not args.url or not args.api_key:
            raise LiveConformanceError("Defina --url/METABASE_URL e --api-key/METABASE_API_KEY.")
        sql = _read_sql(args.sql, args.file)
        payload = run_live(
            sql,
            url=args.url,
            api_key=args.api_key,
            database=args.database,
            database_id=args.database_id,
            schema=args.schema or None,
            execute=args.execute,
            compare_native=args.compare_native,
        )
    except (ConversionError, LiveConformanceError, OSError, httpx.HTTPError) as exc:
        parser.error(str(exc))

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
