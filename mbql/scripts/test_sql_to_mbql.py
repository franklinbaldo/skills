#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3.0", "sqlglot>=27,<29"]
# ///
"""Regression/specification tests for the DuckDB SQL -> portable MBQL converter."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sql_to_mbql import ConversionError, convert_sql


class SqlToMbqlTests(unittest.TestCase):
    def test_mysql_source_dialect_matches_duckdb(self) -> None:
        sql = "SELECT id FROM orders WHERE status = 'SENT' ORDER BY id DESC LIMIT 101"
        self.assertEqual(
            convert_sql(sql, database="Analytics", source_dialect="mysql"),
            convert_sql(sql, database="Analytics"),
        )

    def test_invalid_source_dialect_is_diagnostic(self) -> None:
        with self.assertRaises(ConversionError):
            convert_sql("SELECT id FROM orders", database="Analytics", source_dialect="nonexistent")

    def test_plain_projection_where_order_limit(self) -> None:
        query = convert_sql(
            "SELECT id, total FROM orders WHERE total > 100 ORDER BY id DESC LIMIT 5",
            database="Analytics",
        )
        stage = query["stages"][0]

        self.assertEqual(stage["source-table"], ["Analytics", "main", "orders"])
        self.assertEqual(
            stage["fields"],
            [
                ["field", {}, ["Analytics", "main", "orders", "id"]],
                ["field", {}, ["Analytics", "main", "orders", "total"]],
            ],
        )
        self.assertEqual(
            stage["filters"],
            [[">", {}, ["field", {}, ["Analytics", "main", "orders", "total"]], 100]],
        )
        self.assertEqual(stage["limit"], 5)
        self.assertEqual(stage["order-by"][0][0], "desc")

    def test_group_by_and_order_by_ordinals_resolve_select_positions(self) -> None:
        query = convert_sql(
            "SELECT status, COUNT(*) AS n FROM orders GROUP BY 1 ORDER BY 2 DESC",
            database="Analytics",
        )
        stage = query["stages"][0]
        self.assertEqual(
            stage["breakout"],
            [["field", {}, ["Analytics", "main", "orders", "status"]]],
        )
        self.assertEqual(stage["order-by"], [["desc", {}, ["aggregation", {}, 0]]])

    def test_group_by_projection_alias_resolves_underlying_expression(self) -> None:
        query = convert_sql(
            "SELECT lower(status) AS normalized, COUNT(*) AS n FROM orders GROUP BY normalized ORDER BY normalized ASC",
            database="Analytics",
        )
        field = ["field", {}, ["Analytics", "main", "orders", "status"]]
        stage = query["stages"][0]
        self.assertEqual(stage["breakout"], [["lower", {}, field]])
        self.assertEqual(stage["order-by"], [["asc", {}, ["lower", {}, field]]])

    def test_order_by_nonaggregate_projection_alias_uses_expression_ref(self) -> None:
        query = convert_sql(
            "SELECT total * quantity AS gross FROM orders ORDER BY gross DESC",
            database="Analytics",
        )
        self.assertEqual(
            query["stages"][0]["order-by"],
            [["desc", {}, ["expression", {}, "gross"]]],
        )

    def test_grouped_aggregation(self) -> None:
        query = convert_sql(
            "SELECT status, COUNT(*) AS n, SUM(total) AS revenue "
            "FROM sales.orders WHERE paid = true GROUP BY status ORDER BY revenue DESC LIMIT 20",
            database="Warehouse",
        )
        stage = query["stages"][0]

        self.assertEqual(
            stage["breakout"],
            [["field", {}, ["Warehouse", "sales", "orders", "status"]]],
        )
        # O alias SQL da agregação final vira o nome da coluna (opção `name`).
        self.assertEqual(stage["aggregation"][0], ["count", {"name": "n"}])
        self.assertEqual(
            stage["aggregation"][1],
            ["sum", {"name": "revenue"}, ["field", {}, ["Warehouse", "sales", "orders", "total"]]],
        )
        self.assertEqual(stage["order-by"], [["desc", {}, ["aggregation", {}, 1]]])

    def test_alias_expression_becomes_named_mbql_expression(self) -> None:
        query = convert_sql(
            "SELECT price * quantity AS gross FROM line_items",
            database="Analytics",
        )
        stage = query["stages"][0]
        self.assertIn("gross", stage["expressions"])
        self.assertEqual(stage["fields"], [["expression", {}, "gross"]])

    def test_common_scalar_functions_map_to_mbql_expressions(self) -> None:
        query = convert_sql(
            "SELECT lower(status) AS normalized, upper(status) AS loud, "
            "coalesce(status, 'unknown') AS safe, abs(total) AS magnitude FROM orders",
            database="Analytics",
        )
        expressions = query["stages"][0]["expressions"]
        field = ["field", {}, ["Analytics", "main", "orders", "status"]]
        total = ["field", {}, ["Analytics", "main", "orders", "total"]]
        self.assertEqual(expressions["normalized"], ["lower", {}, field])
        self.assertEqual(expressions["loud"], ["upper", {}, field])
        self.assertEqual(expressions["safe"], ["coalesce", {}, field, "unknown"])
        self.assertEqual(expressions["magnitude"], ["abs", {}, total])

    def test_scalar_functions_work_inside_filters(self) -> None:
        query = convert_sql(
            "SELECT id FROM orders WHERE lower(status) = 'paid' AND abs(total) > 10",
            database="Analytics",
        )
        rendered = repr(query["stages"][0]["filters"][0])
        self.assertIn("'lower'", rendered)
        self.assertIn("'abs'", rendered)

    def test_common_string_functions_map_to_mbql(self) -> None:
        query = convert_sql(
            "SELECT concat(status, '-', id) AS joined, substring(status, 2, 3) AS piece, "
            "replace(status, 'a', 'b') AS replaced, trim(status) AS trimmed, length(status) AS size "
            "FROM orders",
            database="Analytics",
        )
        expressions = query["stages"][0]["expressions"]
        status = ["field", {}, ["Analytics", "main", "orders", "status"]]
        ident = ["field", {}, ["Analytics", "main", "orders", "id"]]
        self.assertEqual(expressions["joined"], ["concat", {}, status, "-", ident])
        self.assertEqual(expressions["piece"], ["substring", {}, status, 2, 3])
        self.assertEqual(expressions["replaced"], ["replace", {}, status, "a", "b"])
        self.assertEqual(expressions["trimmed"], ["trim", {}, status])
        self.assertEqual(expressions["size"], ["length", {}, status])

    def test_complex_trim_is_not_approximated(self) -> None:
        with self.assertRaisesRegex(ConversionError, "TRIM|trim"):
            convert_sql("SELECT trim('x' FROM status) AS x FROM orders", database="Analytics")

    def test_searched_case_maps_to_mbql_case(self) -> None:
        query = convert_sql(
            "SELECT CASE WHEN total > 100 THEN 'high' WHEN total > 0 THEN 'positive' ELSE 'other' END AS bucket "
            "FROM orders",
            database="Analytics",
        )
        total = ["field", {}, ["Analytics", "main", "orders", "total"]]
        self.assertEqual(
            query["stages"][0]["expressions"]["bucket"],
            [
                "case",
                {},
                [
                    [[">", {}, total, 100], "high"],
                    [[">", {}, total, 0], "positive"],
                ],
                "other",
            ],
        )

    def test_if_function_maps_to_single_branch_case(self) -> None:
        query = convert_sql(
            "SELECT if(total > 100, 'high', 'low') AS bucket FROM orders",
            database="Analytics",
        )
        total = ["field", {}, ["Analytics", "main", "orders", "total"]]
        self.assertEqual(
            query["stages"][0]["expressions"]["bucket"],
            ["case", {}, [[[">", {}, total, 100], "high"]], "low"],
        )

    def test_temporal_extract_components_map_to_mbql_getters(self) -> None:
        query = convert_sql(
            "SELECT extract(year FROM created_at) AS y, extract(month FROM created_at) AS m, "
            "extract(day FROM created_at) AS d, extract(hour FROM created_at) AS h, "
            "extract(minute FROM created_at) AS mi, extract(second FROM created_at) AS s, "
            "extract(quarter FROM created_at) AS q FROM orders",
            database="Analytics",
        )
        field = ["field", {}, ["Analytics", "main", "orders", "created_at"]]
        expressions = query["stages"][0]["expressions"]
        for alias, op in {
            "y": "get-year",
            "m": "get-month",
            "d": "get-day",
            "h": "get-hour",
            "mi": "get-minute",
            "s": "get-second",
            "q": "get-quarter",
        }.items():
            self.assertEqual(expressions[alias], [op, {}, field])

    def test_temporal_extract_with_calendar_semantics_is_not_approximated(self) -> None:
        with self.assertRaisesRegex(ConversionError, "EXTRACT|extract|unidade"):
            convert_sql("SELECT extract(week FROM created_at) AS w FROM orders", database="Analytics")

    def test_simple_case_is_rewritten_as_explicit_equalities(self) -> None:
        query = convert_sql(
            "SELECT CASE status WHEN 'paid' THEN 1 WHEN 'open' THEN 2 ELSE 0 END AS code FROM orders",
            database="Analytics",
        )
        status = ["field", {}, ["Analytics", "main", "orders", "status"]]
        self.assertEqual(
            query["stages"][0]["expressions"]["code"],
            [
                "case",
                {},
                [
                    [["=", {}, status, "paid"], 1],
                    [["=", {}, status, "open"], 2],
                ],
                0,
            ],
        )

    def test_basic_casts_map_to_native_mbql_conversion_ops(self) -> None:
        query = convert_sql(
            "SELECT cast(status AS VARCHAR) AS text_status, "
            "cast(total AS INTEGER) AS int_total, cast(total AS DOUBLE) AS float_total FROM orders",
            database="Analytics",
        )
        expressions = query["stages"][0]["expressions"]
        status = ["field", {}, ["Analytics", "main", "orders", "status"]]
        total = ["field", {}, ["Analytics", "main", "orders", "total"]]
        self.assertEqual(expressions["text_status"], ["text", {}, status])
        self.assertEqual(expressions["int_total"], ["integer", {}, total])
        self.assertEqual(expressions["float_total"], ["float", {}, total])

    def test_unsafe_cast_families_fail_explicitly(self) -> None:
        for sql in (
            "SELECT cast(total AS DECIMAL(18,2)) AS x FROM orders",
            "SELECT try_cast(status AS INTEGER) AS x FROM orders",
        ):
            with self.subTest(sql=sql), self.assertRaisesRegex(ConversionError, "CAST|cast|convers"):
                convert_sql(sql, database="Analytics")

    def test_in_between_like_and_null_predicates(self) -> None:
        query = convert_sql(
            "SELECT id FROM orders "
            "WHERE status IN ('paid', 'shipped') "
            "AND total BETWEEN 10 AND 100 "
            "AND customer_name ILIKE 'ana%' "
            "AND cancelled_at IS NULL",
            database="Analytics",
        )
        filter_ = query["stages"][0]["filters"][0]
        rendered = repr(filter_)
        self.assertIn("'in'", rendered)
        self.assertIn("'between'", rendered)
        self.assertIn("'starts-with'", rendered)
        self.assertIn("'case-sensitive': False", rendered)
        self.assertIn("'is-null'", rendered)

    def test_population_stddev_and_variance_map_to_mbql(self) -> None:
        cases = (
            ("SELECT stddev_pop(total) AS spread FROM orders", "stddev"),
            ("SELECT var_pop(total) AS spread FROM orders", "var"),
        )
        for sql, operator in cases:
            with self.subTest(sql=sql):
                query = convert_sql(sql, database="Analytics")
                self.assertEqual(
                    query["stages"][0]["aggregation"],
                    [[operator, {"name": "spread"}, ["field", {}, ["Analytics", "main", "orders", "total"]]]],
                )

    def test_sample_stddev_and_variance_fail_instead_of_changing_semantics(self) -> None:
        for sql in (
            "SELECT stddev(total) AS spread FROM orders",
            "SELECT stddev_samp(total) AS spread FROM orders",
            "SELECT variance(total) AS spread FROM orders",
            "SELECT var_samp(total) AS spread FROM orders",
        ):
            with self.subTest(sql=sql), self.assertRaisesRegex(ConversionError, "não suportada"):
                convert_sql(sql, database="Analytics")


if __name__ == "__main__":
    unittest.main()
