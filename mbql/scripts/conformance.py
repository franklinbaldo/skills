#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Classify DuckDB SQL features against the MBQL converter contract."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Iterable

from sqlglot import exp, parse_one


class Status(StrEnum):
    SUPPORTED = "supported"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class FeatureResult:
    feature: str
    status: Status
    reason: str


FEATURE_MATRIX: tuple[FeatureResult, ...] = (
    FeatureResult("select", Status.SUPPORTED, "single SELECT over a direct table"),
    FeatureResult("where", Status.SUPPORTED, "boolean filters and common comparisons"),
    FeatureResult("group_by", Status.SUPPORTED, "breakout in first MBQL stage"),
    FeatureResult("having_simple", Status.SUPPORTED, "second-stage filter over projected aggregate"),
    FeatureResult("having_expression", Status.AMBIGUOUS, "aggregate-expression output naming across stages is unresolved"),
    FeatureResult("order_by", Status.SUPPORTED, "field and aggregation ordering"),
    FeatureResult("limit", Status.SUPPORTED, "direct stage limit"),
    FeatureResult("offset", Status.AMBIGUOUS, "portable page/items contract not fixed"),
    FeatureResult("select_distinct", Status.AMBIGUOUS, "row DISTINCT is not always equivalent to breakout"),
    FeatureResult("count_distinct", Status.SUPPORTED, "single-field COUNT DISTINCT maps to distinct aggregation"),
    FeatureResult("joins", Status.SUPPORTED, "inner/left/right/full joins with conjunctive comparisons"),
    FeatureResult("subquery", Status.UNSUPPORTED, "no direct-table source semantics implemented"),
    FeatureResult("cte", Status.UNSUPPORTED, "multi-source staging contract not implemented"),
    FeatureResult("window", Status.AMBIGUOUS, "requires explicit cross-stage/window semantics"),
    FeatureResult("qualify", Status.UNSUPPORTED, "depends on window output semantics"),
    FeatureResult("set_operations", Status.UNSUPPORTED, "UNION/INTERSECT/EXCEPT are outside current MBQL stage contract"),
    FeatureResult("unnest", Status.UNSUPPORTED, "DuckDB nested expansion has no converter contract"),
    FeatureResult("pivot", Status.UNSUPPORTED, "DuckDB PIVOT has no converter contract"),
    FeatureResult("asof_join", Status.UNSUPPORTED, "ASOF join has no MBQL mapping"),
)


def classify(sql: str) -> list[FeatureResult]:
    node = parse_one(sql, read="duckdb")
    found: list[FeatureResult] = []
    by_name = {item.feature: item for item in FEATURE_MATRIX}

    def add(name: str) -> None:
        item = by_name[name]
        if item not in found:
            found.append(item)

    if isinstance(node, exp.Select):
        add("select")
        if node.args.get("with_"):
            add("cte")
        if node.args.get("where"):
            add("where")
        if node.args.get("group"):
            add("group_by")
        if node.args.get("having"):
            having = node.args["having"].this
            aggregate_nodes = tuple(having.find_all(exp.AggFunc))
            has_arithmetic = any(isinstance(x, (exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod)) for x in having.walk())
            add("having_expression" if aggregate_nodes and has_arithmetic else "having_simple")
        if node.args.get("order"):
            add("order_by")
        if node.args.get("limit"):
            add("limit")
        if node.args.get("offset"):
            add("offset")
        if node.args.get("distinct"):
            add("select_distinct")
        if node.args.get("joins"):
            add("joins")
        if node.args.get("qualify"):
            add("qualify")

    if any(node.find_all(exp.Window)):
        add("window")
    if any(node.find_all(exp.Subquery)):
        add("subquery")
    if any(isinstance(x, exp.Count) and isinstance(x.this, exp.Distinct) for x in node.walk()):
        add("count_distinct")
    if isinstance(node, (exp.Union, exp.Intersect, exp.Except)):
        add("set_operations")

    # sqlglot class names vary for some DuckDB-specific constructs; keep those
    # detectable by normalized SQL text rather than guessing AST internals.
    normalized = node.sql(dialect="duckdb").upper()
    if "UNNEST(" in normalized:
        add("unnest")
    if "PIVOT" in normalized:
        add("pivot")
    if "ASOF JOIN" in normalized:
        add("asof_join")

    return found


def report(rows: Iterable[FeatureResult] = FEATURE_MATRIX) -> dict[str, object]:
    rows = tuple(rows)
    counts = {status.value: sum(row.status == status for row in rows) for status in Status}
    return {
        "features": [asdict(row) for row in rows],
        "counts": counts,
        "semantic_mismatch_allowed": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql", nargs="?", help="optional DuckDB SQL to classify")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    payload: object = report() if not args.sql else [asdict(row) for row in classify(args.sql)]
    print(json.dumps(payload, ensure_ascii=False, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
