#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb>=1.4",
#   "hypothesis>=6.140",
#   "pytest>=8.4",
#   "sqlglot>=27,<29",
# ]
# ///
"""Bounded-exhaustive and property tests for DuckDB SQL -> MBQL."""
# ruff: noqa: E402, I001

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import duckdb
import pytest
from hypothesis import given, settings, strategies as st

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from conformance import Status, classify, report
from sql_to_mbql import ConversionError, convert_sql

COLUMNS = ("id", "total", "quantity", "status")
NUMERIC = ("id", "total", "quantity")
COMPARISONS = (">", ">=", "<", "<=", "=", "!=")
AGGREGATES = ("COUNT(*)", "SUM(total)", "AVG(total)", "MIN(total)", "MAX(total)")
SCALAR_PROJECTIONS = (
    "lower(status) AS lower_status",
    "upper(status) AS upper_status",
    "coalesce(status, 'unknown') AS safe_status",
    "abs(total) AS absolute_total",
    "cast(status AS VARCHAR) AS text_status",
    "cast(total AS INTEGER) AS int_total",
    "cast(total AS DOUBLE) AS float_total",
    "concat(status, '-', id) AS joined_status",
    "substring(status, 2, 3) AS status_piece",
    "replace(status, 'a', 'b') AS replaced_status",
    "trim(status) AS trimmed_status",
    "length(status) AS status_length",
    "CASE WHEN total > 100 THEN 'high' ELSE 'low' END AS bucket",
    "CASE status WHEN 'paid' THEN 1 ELSE 0 END AS paid_code",
    "if(total > 100, 'high', 'low') AS if_bucket",
    "extract(year FROM created_at) AS created_year",
    "extract(month FROM created_at) AS created_month",
)


