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
    FeatureResult("scalar_functions_common", Status.SUPPORTED, "LOWER/UPPER/COALESCE/ABS map to MBQL expressions"),
    FeatureResult("string_functions_common", Status.SUPPORTED, "CONCAT/SUBSTRING/REPLACE/TRIM/LENGTH map to MBQL expressions"),
    FeatureResult("case_expression", Status.SUPPORTED, "searched/simple CASE map to MBQL case clauses"),
    FeatureResult("if_expression", Status.SUPPORTED, "DuckDB IF maps to a single-branch MBQL case"),
    FeatureResult("dpipe_overloaded", Status.AMBIGUOUS, "DuckDB || can concatenate strings or nested/list values without type metadata"),
    FeatureResult("temporal_extract_basic", Status.SUPPORTED, "YEAR/MONTH/DAY/HOUR/MINUTE/SECOND/QUARTER map to MBQL getters"),
    FeatureResult("temporal_extract_calendar", Status.UNSUPPORTED, "calendar-sensitive EXTRACT units need explicit conventions"),
    FeatureResult("cast_basic", Status.SUPPORTED, "VARCHAR/integer/FLOAT-DOUBLE casts map to MBQL text/integer/float"),
    FeatureResult("cast_unsupported", Status.UNSUPPORTED, "DECIMAL, temporal and TRY_CAST semantics are not approximated"),
    FeatureResult("group_by", Status.SUPPORTED, "breakout in first MBQL stage"),
    FeatureResult("having_simple", Status.SUPPORTED, "second-stage filter over projected aggregate"),
    FeatureResult("having_expression", Status.AMBIGUOUS, "aggregate-expression output naming across stages is unresolved"),
    FeatureResult("order_by", Status.SUPPORTED, "field and aggregation ordering"),
    FeatureResult("limit", Status.SUPPORTED, "direct stage limit"),
    FeatureResult("offset_aligned", Status.SUPPORTED, "LIMIT N OFFSET k*N maps exactly to MBQL page/items"),
    FeatureResult("offset_unaligned", Status.AMBIGUOUS, "arbitrary OFFSET cannot be represented exactly by page/items"),
    FeatureResult("offset_without_limit", Status.UNSUPPORTED, "MBQL page requires a finite items/page size"),
    FeatureResult("select_distinct_simple", Status.SUPPORTED, "single direct column maps to breakout distinct-values semantics"),
    FeatureResult("select_distinct_complex", Status.AMBIGUOUS, "DISTINCT expressions/aliases/composite forms need explicit contracts"),
    FeatureResult("count_distinct", Status.SUPPORTED, "single-field COUNT DISTINCT maps to distinct aggregation"),
    FeatureResult("joins", Status.SUPPORTED, "inner/left/right/full joins with conjunctive comparisons"),
    FeatureResult("join_unqualified_column", Status.AMBIGUOUS, "without schema metadata, unqualified columns in joins cannot be attributed safely"),
    FeatureResult("subquery_linear", Status.SUPPORTED, "single derived SELECT source maps to the preceding MBQL stage"),
    FeatureResult("subquery_complex", Status.UNSUPPORTED, "aggregate/outer-join derived sources need stronger cross-stage contracts"),
    FeatureResult("cte_linear", Status.SUPPORTED, "single non-recursive CTE used as the only source maps to linear stages"),
    FeatureResult("cte_complex", Status.UNSUPPORTED, "multiple/recursive/non-linear CTEs are outside the current stage contract"),
    FeatureResult("window", Status.AMBIGUOUS, "requires explicit cross-stage/window semantics"),
    FeatureResult("qualify", Status.UNSUPPORTED, "depends on window output semantics"),
    FeatureResult("set_operations", Status.UNSUPPORTED, "UNION/INTERSECT/EXCEPT are outside current MBQL stage contract"),
    FeatureResult("unnest", Status.UNSUPPORTED, "DuckDB nested expansion has no converter contract"),
    FeatureResult("pivot", Status.UNSUPPORTED, "DuckDB PIVOT has no converter contract"),
    FeatureResult("asof_join", Status.UNSUPPORTED, "ASOF join has no MBQL mapping"),
)


def _literal_int(node: exp.Expression | None) -> int | None:
    if not isinstance(node, exp.Literal) or node.is_string:
        return None
    try:
        return int(node.this)
    except (TypeError, ValueError):
        return None



