#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Regression/specification tests for the DuckDB SQL -> portable MBQL converter."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sql_to_mbql import ConversionError, convert_sql


class SqlToMbqlTests(unittest.TestCase):
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
        self.assertEqual(stage["aggregation"][0], ["count", {}])
        self.assertEqual(
            stage["aggregation"][1],
            ["sum", {}, ["field", {}, ["Warehouse", "sales", "orders", "total"]]],
        )
        self.assertEqual(stage["order-by"], [["desc", {}, ["aggregation", {}, 1]]])

    def test_left_join_adds_join_alias_to_joined_fields(self) -> None:
        query = convert_sql(
            "SELECT o.id, c.name FROM orders o "
            "LEFT JOIN customers c ON o.customer_id = c.id "
            "WHERE c.active = true",
            database="Analytics",
        )
        stage = query["stages"][0]
        join = stage["joins"][0]

        self.assertEqual(join["alias"], "c")
        self.assertEqual(join["strategy"], "left-join")
        self.assertEqual(
            join["conditions"],
            [[
                "=",
                {},
                ["field", {}, ["Analytics", "main", "orders", "customer_id"]],
                ["field", {"join-alias": "c"}, ["Analytics", "main", "customers", "id"]],
            ]],
        )
        self.assertEqual(
            stage["filters"],
            [["=", {}, ["field", {"join-alias": "c"}, ["Analytics", "main", "customers", "active"]], True]],
        )

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

    def test_having_on_aggregation_becomes_second_stage_filter(self) -> None:
        query = convert_sql(
            "SELECT status, count(*) AS n FROM orders "
            "GROUP BY status HAVING count(*) > 3",
            database="Analytics",
        )
        self.assertEqual(len(query["stages"]), 2)
        self.assertEqual(
            query["stages"][1]["filters"],
            [[">", {}, ["field", {}, "count"], 3]],
        )

    def test_having_alias_resolves_to_previous_stage_machine_name(self) -> None:
        query = convert_sql(
            "SELECT status, sum(total) AS revenue FROM orders "
            "GROUP BY status HAVING revenue >= 1000",
            database="Analytics",
        )
        self.assertEqual(
            query["stages"][1]["filters"],
            [[">=", {}, ["field", {}, "sum"], 1000]],
        )

    def test_count_distinct_maps_to_distinct_aggregation(self) -> None:
        query = convert_sql(
            "SELECT count(DISTINCT customer_id) AS customers FROM orders",
            database="Analytics",
        )
        self.assertEqual(
            query["stages"][0]["aggregation"],
            [["distinct", {}, ["field", {}, ["Analytics", "main", "orders", "customer_id"]]]],
        )

    def test_select_distinct_single_column_maps_to_breakout(self) -> None:
        query = convert_sql(
            "SELECT DISTINCT status FROM orders WHERE total > 0 ORDER BY status DESC LIMIT 10",
            database="Analytics",
        )
        stage = query["stages"][0]
        self.assertEqual(
            stage["breakout"],
            [["field", {}, ["Analytics", "main", "orders", "status"]]],
        )
        self.assertNotIn("fields", stage)
        self.assertEqual(stage["order-by"][0][0], "desc")
        self.assertEqual(stage["limit"], 10)

    @unittest.expectedFailure
    def test_select_distinct_expression_remains_ambiguous(self) -> None:
        query = convert_sql(
            "SELECT DISTINCT lower(status) FROM orders",
            database="Analytics",
        )
        self.assertIn("breakout", query["stages"][0])

    def test_aligned_offset_maps_exactly_to_page(self) -> None:
        query = convert_sql(
            "SELECT id FROM orders ORDER BY id LIMIT 10 OFFSET 20",
            database="Analytics",
        )
        stage = query["stages"][0]
        self.assertEqual(stage["page"], {"items": 10, "page": 3})
        self.assertNotIn("limit", stage)

    @unittest.expectedFailure
    def test_unaligned_offset_remains_ambiguous(self) -> None:
        query = convert_sql(
            "SELECT id FROM orders ORDER BY id LIMIT 10 OFFSET 5",
            database="Analytics",
        )
        self.assertEqual(query["stages"][0]["page"], {"items": 10, "page": 1.5})

    @unittest.expectedFailure
    def test_having_expression_without_stable_output_name_is_ambiguous(self) -> None:
        query = convert_sql(
            "SELECT status, sum(total) FROM orders "
            "GROUP BY status HAVING sum(total) / count(*) > 10",
            database="Analytics",
        )
        self.assertEqual(len(query["stages"]), 2)

    @unittest.expectedFailure
    def test_window_function_requires_multistage_semantics(self) -> None:
        query = convert_sql(
            "SELECT id, row_number() OVER (PARTITION BY status ORDER BY created_at) AS rn FROM orders",
            database="Analytics",
        )
        self.assertIn("expressions", query["stages"][0])

    def test_subquery_still_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(ConversionError, "subquery|Subquery|FROM"):
            convert_sql(
                "SELECT id FROM (SELECT id FROM orders) q",
                database="Analytics",
            )


if __name__ == "__main__":
    unittest.main()
