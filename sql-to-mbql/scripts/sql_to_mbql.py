"""Conservative SQLGlot → legacy MBQL converter.

Never substitutes a native SQL query for a structured query. Unsupported SQL
fails explicitly rather than silently changing result semantics.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from sqlglot import exp, parse_one


class UnsupportedSQL(ValueError):
    """SQL cannot be represented exactly by the supported MBQL subset."""


def _field(node: exp.Expression, fields: dict[str, int]) -> list[Any]:
    if not isinstance(node, exp.Column) or node.table:
        raise UnsupportedSQL("only unqualified columns are supported")
    name = node.name
    if name not in fields:
        raise UnsupportedSQL(f"unknown field: {name}")
    return ["field", fields[name], None]


def _literal(node: exp.Expression) -> Any:
    if isinstance(node, exp.Null):
        return None
    if isinstance(node, exp.Boolean):
        return bool(node.this)
    if isinstance(node, exp.Literal):
        if node.is_string:
            return node.this
        try:
            return int(node.this)
        except ValueError:
            try:
                return float(node.this)
            except ValueError as exc:
                raise UnsupportedSQL("invalid numeric literal") from exc
    raise UnsupportedSQL(f"unsupported literal: {node.key}")


def _filter(node: exp.Expression, fields: dict[str, int]) -> list[Any]:
    if isinstance(node, exp.Paren):
        return _filter(node.this, fields)
    if isinstance(node, (exp.And, exp.Or)):
        return [node.key, _filter(node.left, fields), _filter(node.right, fields)]
    if isinstance(node, exp.Not):
        return ["not", _filter(node.this, fields)]
    for cls, op in ((exp.EQ, "="), (exp.NEQ, "!="),
                    (exp.GT, ">"), (exp.GTE, ">="),
                    (exp.LT, "<"), (exp.LTE, "<=")):
        if isinstance(node, cls):
            return [op, _field(node.left, fields), _literal(node.right)]
    if isinstance(node, exp.Is) and isinstance(node.expression, exp.Null):
        return ["is-null", _field(node.this, fields)]
    if isinstance(node, exp.In) and not node.args.get("query"):
        values = [_literal(item) for item in node.expressions]
        if not values or any(v is None for v in values):
            raise UnsupportedSQL("IN with empty set or NULL needs specialized semantics")
        return ["=", _field(node.this, fields), *values]
    raise UnsupportedSQL(f"unsupported predicate: {node.key}")


def convert(sql: str, schema: dict[str, Any], dialect: str = "mysql") -> dict[str, Any]:
    """Translate a deliberately small SELECT subset, rejecting all extra clauses.

    schema: {"tables": {"physical_name": {"id": 10, "fields": {"column": 20}}}}
    IDs are Metabase IDs, not guessed from database column positions.
    """
    try:
        tree = parse_one(sql, read=dialect)
    except Exception as exc:
        raise UnsupportedSQL("SQL parse failed") from exc
    if not isinstance(tree, exp.Select):
        raise UnsupportedSQL("only SELECT is supported")
    allowed = {"expressions", "from_", "where", "order", "limit"}
    extra = {key for key, value in tree.args.items() if value is not None and key not in allowed}
    if extra:
        raise UnsupportedSQL(f"unsupported SELECT clauses: {sorted(extra)}")
    source = tree.args.get("from_")
    if not isinstance(source, exp.From) or not isinstance(source.this, exp.Table):
        raise UnsupportedSQL("one physical table is required")
    table = source.this
    if table.alias or table.db or table.catalog:
        raise UnsupportedSQL("table aliases and qualified tables unsupported")
    table_name = table.name
    tables = schema.get("tables", {})
    if table_name not in tables:
        raise UnsupportedSQL(f"unknown table: {table_name}")
    metadata = tables[table_name]
    fields = metadata["fields"]
    if not isinstance(metadata["id"], int) or isinstance(metadata["id"], bool):
        raise UnsupportedSQL("table id must be numeric")
    query: dict[str, Any] = {"source-table": metadata["id"]}
    projections = list(tree.expressions)
    if not (len(projections) == 1 and isinstance(projections[0], exp.Star)):
        if not projections:
            raise UnsupportedSQL("empty projection")
        query["fields"] = [_field(projection, fields) for projection in projections]
    where = tree.args.get("where")
    if where is not None:
        query["filter"] = _filter(where.this, fields)
    order = tree.args.get("order")
    if order is not None:
        query["order-by"] = [
            ["desc" if ordered.args.get("desc") else "asc", _field(ordered.this, fields)]
            for ordered in order.expressions
        ]
    limit = tree.args.get("limit")
    if limit is not None:
        n = _literal(limit.expression)
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise UnsupportedSQL("LIMIT must be a positive integer")
        query["limit"] = n
    return {"type": "query", "query": query}


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert safe SELECT SQL to structured MBQL")
    parser.add_argument("sql")
    parser.add_argument("--schema", required=True, help="JSON schema file with Metabase IDs")
    parser.add_argument("--dialect", default="mysql")
    args = parser.parse_args()
    with open(args.schema, encoding="utf-8") as stream:
        schema = json.load(stream)
    print(json.dumps(convert(args.sql, schema, args.dialect), ensure_ascii=False))


if __name__ == "__main__":
    main()
