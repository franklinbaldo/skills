#!/usr/bin/env python3
"""Materialize canonical audit views in an okf-parser DuckDB artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

VIEW_NAMES = (
    "eval_coverage",
    "skill_relations",
    "mentions_without_edge",
    "isolated_skills",
    "resource_surface",
    "routing_observations",
    "routing_observation_mismatches",
    "routing_runs",
    "routing_run_coverage",
    "routing_case_results",
    "routing_skill_results",
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "queries" / "typed-audit.sql",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run(args.database, args.queries)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
