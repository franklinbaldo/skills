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

    def convert(self, sql: str) -> dict[str, Any]:
        try:
            node = parse_one(sql, read="duckdb")
        except ParseError as exc:
            raise ConversionError(f"DuckDB SQL inválido: {exc}") from exc

        if not isinstance(node, exp.Select):
            raise ConversionError("A v1 converte apenas uma instrução SELECT simples.")
        if node.args.get("with_"):
            raise ConversionError("CTEs ainda não são suportadas; materialize ou simplifique a consulta.")
        if any(node.find_all(exp.Window)):
            raise ConversionError("Window functions ainda não são suportadas.")
        if node.args.get("having"):
            raise ConversionError("HAVING ainda não é suportado com tradução segura na v1.")
        if node.args.get("qualify"):
            raise ConversionError("QUALIFY ainda não é suportado.")
        if node.args.get("distinct"):
            raise ConversionError("SELECT DISTINCT ainda não é suportado.")

        from_ = node.args.get("from_")
        if from_ is None or not isinstance(from_.this, exp.Table):
            raise ConversionError("FROM deve apontar diretamente para uma tabela.")

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
                aggregations.append(self._aggregate(expression))
                if alias:
                    self.aggregation_aliases[alias.lower()] = idx
                continue

            if group_exprs:
                # GROUP BY defines the projected dimensions in MBQL.
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
            raise ConversionError("OFFSET ainda não é suportado pelo conversor v1.")

        return {"lib/type": "mbql/query", "stages": [stage]}

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
            raise ConversionError("JOIN ON suporta apenas comparações ligadas por AND na v1.")

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
            # SQL "IS NOT NULL" arrives as NOT(IS(...)).
            if isinstance(node.this, exp.Is) and isinstance(node.this.expression, exp.Null):
                return ["not-null", {}, self._expr(node.this.this)]
            return ["not", {}, self._expr(node.this)]
        if isinstance(node, exp.Is):
            if isinstance(node.expression, exp.Null):
                return ["is-null", {}, self._expr(node.this)]
            raise ConversionError("IS só é suportado para NULL na v1.")
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
        if isinstance(node, exp.Like):
            pattern = self._expr(node.expression)
            if not isinstance(pattern, str):
                raise ConversionError("LIKE exige padrão literal na v1.")
            # MBQL contains/starts-with/ends-with are safer than pretending full LIKE support.
            if "%" not in pattern and "_" not in pattern:
                return ["=", {}, self._expr(node.this), pattern]
            if "_" in pattern or pattern.count("%") > 2 or ("%" in pattern[1:-1]):
                raise ConversionError("LIKE complexo (%, _) ainda não é suportado.")
            if pattern.startswith("%") and pattern.endswith("%"):
                return ["contains", {}, self._expr(node.this), pattern[1:-1]]
            if pattern.endswith("%"):
                return ["starts-with", {}, self._expr(node.this), pattern[:-1]]
            if pattern.startswith("%"):
                return ["ends-with", {}, self._expr(node.this), pattern[1:]]
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
            if expression.args.get("distinct"):
                raise ConversionError("COUNT(DISTINCT ...) ainda não é suportado na v1.")
            arg = expression.this
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
            raise ConversionError(f"{label} deve ser inteiro literal na v1.")
        try:
            value = int(node.this)
        except ValueError as exc:
            raise ConversionError(f"{label} deve ser inteiro literal na v1.") from exc
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
