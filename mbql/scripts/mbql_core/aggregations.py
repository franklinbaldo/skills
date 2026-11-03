# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Aggregations, their machine names, post-aggregation expressions and ordering."""

from __future__ import annotations

from typing import Any

from sqlglot import exp

from mbql_core.base import ConversionError
from mbql_core.expressions import ExpressionCompiler


class AggregationCompiler(ExpressionCompiler):
    """Aggregations, their machine names, post-aggregation expressions and ordering."""

    def _aggregate(self, node: exp.Expression) -> list[Any]:
        expression, _ = self._unwrap_alias(node)
        if isinstance(expression, exp.Count):
            arg = expression.this
            if isinstance(arg, exp.Distinct):
                if len(arg.expressions) != 1:
                    raise ConversionError(motivo="COUNT(DISTINCT ...) com múltiplos campos ainda não é suportado.")
                return ["distinct", {}, self._expr(arg.expressions[0])]
            if expression.args.get("distinct"):
                if arg is None:
                    raise ConversionError(motivo="COUNT(DISTINCT ...) sem campo não é suportado.")
                return ["distinct", {}, self._expr(arg)]
            if arg is None or isinstance(arg, exp.Star):
                return ["count", {}]
            return ["count", {}, self._expr(arg)]
        mapping: tuple[tuple[type[exp.Expression], str], ...] = (
            (exp.Sum, "sum"),
            (exp.Avg, "avg"),
            (exp.Min, "min"),
            (exp.Max, "max"),
            (exp.Median, "median"),
            (exp.StddevPop, "stddev"),
            (exp.VariancePop, "var"),
        )
        for cls, operator in mapping:
            if isinstance(expression, cls):
                return [operator, {}, self._expr(expression.this)]
        raise ConversionError(motivo=f"Agregação não suportada: {expression.sql(dialect='duckdb')}")

    def _register_aggregation_output(self, node: exp.Expression) -> str:
        base = self._aggregate_machine_base(node)
        self._aggregation_name_counts[base] += 1
        occurrence = self._aggregation_name_counts[base]
        output = base if occurrence == 1 else f"{base}_{occurrence}"
        self.aggregation_expression_outputs[self._expression_key(node)] = output
        return output

    def _post_aggregation_expr(self, node: exp.Expression) -> Any:
        if isinstance(node, exp.Paren):
            return self._post_aggregation_expr(node.this)
        if self._is_aggregate(node):
            name = self.aggregation_expression_outputs.get(self._expression_key(node))
            if name is None:
                raise ConversionError(
                    motivo="HAVING referencia uma agregação que não está projetada; "
                    "a inserção implícita dessa agregação ainda não tem contrato."
                )
            return ["field", {}, name]
        if isinstance(node, exp.Column):
            if not node.table:
                alias = self.aggregation_alias_outputs.get(node.name.lower())
                if alias is not None:
                    return ["field", {}, alias]
            return ["field", {}, node.name]
        if isinstance(node, (exp.Literal, exp.Null, exp.Boolean)):
            return self._expr(node)
        if isinstance(node, exp.Not):
            return ["not", {}, self._post_aggregation_expr(node.this)]
        if isinstance(node, exp.Is) and isinstance(node.expression, exp.Null):
            return ["is-null", {}, self._post_aggregation_expr(node.this)]
        if isinstance(node, exp.Between):
            return [
                "between",
                {},
                self._post_aggregation_expr(node.this),
                self._post_aggregation_expr(node.args["low"]),
                self._post_aggregation_expr(node.args["high"]),
            ]
        if isinstance(node, exp.In):
            if node.args.get("query") is not None:
                raise ConversionError(motivo="HAVING IN (subquery) ainda não é suportado.")
            return [
                "in",
                {},
                self._post_aggregation_expr(node.this),
                *[self._post_aggregation_expr(item) for item in node.expressions],
            ]

        comparisons: tuple[tuple[type[exp.Expression], str], ...] = (
            (exp.And, "and"),
            (exp.Or, "or"),
            (exp.EQ, "="),
            (exp.NEQ, "!="),
            (exp.GT, ">"),
            (exp.GTE, ">="),
            (exp.LT, "<"),
            (exp.LTE, "<="),
        )
        for cls, operator in comparisons:
            if isinstance(node, cls):
                return [
                    operator,
                    {},
                    self._post_aggregation_expr(node.this),
                    self._post_aggregation_expr(node.expression),
                ]
        if isinstance(node, (exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod)):
            raise ConversionError(
                motivo="HAVING com aritmética entre agregações permanece ambíguo; "
                "há um xfail executável cobrindo esse caso."
            )
        raise ConversionError(
            motivo=f"HAVING ainda não suportado para: {node.sql(dialect='duckdb')} ({type(node).__name__})"
        )

    def _order(self, ordered: exp.Expression) -> list[Any]:
        node = ordered.this if isinstance(ordered, exp.Ordered) else ordered
        direction = "desc" if isinstance(ordered, exp.Ordered) and bool(ordered.args.get("desc")) else "asc"
        ordinal_alias: str | None = None
        if isinstance(node, exp.Literal) and not node.is_string:
            node, ordinal_alias = self._projection_at(node, label="ORDER BY")

        if isinstance(node, exp.Column) and not node.table:
            alias_key = node.name.lower()
            idx = self.aggregation_aliases.get(alias_key)
            if idx is not None:
                return [direction, {}, ["aggregation", {}, idx]]
            projection = self.projection_aliases.get(alias_key)
            if projection is not None:
                if alias_key in self.breakout_aliases:
                    return [direction, {}, self._expr(projection)]
                return [direction, {}, ["expression", {}, node.name]]

        if self._is_aggregate(node):
            idx = self.aggregation_expression_indices.get(self._expression_key(node))
            if idx is not None:
                return [direction, {}, ["aggregation", {}, idx]]
            return [direction, {}, self._aggregate(node)]

        if ordinal_alias and ordinal_alias.lower() not in self.breakout_aliases:
            return [direction, {}, ["expression", {}, ordinal_alias]]
        return [direction, {}, self._expr(node)]
