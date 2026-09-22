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
            "SELECT lower(status) AS normalized, COUNT(*) AS n "
            "FROM orders GROUP BY normalized ORDER BY normalized ASC",
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
            [[
                "=",
                {},
                ["field", {}, ["Analytics", "main", "orders", "customer_id"]],
                ["field", {"join-alias": "q"}, "customer_id"],
            ]],
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
            [[
                "=",
                {},
                ["field", {}, ["Analytics", "main", "orders", "customer_id"]],
                ["field", {"join-alias": "q"}, "customer"],
            ]],
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
            "SELECT cast(created_at AS DATE) AS x FROM orders",
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
                    [[operator, {}, ["field", {}, ["Analytics", "main", "orders", "total"]]]],
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
            "WITH x AS (SELECT id, total FROM orders WHERE total > 10) "
            "SELECT id FROM x WHERE total < 100",
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
            "SELECT status, revenue FROM "
            "(SELECT status, sum(total) AS revenue FROM orders GROUP BY status) q",
            database="Analytics",
        )
        self.assertEqual(
            query["stages"][1]["fields"],
            [["field", {}, "status"], ["field", {}, "sum"]],
        )

    def test_grouped_breakout_alias_resolves_to_source_machine_name(self) -> None:
        query = convert_sql(
            "SELECT s FROM (SELECT status AS s, sum(total) AS revenue "
            "FROM orders GROUP BY status) q",
            database="Analytics",
        )
        self.assertEqual(query["stages"][1]["fields"], [["field", {}, "status"]])

    @unittest.expectedFailure
    def test_grouped_breakout_expression_alias_remains_ambiguous(self) -> None:
        query = convert_sql(
            "SELECT s FROM (SELECT lower(status) AS s, sum(total) AS revenue "
            "FROM orders GROUP BY lower(status)) q",
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