def _inner_cross_stage_safe(select: exp.Select) -> bool:
    grouped = select.args.get("group") is not None
    for projection in select.expressions:
        expression = projection.this if isinstance(projection, exp.Alias) else projection
        alias = projection.alias if isinstance(projection, exp.Alias) else None
        if isinstance(expression, exp.AggFunc):
            if not alias:
                return False
            continue
        if grouped and not isinstance(expression, exp.Column):
            return False
        if grouped and alias and isinstance(expression, exp.Column) and alias.lower() != expression.name.lower():
            return False
    return True


def _linear_subquery_source(node: exp.Select) -> bool:
    from_ = node.args.get("from_")
    if from_ is None or not isinstance(from_.this, exp.Subquery) or not isinstance(from_.this.this, exp.Select):
        return False
    return not node.args.get("joins") and _inner_cross_stage_safe(from_.this.this)


def _linear_cte_source(node: exp.Select) -> bool:
    with_ = node.args.get("with_")
    if with_ is None or bool(with_.args.get("recursive")) or len(with_.expressions) != 1:
        return False
    cte = with_.expressions[0]
    if not isinstance(cte, exp.CTE) or not isinstance(cte.this, exp.Select) or not _inner_cross_stage_safe(cte.this):
        return False
    from_ = node.args.get("from_")
    return (
        from_ is not None
        and isinstance(from_.this, exp.Table)
        and from_.this.name.lower() == cte.alias_or_name.lower()
        and not node.args.get("joins")
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
            add("cte_linear" if _linear_cte_source(node) else "cte_complex")
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

        limit = node.args.get("limit")
        offset = node.args.get("offset")
        if limit:
            add("limit")
        if offset:
            if not limit:
                add("offset_without_limit")
            else:
                items = _literal_int(limit.expression)
                offset_value = _literal_int(offset.expression)
                if items and offset_value is not None and offset_value % items == 0:
                    add("offset_aligned")
                else:
                    add("offset_unaligned")

        if node.args.get("distinct"):
            simple = (
                len(node.expressions) == 1
                and isinstance(node.expressions[0], exp.Column)
                and not node.args.get("group")
                and not node.args.get("having")
            )
            add("select_distinct_simple" if simple else "select_distinct_complex")
        if node.args.get("joins"):
            add("joins")
            scoped_nodes = [*node.expressions]
            if node.args.get("where"):
                scoped_nodes.append(node.args["where"].this)
            if node.args.get("group"):
                scoped_nodes.extend(node.args["group"].expressions)
            if any(
                isinstance(column, exp.Column) and not column.table
                for scoped in scoped_nodes
                for column in scoped.find_all(exp.Column)
            ):
                add("join_unqualified_column")
        if node.args.get("qualify"):
            add("qualify")

    if any(isinstance(item, (exp.Lower, exp.Upper, exp.Coalesce, exp.Abs)) for item in node.walk()):
        add("scalar_functions_common")
    if any(isinstance(item, (exp.Concat, exp.Substring, exp.Replace, exp.Trim, exp.Length)) for item in node.walk()):
        add("string_functions_common")
    if any(isinstance(item, exp.Case) for item in node.walk()):
        add("case_expression")
    if any(isinstance(item, exp.If) for item in node.walk()):
        add("if_expression")
    if any(isinstance(item, exp.DPipe) for item in node.walk()):
        add("dpipe_overloaded")
    for item in node.find_all(exp.Extract):
        unit = item.this.sql(dialect="duckdb").strip("'\"").lower()
        if unit in {"year", "month", "day", "hour", "minute", "second", "quarter"}:
            add("temporal_extract_basic")
        else:
            add("temporal_extract_calendar")
    safe_cast_targets = {"VARCHAR", "TEXT", "TINYINT", "SMALLINT", "INTEGER", "INT", "BIGINT", "HUGEINT", "REAL", "FLOAT", "DOUBLE"}
    for item in node.walk():
        if isinstance(item, exp.TryCast):
            add("cast_unsupported")
        elif isinstance(item, exp.Cast):
            target = item.to.sql(dialect="duckdb").upper()
            add("cast_basic" if target in safe_cast_targets else "cast_unsupported")
    if any(node.find_all(exp.Window)):
        add("window")
    if any(node.find_all(exp.Subquery)):
        add("subquery_linear" if _linear_subquery_source(node) else "subquery_complex")
    if any(isinstance(x, exp.Count) and isinstance(x.this, exp.Distinct) for x in node.walk()):
        add("count_distinct")
    if isinstance(node, (exp.Union, exp.Intersect, exp.Except)):
        add("set_operations")

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
