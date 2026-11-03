#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3.0", "sqlglot>=27,<29"]
# ///
"""Regression tests for multi-stage conversion: joins, HAVING, DISTINCT, OFFSET, subqueries and CTEs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sql_to_mbql import ConversionError, convert_sql


class SqlToMbqlStageTests(unittest.TestCase):
    def test_left_join_adds_join_alias_to_joined_fields(self) -> None:
        query = convert_sql(
            "SELECT o.id, c.name FROM orders o LEFT JOIN customers c ON o.customer_id = c.id WHERE c.active = true",
            database="Analytics",
        )
        stage = query["stages"][0]
        join = stage["joins"][0]

        self.assertEqual(join["alias"], "c")
        self.assertEqual(join["strategy"], "left-join")
        self.assertEqual(
            join["conditions"],
            [
                [
                    "=",
                    {},
                    ["field", {}, ["Analytics", "main", "orders", "customer_id"]],
                    ["field", {"join-alias": "c"}, ["Analytics", "main", "customers", "id"]],
                ]
            ],
        )
        self.assertEqual(
            stage["filters"],
            [["=", {}, ["field", {"join-alias": "c"}, ["Analytics", "main", "customers", "active"]], True]],
        )

    def test_join_against_linear_subquery_uses_nested_join_stages(self) -> None:
        query = convert_sql(
            "SELECT o.id, q.revenue FROM orders o "
            "LEFT JOIN (SELECT customer_id, sum(total) AS revenue "
            "FROM invoices GROUP BY customer_id) q "
            "ON o.customer_id = q.customer_id",
            database="Analytics",
        )
        stage = query["stages"][0]
        join = stage["joins"][0]
        self.assertEqual(join["alias"], "q")
        self.assertEqual(join["strategy"], "left-join")
        self.assertEqual(
            join["stages"][0]["source-table"],
            ["Analytics", "main", "invoices"],
        )
        self.assertEqual(
            join["conditions"],
            [
                [
                    "=",
                    {},
                    ["field", {}, ["Analytics", "main", "orders", "customer_id"]],
                    ["field", {"join-alias": "q"}, "customer_id"],
                ]
            ],
        )
        self.assertEqual(
            stage["fields"],
            [
                ["field", {}, ["Analytics", "main", "orders", "id"]],
                ["field", {"join-alias": "q"}, "sum"],
            ],
        )

    def test_join_subquery_maps_plain_projection_aliases(self) -> None:
        query = convert_sql(
            "SELECT o.id, q.customer FROM orders o "
            "LEFT JOIN (SELECT id AS customer, active FROM customers) q "
            "ON o.customer_id = q.customer",
            database="Analytics",
        )
        stage = query["stages"][0]
        self.assertEqual(
            stage["joins"][0]["conditions"],
            [
                [
                    "=",
                    {},
                    ["field", {}, ["Analytics", "main", "orders", "customer_id"]],
                    ["field", {"join-alias": "q"}, "customer"],
                ]
            ],
        )
        self.assertEqual(
            stage["fields"][1],
            ["field", {"join-alias": "q"}, "customer"],
        )

    def test_unqualified_column_with_join_is_rejected_as_ambiguous(self) -> None:
        with self.assertRaisesRegex(ConversionError, "qualific|ambígu"):
            convert_sql(
                "SELECT name FROM orders o JOIN customers c ON o.customer_id = c.id",
                database="Analytics",
            )

    def test_having_on_aggregation_becomes_second_stage_filter(self) -> None:
        query = convert_sql(
            "SELECT status, count(*) AS n FROM orders GROUP BY status HAVING count(*) > 3",
            database="Analytics",
        )
        self.assertEqual(len(query["stages"]), 2)
        self.assertEqual(
            query["stages"][1]["filters"],
            [[">", {}, ["field", {}, "count"], 3]],
        )

    def test_having_alias_resolves_to_previous_stage_machine_name(self) -> None:
        query = convert_sql(
            "SELECT status, sum(total) AS revenue FROM orders GROUP BY status HAVING revenue >= 1000",
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
            [["distinct", {"name": "customers"}, ["field", {}, ["Analytics", "main", "orders", "customer_id"]]]],
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

    def test_select_distinct_multiple_direct_columns_maps_to_breakouts(self) -> None:
        query = convert_sql(
            "SELECT DISTINCT status, customer_id FROM orders ORDER BY status, customer_id",
            database="Analytics",
        )
        self.assertEqual(
            query["stages"][0]["breakout"],
            [
                ["field", {}, ["Analytics", "main", "orders", "status"]],
                ["field", {}, ["Analytics", "main", "orders", "customer_id"]],
            ],
        )

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
            "SELECT status, sum(total) FROM orders GROUP BY status HAVING sum(total) / count(*) > 10",
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

    def test_simple_from_subquery_linearizes_to_second_stage(self) -> None:
        query = convert_sql(
            "SELECT id FROM (SELECT id, total FROM orders WHERE total > 10) q WHERE id > 1",
            database="Analytics",
        )
        self.assertEqual(len(query["stages"]), 2)
        inner, outer = query["stages"]
        self.assertEqual(inner["source-table"], ["Analytics", "main", "orders"])
        self.assertEqual(
            outer["fields"],
            [["field", {}, "id"]],
        )
        self.assertEqual(
            outer["filters"],
            [[">", {}, ["field", {}, "id"], 1]],
        )
        self.assertNotIn("source-table", outer)

    def test_multiple_ctes_in_linear_chain_become_multiple_stages(self) -> None:
        query = convert_sql(
            "WITH x AS (SELECT id, total FROM orders), "
            "y AS (SELECT id, total FROM x WHERE total > 10) "
            "SELECT id FROM y WHERE id > 1",
            database="Analytics",
        )
        self.assertEqual(len(query["stages"]), 3)
        self.assertEqual(query["stages"][1]["filters"], [[">", {}, ["field", {}, "total"], 10]])
        self.assertEqual(query["stages"][2]["fields"], [["field", {}, "id"]])
        self.assertEqual(query["stages"][2]["filters"], [[">", {}, ["field", {}, "id"], 1]])

    def test_cte_chain_preserves_aggregate_sql_name_mapping(self) -> None:
        query = convert_sql(
            "WITH x AS (SELECT status, sum(total) AS revenue FROM orders GROUP BY status), "
            "y AS (SELECT status, revenue FROM x WHERE revenue > 10) "
            "SELECT revenue FROM y",
            database="Analytics",
        )
        self.assertEqual(len(query["stages"]), 3)
        self.assertEqual(query["stages"][1]["fields"], [["field", {}, "status"], ["field", {}, "sum"]])
        self.assertEqual(query["stages"][2]["fields"], [["field", {}, "sum"]])

    def test_single_cte_single_use_linearizes_to_second_stage(self) -> None:
        query = convert_sql(
            "WITH x AS (SELECT id, total FROM orders WHERE total > 10) SELECT id FROM x WHERE total < 100",
            database="Analytics",
        )
        self.assertEqual(len(query["stages"]), 2)
        self.assertEqual(query["stages"][1]["fields"], [["field", {}, "id"]])
        self.assertEqual(
            query["stages"][1]["filters"],
            [["<", {}, ["field", {}, "total"], 100]],
        )

    def test_subquery_aggregate_alias_resolves_to_machine_name(self) -> None:
        query = convert_sql(
            "SELECT revenue FROM (SELECT sum(total) AS revenue FROM orders) q",
            database="Analytics",
        )
        self.assertEqual(query["stages"][1]["fields"], [["field", {}, "sum"]])

    def test_grouped_subquery_exposes_plain_breakout_and_aggregate_alias(self) -> None:
        query = convert_sql(
            "SELECT status, revenue FROM (SELECT status, sum(total) AS revenue FROM orders GROUP BY status) q",
            database="Analytics",
        )
        self.assertEqual(
            query["stages"][1]["fields"],
            [["field", {}, "status"], ["field", {}, "sum"]],
        )

    def test_grouped_breakout_alias_resolves_to_source_machine_name(self) -> None:
        query = convert_sql(
            "SELECT s FROM (SELECT status AS s, sum(total) AS revenue FROM orders GROUP BY status) q",
            database="Analytics",
        )
        self.assertEqual(query["stages"][1]["fields"], [["field", {}, "status"]])

    @unittest.expectedFailure
    def test_grouped_breakout_expression_alias_remains_ambiguous(self) -> None:
        query = convert_sql(
            "SELECT s FROM (SELECT lower(status) AS s, sum(total) AS revenue FROM orders GROUP BY lower(status)) q",
            database="Analytics",
        )
        self.assertEqual(query["stages"][1]["fields"], [["field", {}, "s"]])

    def test_in_subquery_still_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(ConversionError, "subquery|Subquery"):
            convert_sql(
                "SELECT id FROM orders WHERE id IN (SELECT id FROM customers)",
                database="Analytics",
            )


if __name__ == "__main__":
    unittest.main()
