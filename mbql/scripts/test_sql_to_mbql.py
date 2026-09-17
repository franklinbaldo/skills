#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Regression tests for the DuckDB SQL -> portable MBQL converter."""

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

    def test_having_fails_instead_of_changing_semantics(self) -> None:
        with self.assertRaisesRegex(ConversionError, "HAVING"):
            convert_sql(
                "SELECT status, count(*) FROM orders GROUP BY status HAVING count(*) > 3",
                database="Analytics",
            )


if __name__ == "__main__":
    unittest.main()
