#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb",
#     "cyclopts>=3.0",
# ]
# ///
"""Materialize canonical static audit views in an okf-parser DuckDB artifact."""

from __future__ import annotations

import json
from pathlib import Path

import cyclopts
import duckdb

VIEW_NAMES = (
    "eval_coverage",
    "skill_relations",
    "mentions_without_edge",
    "isolated_skills",
    "resource_surface",
)


def _rows_as_dicts(con: duckdb.DuckDBPyConnection, view: str) -> list[dict[str, object]]:
    cursor = con.execute(f'SELECT * FROM audit."{view}"')
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def run(database: Path, query_file: Path) -> dict[str, list[dict[str, object]]]:
    sql = query_file.read_text(encoding="utf-8")
    con = duckdb.connect(str(database))
    try:
        con.execute(sql)
        return {view: _rows_as_dicts(con, view) for view in VIEW_NAMES}
    finally:
        con.close()


app = cyclopts.App(name="run-typed-audit", help=__doc__)


@app.default
def main(
    database: Path,
    *,
    queries: Path = Path(__file__).resolve().parents[1] / "queries" / "typed-audit.sql",
    output: Path | None = None,
) -> int:
    """Materialize the audit views.

    Parameters
    ----------
    database
        DuckDB artifact produced by okf-parser.
    queries
        SQL file with the canonical audit view definitions.
    output
        Write the JSON report here instead of stdout.
    """
    report = run(database, queries)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(app())