def _walk_clauses(value: Any):
    if isinstance(value, list):
        if value and isinstance(value[0], str):
            yield value
        for item in value:
            yield from _walk_clauses(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_clauses(item)


def assert_mbql_shape(query: dict[str, Any]) -> None:
    assert query["lib/type"] == "mbql/query"
    assert query["stages"]
    for stage in query["stages"]:
        assert stage["lib/type"] == "mbql.stage/mbql"
    for clause in _walk_clauses(query):
        if clause[0] in {"Analytics", "main", "orders", "customers"}:
            continue
        if clause[0] in {
            "field", "expression", "aggregation", "count", "distinct", "sum", "avg", "min", "max", "median",
            "and", "or", "not", "=", "!=", ">", ">=", "<", "<=", "+", "-", "*", "/", "mod",
            "between", "in", "is-null", "not-null", "contains", "starts-with", "ends-with", "asc", "desc",
            "lower", "upper", "coalesce", "abs", "text", "integer", "float",
            "concat", "substring", "replace", "trim", "length", "case",
            "get-year", "get-month", "get-day", "get-hour", "get-minute", "get-second", "get-quarter",
        }:
            assert len(clause) >= 2
            assert isinstance(clause[1], dict), clause


@st.composite
def supported_queries(draw) -> str:
    """Generate a finite-grammar family known to have a defined contract."""
    grouped = draw(st.booleans())
    where = draw(st.booleans())
    ordered = draw(st.booleans())
    limited = draw(st.booleans())

    parts: list[str] = []
    if grouped:
        agg = draw(st.sampled_from(AGGREGATES))
        parts.append(f"SELECT status, {agg} AS metric FROM orders")
    elif draw(st.booleans()):
        projection = draw(st.sampled_from(SCALAR_PROJECTIONS))
        parts.append(f"SELECT id, {projection} FROM orders")
    else:
        cols = draw(st.lists(st.sampled_from(COLUMNS), min_size=1, max_size=3, unique=True))
        parts.append("SELECT " + ", ".join(cols) + " FROM orders")

    if where:
        if not grouped and draw(st.booleans()):
            text_op = draw(st.sampled_from(("lower", "upper")))
            parts.append(f"WHERE {text_op}(status) = 'paid'")
        else:
            col = draw(st.sampled_from(NUMERIC))
            op = draw(st.sampled_from(COMPARISONS))
            value = draw(st.integers(min_value=-5, max_value=500))
            parts.append(f"WHERE {col} {op} {value}")

    if grouped:
        parts.append("GROUP BY status")
        if draw(st.booleans()):
            threshold = draw(st.integers(min_value=0, max_value=20))
            parts.append(f"HAVING metric > {threshold}")

    if ordered:
        parts.append("ORDER BY " + ("metric DESC" if grouped else "id ASC"))
    if limited:
        parts.append(f"LIMIT {draw(st.integers(min_value=1, max_value=100))}")
    return " ".join(parts)


@given(supported_queries())
@settings(max_examples=400, deadline=None)
def test_generated_supported_queries_never_produce_malformed_mbql(sql: str) -> None:
    query = convert_sql(sql, database="Analytics")
    assert_mbql_shape(query)


@given(supported_queries())
@settings(max_examples=250, deadline=None)
def test_formatting_is_metamorphic(sql: str) -> None:
    compact = " ".join(sql.split())
    noisy = "\n  " + compact.replace(" FROM ", "\nFROM\n").replace(" WHERE ", "\nWHERE\n") + ";\n"
    assert convert_sql(compact, database="Analytics") == convert_sql(noisy, database="Analytics")


def test_adversarial_duckdb_fixture_is_executable() -> None:
    fixture = (HERE / "fixtures" / "adversarial.sql").read_text(encoding="utf-8")
    con = duckdb.connect(":memory:")
    try:
        con.execute(fixture)
        assert con.execute("SELECT count(*) FROM orders").fetchone() == (7,)
        assert con.execute("SELECT count(*) FROM customers").fetchone() == (4,)
        assert con.execute("SELECT count(*) FROM orders WHERE total IS NULL").fetchone() == (1,)
        assert con.execute("SELECT count(*) FROM orders o LEFT JOIN customers c ON o.customer_id = c.id WHERE c.id IS NULL").fetchone() == (2,)
    finally:
        con.close()


def test_feature_report_has_three_explicit_outcomes_and_zero_silent_mismatch_budget() -> None:
    payload = report()
    assert set(payload["counts"]) == {status.value for status in Status}
    assert payload["semantic_mismatch_allowed"] == 0
    assert sum(payload["counts"].values()) == len(payload["features"])


@pytest.mark.parametrize(
    ("sql", "feature", "status"),
    [
        ("SELECT id FROM orders WHERE total > 10", "where", Status.SUPPORTED),
        ("SELECT median(total) FROM orders", "median", Status.SUPPORTED),
        ("SELECT stddev(total) FROM orders", "stddev_sample", Status.SUPPORTED),
        ("SELECT stddev_samp(total) FROM orders", "stddev_sample", Status.SUPPORTED),
        ("SELECT stddev_pop(total) FROM orders", "stddev_population", Status.UNSUPPORTED),
        ("SELECT corr(total, quantity) FROM orders", "aggregation_unsupported", Status.UNSUPPORTED),
        ("SELECT lower(status) AS s FROM orders", "scalar_functions_common", Status.SUPPORTED),
        ("SELECT cast(total AS INTEGER) AS n FROM orders", "cast_basic", Status.SUPPORTED),
        ("SELECT substring(status, 2, 3) AS s FROM orders", "string_functions_common", Status.SUPPORTED),
        ("SELECT CASE WHEN total > 0 THEN 1 ELSE 0 END AS positive FROM orders", "case_expression", Status.SUPPORTED),
        ("SELECT if(total > 0, 1, 0) AS positive FROM orders", "if_expression", Status.SUPPORTED),
        ("SELECT status || id FROM orders", "dpipe_overloaded", Status.AMBIGUOUS),
        ("SELECT extract(year FROM created_at) AS y FROM orders", "temporal_extract_basic", Status.SUPPORTED),
        ("SELECT extract(week FROM created_at) AS w FROM orders", "temporal_extract_calendar", Status.UNSUPPORTED),
        ("SELECT cast(total AS DECIMAL(18,2)) AS n FROM orders", "cast_unsupported", Status.UNSUPPORTED),
        ("SELECT name FROM orders o JOIN customers c ON o.customer_id = c.id", "join_unqualified_column", Status.AMBIGUOUS),
        ("SELECT o.id, q.revenue FROM orders o LEFT JOIN (SELECT customer_id, sum(total) AS revenue FROM invoices GROUP BY customer_id) q ON o.customer_id = q.customer_id", "join_subquery_linear", Status.SUPPORTED),
        ("SELECT o.id, q.s FROM orders o LEFT JOIN (SELECT lower(status) AS s, sum(total) AS revenue FROM invoices GROUP BY lower(status)) q ON lower(o.status) = q.s", "join_subquery_complex", Status.UNSUPPORTED),
        ("SELECT DISTINCT status FROM orders", "select_distinct_simple", Status.SUPPORTED),
        ("SELECT DISTINCT status, customer_id FROM orders", "select_distinct_simple", Status.SUPPORTED),
        ("SELECT DISTINCT lower(status) FROM orders", "select_distinct_complex", Status.AMBIGUOUS),
        ("SELECT id FROM orders LIMIT 10 OFFSET 20", "offset_aligned", Status.SUPPORTED),
        ("SELECT id FROM orders LIMIT 10 OFFSET 5", "offset_unaligned", Status.AMBIGUOUS),
        ("SELECT id FROM orders OFFSET 5", "offset_without_limit", Status.UNSUPPORTED),
        ("WITH x AS (SELECT id FROM orders) SELECT * FROM x", "cte_linear", Status.SUPPORTED),
        ("WITH x AS (SELECT id, total FROM orders), y AS (SELECT id, total FROM x WHERE total > 10) SELECT id FROM y", "cte_linear", Status.SUPPORTED),
        ("WITH x AS (SELECT id FROM orders), y AS (SELECT id FROM orders) SELECT * FROM x", "cte_complex", Status.UNSUPPORTED),
        ("SELECT id FROM (SELECT id, total FROM orders) q", "subquery_linear", Status.SUPPORTED),
        ("SELECT revenue FROM (SELECT sum(total) AS revenue FROM orders) q", "subquery_linear", Status.SUPPORTED),
        ("SELECT s FROM (SELECT lower(status) AS s, sum(total) AS revenue FROM orders GROUP BY lower(status)) q", "subquery_complex", Status.UNSUPPORTED),
        ("SELECT row_number() OVER (ORDER BY id) FROM orders", "window", Status.AMBIGUOUS),
        ("SELECT * FROM orders UNION SELECT * FROM customers", "set_operations", Status.UNSUPPORTED),
    ],
)
def test_classifier_exposes_contract(sql: str, feature: str, status: Status) -> None:
    rows = classify(sql)
    assert any(row.feature == feature and row.status == status for row in rows)


def test_simple_select_distinct_is_supported() -> None:
    query = convert_sql("SELECT DISTINCT status FROM orders", database="Analytics")
    assert query["stages"][0]["breakout"] == [
        ["field", {}, ["Analytics", "main", "orders", "status"]]
    ]


@pytest.mark.xfail(strict=True, reason="DISTINCT over expressions needs an explicit portable MBQL semantic contract")
def test_ambiguous_select_distinct_expression_stays_executable() -> None:
    convert_sql("SELECT DISTINCT lower(status) FROM orders", database="Analytics")


@pytest.mark.xfail(strict=True, reason="unaligned OFFSET cannot be represented exactly by MBQL page/items")
def test_ambiguous_offset_stays_executable() -> None:
    convert_sql("SELECT id FROM orders LIMIT 10 OFFSET 5", database="Analytics")


@pytest.mark.xfail(strict=True, reason="window semantics need an explicit multi-stage contract")
def test_ambiguous_window_stays_executable() -> None:
    convert_sql("SELECT id, row_number() OVER (ORDER BY id) AS n FROM orders", database="Analytics")


@pytest.mark.xfail(strict=True, reason="semantic differential requires a configured live Metabase instance in CI")
def test_duckdb_vs_mbql_differential_oracle_boundary_is_explicit() -> None:
    sql = "SELECT status, COUNT(*) AS n FROM orders GROUP BY status ORDER BY n DESC"
    fixture = (HERE / "fixtures" / "adversarial.sql").read_text(encoding="utf-8")
    con = duckdb.connect(":memory:")
    try:
        con.execute(fixture)
        duckdb_rows = con.execute(sql).fetchall()
    finally:
        con.close()
    mbql = convert_sql(sql, database="Analytics")
    metabase_rows = None
    assert metabase_rows == duckdb_rows, mbql


def test_complex_cte_must_fail_loudly() -> None:
    with pytest.raises(ConversionError, match="CTE"):
        convert_sql(
            "WITH x AS (SELECT id FROM orders), y AS (SELECT id FROM orders) SELECT * FROM x",
            database="Analytics",
        )


def test_counterexample_is_serializable_for_replay() -> None:
    sql = "SELECT status, SUM(total) AS metric FROM orders GROUP BY status HAVING metric > 3"
    payload = {"sql": sql, "mbql": convert_sql(sql, database="Analytics")}
    assert json.loads(json.dumps(payload)) == payload


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
