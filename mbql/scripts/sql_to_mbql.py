#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3.0", "sqlglot>=27,<29"]
# ///
"""Convert a practical subset of DuckDB SQL to portable Metabase MBQL 5.

The converter lives in `mbql_core`; this script is its command line and keeps
the historical import surface (`convert_sql`, `ConversionError`, `Converter`).
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import cyclopts

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mbql_core import (  # noqa: E402
    CaseSensitiveEquality,
    ConversionError,
    Converter,
    TableRef,
    UniqueRowPerGroup,
    convert_sql,
)
from mbql_core.metabase_ids import catalogo_de_metadados, resolver_ids  # noqa: E402 - sem dependência extra

__all__ = [
    "CaseSensitiveEquality",
    "ConversionError",
    "Converter",
    "TableRef",
    "UniqueRowPerGroup",
    "convert_sql",
]


def _read_sql(value: str | None, file: Path | None) -> str:
    if value and file:
        raise ConversionError("Use SQL posicional ou --file, não os dois.")
    if file:
        return file.read_text(encoding="utf-8")
    if value:
        return value
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ConversionError("Informe o SQL como argumento, --file, ou stdin.")


def _precondicao(guard: CaseSensitiveEquality | UniqueRowPerGroup) -> dict[str, Any]:
    return {"kind": type(guard).__name__, **asdict(guard)}


app = cyclopts.App(name="sql-to-mbql", help=__doc__)


@app.default
def main(
    sql: str | None = None,
    *,
    database: str,
    file: Path | None = None,
    schema: str = "main",
    source_dialect: str = "duckdb",
    metadata: Path | None = None,
    ids: bool = False,
    database_id: int | None = None,
    preconditions: bool = False,
    compact: bool = False,
) -> int:
    """Convert one SELECT to MBQL 5.

    Parameters
    ----------
    metadata
        JSON of `/api/database/<id>/metadata?include_hidden=true`. Enables the
        schema-aware rewrites (CTE inlining, IN as join, subquery merging).
    ids
        Emit id-based MBQL 5 for `/api/dataset` instead of portable MBQL; needs
        `--metadata` and `--database-id`.
    preconditions
        Also apply the rewrites that hold only under a condition on the data
        (BINARY equality, latest row per group) and print each condition, which
        the caller must check before running the query.
    """
    try:
        source = _read_sql(sql, file)
        catalogo = None
        if metadata is not None:
            catalogo = catalogo_de_metadados(json.loads(metadata.read_text(encoding="utf-8")))
        if (ids or preconditions) and catalogo is None:
            raise ConversionError("--ids e --preconditions exigem --metadata.")
        guards: list[CaseSensitiveEquality | UniqueRowPerGroup] | None = [] if preconditions else None
        query = convert_sql(
            source,
            database=database,
            schema=schema or None,
            source_dialect=source_dialect,
            tables=catalogo.esquema() if catalogo else None,
            primary_keys=catalogo.chaves_primarias() if catalogo else None,
            guards=guards,
        )
        if ids:
            if database_id is None:
                raise ConversionError("--ids exige --database-id.")
            query = {**resolver_ids(query, catalogo, database=database), "database": database_id}
    except (ConversionError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    saida: Any = query if guards is None else {"query": query, "preconditions": [_precondicao(g) for g in guards]}
    print(
        json.dumps(saida, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(saida, ensure_ascii=False, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(app())
