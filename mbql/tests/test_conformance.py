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
        }:
            assert len(clause) >= 2
            assert isinstance(clause[1], dict), clause


@st.composite
def supported_queries(draw) -> str:
    """Generate a finite-grammar family known to have a defined v2 contract."""
    grouped = draw(st.booleans())
    where = draw(st.booleans())
    ordered = draw(st.booleans())
    limited = draw(st.booleans())

    parts: list[str] = []
    if grouped:
        agg = draw(st.sampled_from(AGGREGATES))
        parts.append(f"SELECT status, {agg} AS metric FROM orders")
    else:
        cols = draw(st.lists(st.sampled_from(COLUMNS), min_size=1, max_size=3, unique=True))
        parts.append("SELECT " + ", ".join(cols) + " FROM orders")

    if where:
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
@settings(max_examples=300, deadline=None)
def test_generated_supported_queries_never_produce_malformed_mbql(sql: str) -> None:
    query = convert_sql(sql, database="Analytics")
    assert_mbql_shape(query)


@given(supported_queries())
@settings(max_examples=200, deadline=None)
def test_formatting_is_metamorphic(sql: str) -> None:
    """Whitespace/terminator changes must not alter the generated MBQL."""
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
        ("SELECT DISTINCT status FROM orders", "select_distinct", Status.AMBIGUOUS),
        ("SELECT id FROM orders LIMIT 10 OFFSET 5", "offset", Status.AMBIGUOUS),
        ("WITH x AS (SELECT id FROM orders) SELECT * FROM x", "cte", Status.UNSUPPORTED),
        ("SELECT row_number() OVER (ORDER BY id) FROM orders", "window", Status.AMBIGUOUS),
        ("SELECT * FROM orders UNION SELECT * FROM customers", "set_operations", Status.UNSUPPORTED),
    ],
)
def test_classifier_exposes_contract(sql: str, feature: str, status: Status) -> None:
    rows = classify(sql)
    assert any(row.feature == feature and row.status == status for row in rows)


@pytest.mark.xfail(strict=True, reason="row-level DISTINCT needs an explicit portable MBQL semantic contract")
def test_ambiguous_select_distinct_stays_executable() -> None:
    convert_sql("SELECT DISTINCT status FROM orders", database="Analytics")


@pytest.mark.xfail(strict=True, reason="OFFSET needs a decided OFFSET/LIMIT -> MBQL page/items mapping")
def test_ambiguous_offset_stays_executable() -> None:
    convert_sql("SELECT id FROM orders LIMIT 10 OFFSET 5", database="Analytics")


@pytest.mark.xfail(strict=True, reason="window semantics need an explicit multi-stage contract")
def test_ambiguous_window_stays_executable() -> None:
    convert_sql("SELECT id, row_number() OVER (ORDER BY id) AS n FROM orders", database="Analytics")


@pytest.mark.xfail(strict=True, reason="semantic differential needs a live Metabase MBQL execution oracle")
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


def test_unsupported_cte_must_fail_loudly() -> None:
    with pytest.raises(ConversionError, match="CTE"):
        convert_sql("WITH x AS (SELECT id FROM orders) SELECT * FROM x", database="Analytics")


def test_counterexample_is_serializable_for_replay() -> None:
    sql = "SELECT status, SUM(total) AS metric FROM orders GROUP BY status HAVING metric > 3"
    payload = {"sql": sql, "mbql": convert_sql(sql, database="Analytics")}
    assert json.loads(json.dumps(payload)) == payload


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
