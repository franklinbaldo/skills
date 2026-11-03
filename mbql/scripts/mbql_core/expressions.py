# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Scalar SQL expressions and LIKE patterns compiled to MBQL clauses."""

from __future__ import annotations

from typing import Any

from sqlglot import exp

from mbql_core.base import ConversionError, ConverterBase, _safe_sql


class ExpressionCompiler(ConverterBase):
    """Scalar SQL expressions and LIKE patterns compiled to MBQL clauses."""

    def _expr(self, node: exp.Expression) -> Any:
        if isinstance(node, exp.Paren):
            return self._expr(node.this)
        if isinstance(node, exp.Column):
            return self._field(node)
        if isinstance(node, exp.Literal):
            if node.is_string:
                return node.this
            try:
                return int(node.this)
            except ValueError:
                try:
                    return float(node.this)
                except ValueError as exc:
                    raise ConversionError(motivo=f"Literal numérico inválido: {node.this}") from exc
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
            raise ConversionError(motivo="IS só é suportado para NULL.")
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
                raise ConversionError(motivo="IN (subquery) ainda não é suportado.")
            return [
                "in",
                {},
                self._expr(node.this),
                *[self._expr(item) for item in node.expressions],
            ]
        if isinstance(node, exp.ILike):
            return self._like(node, case_sensitive=False)
        if isinstance(node, exp.Like):
            return self._like(node, case_sensitive=True)
        if isinstance(node, exp.Lower):
            return ["lower", {}, self._expr(node.this)]
        if isinstance(node, exp.Upper):
            return ["upper", {}, self._expr(node.this)]
        if isinstance(node, exp.Coalesce):
            args = [node.this, *node.expressions]
            return ["coalesce", {}, *[self._expr(item) for item in args if item is not None]]
        if isinstance(node, exp.Abs):
            return ["abs", {}, self._expr(node.this)]
        if isinstance(node, exp.Concat):
            return ["concat", {}, *[self._expr(item) for item in node.expressions]]
        if isinstance(node, exp.Substring):
            args = ["substring", {}, self._expr(node.this)]
            start = node.args.get("start")
            length = node.args.get("length")
            if start is not None:
                args.append(self._expr(start))
            if length is not None:
                args.append(self._expr(length))
            return args
        if isinstance(node, exp.Replace):
            replacement = node.args.get("replacement")
            if replacement is None:
                raise ConversionError(motivo="REPLACE sem o texto de substituição não tem contrato MBQL.")
            return [
                "replace",
                {},
                self._expr(node.this),
                self._expr(node.expression),
                self._expr(replacement),
            ]
        if isinstance(node, exp.Trim):
            if node.expression is not None or node.args.get("position") is not None:
                raise ConversionError(
                    motivo="TRIM com caracteres/direção explícitos ainda não tem contrato MBQL nesta skill."
                )
            return ["trim", {}, self._expr(node.this)]
        if isinstance(node, exp.Length):
            return ["length", {}, self._expr(node.this)]
        if isinstance(node, exp.If):
            clause: list[Any] = [
                "case",
                {},
                [[self._expr(node.this), self._expr(node.args["true"])]],
            ]
            fallback = node.args.get("false")
            if fallback is not None:
                clause.append(self._expr(fallback))
            return clause
        if isinstance(node, exp.Case):
            base = node.this
            cases: list[list[Any]] = []
            for branch in node.args.get("ifs") or []:
                condition = branch.this
                if base is not None:
                    condition = exp.EQ(this=base.copy(), expression=condition.copy())
                cases.append([self._expr(condition), self._expr(branch.args["true"])])
            if not cases:
                raise ConversionError(motivo="CASE sem braços WHEN não é suportado.")
            clause: list[Any] = ["case", {}, cases]
            default = node.args.get("default")
            if default is not None:
                clause.append(self._expr(default))
            return clause
        if isinstance(node, exp.Extract):
            unit = node.this.sql(dialect="duckdb").strip("'\"").lower()
            operators = {
                "year": "get-year",
                "month": "get-month",
                "day": "get-day",
                "hour": "get-hour",
                "minute": "get-minute",
                "second": "get-second",
                "quarter": "get-quarter",
            }
            operator = operators.get(unit)
            if operator is None:
                raise ConversionError(
                    motivo=f"EXTRACT com unidade {unit!r} ainda não tem contrato MBQL explícito nesta skill."
                )
            return [operator, {}, self._expr(node.expression)]
        if isinstance(node, exp.TryCast):
            raise ConversionError(motivo="TRY_CAST não tem contrato equivalente no subconjunto MBQL suportado.")
        if isinstance(node, exp.Cast):
            target = node.to.sql(dialect="duckdb").upper()
            if target in {"VARCHAR", "TEXT"}:
                return ["text", {}, self._expr(node.this)]
            if target in {"TINYINT", "SMALLINT", "INTEGER", "INT", "BIGINT", "HUGEINT"}:
                return ["integer", {}, self._expr(node.this)]
            if target in {"REAL", "FLOAT", "DOUBLE"}:
                return ["float", {}, self._expr(node.this)]
            if target == "DATE":
                # O `date` do MBQL compila para `CAST(x AS date)` nos drivers SQL
                # (metabase.driver.sql.query-processor, ->honeysql [:sql :date]).
                return ["date", {}, self._expr(node.this)]
            raise ConversionError(
                motivo=f"CAST para {target} ainda não tem equivalência MBQL explícita; "
                "não será aproximado por outra conversão."
            )
        if isinstance(node, exp.Alias):
            return self._expr(node.this)

        binary_ops: tuple[tuple[type[exp.Expression], str], ...] = (
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
        )
        for cls, operator in binary_ops:
            if isinstance(node, cls):
                return [operator, {}, self._expr(node.this), self._expr(node.expression)]
        raise ConversionError(motivo=f"Expressão DuckDB ainda não suportada: {_safe_sql(node)} ({type(node).__name__})")

    def _like(self, node: exp.Expression, *, case_sensitive: bool) -> list[Any]:
        pattern = self._expr(node.expression)
        if not isinstance(pattern, str):
            raise ConversionError(motivo="LIKE/ILIKE exige padrão literal.")
        options: dict[str, Any] = {"case-sensitive": case_sensitive}
        if "%" not in pattern and "_" not in pattern:
            return ["=", options, self._expr(node.this), pattern]
        if "_" in pattern or pattern.count("%") > 2 or "%" in pattern[1:-1]:
            raise ConversionError(motivo="LIKE/ILIKE complexo (wildcards internos ou _) ainda não é suportado.")
        if pattern.startswith("%") and pattern.endswith("%"):
            return ["contains", options, self._expr(node.this), pattern[1:-1]]
        if pattern.endswith("%"):
            return ["starts-with", options, self._expr(node.this), pattern[:-1]]
        if pattern.startswith("%"):
            return ["ends-with", options, self._expr(node.this), pattern[1:]]
        raise ConversionError(motivo="LIKE/ILIKE não pôde ser normalizado com segurança.")
