#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Convert a practical subset of DuckDB SQL to portable Metabase MBQL 5."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

JSON = dict[str, Any] | list[Any] | str | int | float | bool | None


class ConversionError(ValueError):
    """Raised when SQL cannot be translated without guessing semantics."""


@dataclass(frozen=True)
class TableRef:
    database: str
    schema: str | None
    table: str
    alias: str
    join_alias: str | None = None

    @property
    def portable(self) -> list[str | None]:
        return [self.database, self.schema, self.table]


class Converter:
    def __init__(self, *, database: str, default_schema: str | None = "main") -> None:
        self.database = database
        self.default_schema = default_schema
        self.tables: dict[str, TableRef] = {}
        self.source: TableRef | None = None
        self.aggregation_aliases: dict[str, int] = {}
        self.aggregation_alias_outputs: dict[str, str] = {}
        self.aggregation_expression_outputs: dict[str, str] = {}
        self._aggregation_name_counts: Counter[str] = Counter()

    def convert(self, sql: str) -> dict[str, Any]:
        try:
            node = parse_one(sql, read="duckdb")
        except ParseError as exc:
            raise ConversionError(f"DuckDB SQL inválido: {exc}") from exc

        if not isinstance(node, exp.Select):
            raise ConversionError("O conversor aceita apenas uma instrução SELECT por vez.")
        if node.args.get("with_"):
            raise ConversionError("CTEs ainda não são suportadas; materialize ou simplifique a consulta.")
        if any(node.find_all(exp.Window)):
            raise ConversionError("Window functions ainda não são suportadas.")
        if node.args.get("qualify"):
            raise ConversionError("QUALIFY ainda não é suportado.")
        if node.args.get("distinct"):
            raise ConversionError(
                "SELECT DISTINCT permanece ambíguo no contrato portátil; "
                "há um xfail executável cobrindo a decisão pendente."
            )

        from_ = node.args.get("from_")
        if from_ is None or not isinstance(from_.this, exp.Table):
            raise ConversionError("FROM deve apontar diretamente para uma tabela; subquery ainda não é suportada.")

        self.source = self._register_table(from_.this)
        stage: dict[str, Any] = {
            "lib/type": "mbql.stage/mbql",
            "source-table": self.source.portable,
        }

        joins = node.args.get("joins") or []
        if joins:
            stage["joins"] = [self._join(j) for j in joins]

        where = node.args.get("where")
        if where is not None:
            stage["filters"] = [self._expr(where.this)]

        group = node.args.get("group")
        group_exprs = list(group.expressions) if group is not None else []
        if group_exprs:
            stage["breakout"] = [self._expr(e) for e in group_exprs]

        aggregations: list[Any] = []
        fields: list[Any] = []
        expressions: dict[str, Any] = {}
        has_aggregate = False

        for projection in node.expressions:
            expression, alias = self._unwrap_alias(projection)
            if isinstance(expression, exp.Star):
                if len(node.expressions) != 1 or group_exprs:
                    raise ConversionError("SELECT * só é suportado como projeção única sem GROUP BY.")
                continue

            if self._is_aggregate(expression):
                has_aggregate = True
                idx = len(aggregations)
                aggregation = self._aggregate(expression)
                aggregations.append(aggregation)
                output_name = self._register_aggregation_output(expression)
                if alias:
                    self.aggregation_aliases[alias.lower()] = idx
                    self.aggregation_alias_outputs[alias.lower()] = output_name
                continue

            if group_exprs:
                if not self._matches_any(expression, group_exprs):
                    raise ConversionError(
                        f"Projeção não agregada fora do GROUP BY: {expression.sql(dialect='duckdb')}"
                    )
                continue

            if alias:
                expressions[alias] = self._expr(expression)
                fields.append(["expression", {}, alias])
            else:
                fields.append(self._expr(expression))

        if aggregations:
            stage["aggregation"] = aggregations
        if fields and not has_aggregate:
            stage["fields"] = fields
        if expressions:
            stage["expressions"] = expressions

        order = node.args.get("order")
        if order is not None:
            stage["order-by"] = [self._order(item) for item in order.expressions]

        limit = node.args.get("limit")
        if limit is not None:
            stage["limit"] = self._integer_literal(limit.expression, "LIMIT")

        offset = node.args.get("offset")
        if offset is not None:
            raise ConversionError(
                "OFFSET permanece sem contrato portátil definido; há um xfail executável para page/items."
            )

        stages = [stage]
        having = node.args.get("having")
        if having is not None:
            stages.append(
                {
                    "lib/type": "mbql.stage/mbql",
                    "filters": [self._post_aggregation_expr(having.this)],
                }
            )

        return {"lib/type": "mbql/query", "stages": stages}

    def _register_table(self, table: exp.Table, *, joined: bool = False) -> TableRef:
        if table.catalog:
            raise ConversionError(
                "Referência DuckDB catalog.schema.table não é traduzida automaticamente; "
                "passe o database do Metabase em --database e use schema.table."
            )
        schema = table.db or self.default_schema
        name = table.name
        alias = table.alias_or_name
        if not name:
            raise ConversionError("Tabela sem nome não é suportada.")
        ref = TableRef(
            database=self.database,
            schema=schema,
            table=name,
            alias=alias,
            join_alias=alias if joined else None,
        )
        for key in {alias.lower(), name.lower()}:
            existing = self.tables.get(key)
            if existing is not None and existing != ref:
                raise ConversionError(f"Alias de tabela ambíguo: {key}")
            self.tables[key] = ref
        return ref

    def _join(self, join: exp.Join) -> dict[str, Any]:
        if not isinstance(join.this, exp.Table):
            raise ConversionError("JOIN em subquery ainda não é suportado.")
        table = self._register_table(join.this, joined=True)
        on = join.args.get("on")
        if on is None:
            raise ConversionError("JOIN sem ON ainda não é suportado.")

        conditions = [self._expr(part) for part in self._flatten_and(on)]
        allowed = {"=", "!=", "<", "<=", ">", ">="}
        if any(not isinstance(c, list) or not c or c[0] not in allowed for c in conditions):
            raise ConversionError("JOIN ON suporta apenas comparações ligadas por AND.")

        return {
            "alias": table.join_alias,
            "strategy": self._join_strategy(join),
            "stages": [
                {
                    "lib/type": "mbql.stage/mbql",
                    "source-table": table.portable,
                }
            ],
            "conditions": conditions,
        }

    @staticmethod
    def _join_strategy(join: exp.Join) -> str:
        side = (join.args.get("side") or "").upper()
        kind = (join.args.get("kind") or "").upper()
        if side == "LEFT":
            return "left-join"
        if side == "RIGHT":
            return "right-join"
        if side == "FULL":
            return "full-join"
        if kind in {"INNER", ""}:
            return "inner-join"
        raise ConversionError(f"Tipo de JOIN ainda não suportado: {side or kind}")

    def _field(self, column: exp.Column) -> list[Any]:
        table_name = column.table
        if table_name:
            ref = self.tables.get(table_name.lower())
            if ref is None:
                raise ConversionError(f"Tabela/alias desconhecido no campo {column.sql()!r}.")
        else:
            if self.source is None:
                raise AssertionError("source not initialized")
            ref = self.source

        options: dict[str, Any] = {}
        if ref.join_alias:
            options["join-alias"] = ref.join_alias
        return ["field", options, [ref.database, ref.schema, ref.table, column.name]]

    def _expr(self, node: exp.Expression) -> Any:
        if isinstance(node, exp.Paren):
            return self._expr(node.this)
        if isinstance(node, exp.Column):
            return self._field(node)
        if isinstance(node, exp.Literal):
            if node.is_string:
                return node.this
            text = node.this
            try:
                return int(text)
            except ValueError:
                try:
                    return float(text)
                except ValueError as exc:
                    raise ConversionError(f"Literal numérico inválido: {text}") from exc
        if isinstance(node, exp.Null):
            return None
        if isinstance(node, exp.Boolean):
            return bool(node.this)
        if isinstance(node, exp.Neg):
            value = self._expr(node.this)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return -value
            return ["-", {}, 0, value]
        if isinstance(node, exp.Not):
            if isinstance(node.this, exp.Is) and isinstance(node.this.expression, exp.Null):
                return ["not-null", {}, self._expr(node.this.this)]
            return ["not", {}, self._expr(node.this)]
        if isinstance(node, exp.Is):
            if isinstance(node.expression, exp.Null):
                return ["is-null", {}, self._expr(node.this)]
            raise ConversionError("IS só é suportado para NULL.")
        if isinstance(node, exp.Between):
            return [
                "between",
                {},
                self._expr(node.this),
                self._expr(node.args["low"]),
                self._expr(node.args["high"]),
            ]
        if isinstance(node, exp.In):
            if node.args.get("query") is not None:
                raise ConversionError("IN (subquery) ainda não é suportado.")
            return ["in", {}, self._expr(node.this), *[self._expr(e) for e in node.expressions]]
        if isinstance(node, exp.ILike):
            return self._like(node, case_sensitive=False)
        if isinstance(node, exp.Like):
            return self._like(node, case_sensitive=True)
        if isinstance(node, exp.Alias):
            return self._expr(node.this)

        binary_ops: list[tuple[type[exp.Expression], str]] = [
            (exp.And, "and"),
            (exp.Or, "or"),
            (exp.EQ, "="),
            (exp.NEQ, "!="),
            (exp.GT, ">"),
            (exp.GTE, ">="),
            (exp.LT, "<"),
            (exp.LTE, "<="),
            (exp.Add, "+"),
            (exp.Sub, "-"),
            (exp.Mul, "*"),
            (exp.Div, "/"),
            (exp.Mod, "mod"),
        ]
        for cls, op in binary_ops:
            if isinstance(node, cls):
                return [op, {}, self._expr(node.this), self._expr(node.expression)]

        raise ConversionError(
            f"Expressão DuckDB ainda não suportada: {node.sql(dialect='duckdb')} ({type(node).__name__})"
        )

    def _like(self, node: exp.Expression, *, case_sensitive: bool) -> list[Any]:
        pattern = self._expr(node.expression)
        if not isinstance(pattern, str):
            raise ConversionError("LIKE/ILIKE exige padrão literal.")
        options: dict[str, Any] = {"case-sensitive": case_sensitive}
        if "%" not in pattern and "_" not in pattern:
            return ["=", options, self._expr(node.this), pattern]
        if "_" in pattern or pattern.count("%") > 2 or "%" in pattern[1:-1]:
            raise ConversionError("LIKE/ILIKE complexo (wildcards internos ou _) ainda não é suportado.")
        if pattern.startswith("%") and pattern.endswith("%"):
            return ["contains", options, self._expr(node.this), pattern[1:-1]]
        if pattern.endswith("%"):
            return ["starts-with", options, self._expr(node.this), pattern[:-1]]
        if pattern.startswith("%"):
            return ["ends-with", options, self._expr(node.this), pattern[1:]]
        raise ConversionError("LIKE/ILIKE não pôde ser normalizado com segurança.")

    def _aggregate(self, node: exp.Expression) -> list[Any]:
        expression, _ = self._unwrap_alias(node)
        mapping: list[tuple[type[exp.Expression], str]] = [
            (exp.Sum, "sum"),
            (exp.Avg, "avg"),
            (exp.Min, "min"),
            (exp.Max, "max"),
            (exp.Median, "median"),
        ]
        if isinstance(expression, exp.Count):
            arg = expression.this
            if isinstance(arg, exp.Distinct):
                if len(arg.expressions) != 1:
                    raise ConversionError("COUNT(DISTINCT ...) com múltiplos campos ainda não é suportado.")
                return ["distinct", {}, self._expr(arg.expressions[0])]
            if expression.args.get("distinct"):
                if arg is None:
                    raise ConversionError("COUNT(DISTINCT ...) sem campo não é suportado.")
                return ["distinct", {}, self._expr(arg)]
            if arg is None or isinstance(arg, exp.Star):
                return ["count", {}]
            return ["count", {}, self._expr(arg)]
        for cls, op in mapping:
            if isinstance(expression, cls):
                return [op, {}, self._expr(expression.this)]
        raise ConversionError(f"Agregação não suportada: {expression.sql(dialect='duckdb')}")

    @staticmethod
    def _is_aggregate(node: exp.Expression) -> bool:
        return isinstance(node, (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max, exp.Median))

    @staticmethod
    def _aggregate_machine_base(node: exp.Expression) -> str:
        if isinstance(node, exp.Count):
            arg = node.this
            if isinstance(arg, exp.Distinct) or node.args.get("distinct"):
                return "distinct"
            return "count"
        if isinstance(node, exp.Sum):
            return "sum"
        if isinstance(node, exp.Avg):
            return "avg"
        if isinstance(node, exp.Min):
            return "min"
        if isinstance(node, exp.Max):
            return "max"
        if isinstance(node, exp.Median):
            return "median"
        raise ConversionError(f"Agregação sem machine name conhecido: {node.sql(dialect='duckdb')}")

    def _register_aggregation_output(self, node: exp.Expression) -> str:
        base = self._aggregate_machine_base(node)
        self._aggregation_name_counts[base] += 1
        occurrence = self._aggregation_name_counts[base]
        output = base if occurrence == 1 else f"{base}_{occurrence}"
        self.aggregation_expression_outputs[self._expression_key(node)] = output
        return output

    @staticmethod
    def _expression_key(node: exp.Expression) -> str:
        return node.sql(dialect="duckdb", normalize=True).lower()

    def _post_aggregation_expr(self, node: exp.Expression) -> Any:
        if isinstance(node, exp.Paren):
            return self._post_aggregation_expr(node.this)
        if self._is_aggregate(node):
            name = self.aggregation_expression_outputs.get(self._expression_key(node))
            if name is None:
                raise ConversionError(
                    "HAVING referencia uma agregação que não está projetada; "
                    "a inserção implícita dessa agregação ainda não tem contrato."
                )
            return ["field", {}, name]
        if isinstance(node, exp.Column):
            if not node.table:
                alias_name = self.aggregation_alias_outputs.get(node.name.lower())
                if alias_name is not None:
                    return ["field", {}, alias_name]
            return ["field", {}, node.name]
        if isinstance(node, exp.Literal):
            return self._expr(node)
        if isinstance(node, exp.Null):
            return None
        if isinstance(node, exp.Boolean):
            return bool(node.this)
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
                raise ConversionError("HAVING IN (subquery) ainda não é suportado.")
            return [
                "in",
                {},
                self._post_aggregation_expr(node.this),
                *[self._post_aggregation_expr(e) for e in node.expressions],
            ]

        comparison_ops: list[tuple[type[exp.Expression], str]] = [
            (exp.And, "and"),
            (exp.Or, "or"),
            (exp.EQ, "="),
            (exp.NEQ, "!="),
            (exp.GT, ">"),
            (exp.GTE, ">="),
            (exp.LT, "<"),
            (exp.LTE, "<="),
        ]
        for cls, op in comparison_ops:
            if isinstance(node, cls):
                return [
                    op,
                    {},
                    self._post_aggregation_expr(node.this),
                    self._post_aggregation_expr(node.expression),
                ]

        if isinstance(node, (exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod)):
            raise ConversionError(
                "HAVING com aritmética entre agregações permanece ambíguo; "
                "há um xfail executável cobrindo esse caso."
            )

        raise ConversionError(
            f"HAVING ainda não suportado para: {node.sql(dialect='duckdb')} ({type(node).__name__})"
        )

    def _order(self, ordered: exp.Expression) -> list[Any]:
        node = ordered.this if isinstance(ordered, exp.Ordered) else ordered
        direction = "desc" if isinstance(ordered, exp.Ordered) and bool(ordered.args.get("desc")) else "asc"
        if isinstance(node, exp.Column) and not node.table:
            idx = self.aggregation_aliases.get(node.name.lower())
            if idx is not None:
                return [direction, {}, ["aggregation", {}, idx]]
        if self._is_aggregate(node):
            clause = self._aggregate(node)
            return [direction, {}, clause]
        return [direction, {}, self._expr(node)]

    @staticmethod
    def _unwrap_alias(node: exp.Expression) -> tuple[exp.Expression, str | None]:
        if isinstance(node, exp.Alias):
            return node.this, node.alias
        return node, None

    @staticmethod
    def _matches_any(node: exp.Expression, candidates: list[exp.Expression]) -> bool:
        return any(node == candidate for candidate in candidates)

    @staticmethod
    def _flatten_and(node: exp.Expression) -> list[exp.Expression]:
        if isinstance(node, exp.And):
            return Converter._flatten_and(node.this) + Converter._flatten_and(node.expression)
        return [node]

    @staticmethod
    def _integer_literal(node: exp.Expression | None, label: str) -> int:
        if not isinstance(node, exp.Literal) or node.is_string:
            raise ConversionError(f"{label} deve ser inteiro literal.")
        try:
            value = int(node.this)
        except ValueError as exc:
            raise ConversionError(f"{label} deve ser inteiro literal.") from exc
        if value < 0:
            raise ConversionError(f"{label} não pode ser negativo.")
        return value


def convert_sql(sql: str, *, database: str, schema: str | None = "main") -> dict[str, Any]:
    """Convert one DuckDB SELECT into portable MBQL 5."""
    return Converter(database=database, default_schema=schema).convert(sql)


def _read_sql(value: str | None, file: Path | None) -> str:
    if value and file:
        raise ConversionError("Use SQL posicional ou --file, não os dois.")
    if file:
        return file.read_text(encoding="utf-8")
    if value:
        return value
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ConversionError("Informe o SQL como argumento, --file, ou stdin.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql", nargs="?", help="DuckDB SQL SELECT")
    parser.add_argument("--file", type=Path, help="arquivo .sql (alternativa ao argumento)")
    parser.add_argument("--database", required=True, help="nome exato do database no Metabase")
    parser.add_argument("--schema", default="main", help="schema para tabelas não qualificadas (default: main)")
    parser.add_argument("--compact", action="store_true", help="emitir JSON em uma linha")
    args = parser.parse_args(argv)

    try:
        sql = _read_sql(args.sql, args.file)
        query = convert_sql(sql, database=args.database, schema=args.schema or None)
    except (ConversionError, OSError) as exc:
        parser.error(str(exc))

    if args.compact:
        print(json.dumps(query, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(query, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
