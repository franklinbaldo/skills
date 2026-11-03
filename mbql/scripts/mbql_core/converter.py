# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Top-level SELECT, linear subqueries and CTE chains compiled as stage pipelines."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlglot import exp, parse_one, transpile
from sqlglot.errors import ErrorLevel, ParseError, UnsupportedError

from mbql_core.base import ConversionError
from mbql_core.rewrite import CaseSensitiveEquality, rewrite_for_mbql
from mbql_core.rewrite_window import UniqueRowPerGroup
from mbql_core.stages import StageCompiler


class Converter(StageCompiler):
    """Top-level SELECT, linear subqueries and CTE chains compiled as stage pipelines."""

    def convert(self, sql: str) -> dict[str, Any]:
        try:
            node = parse_one(sql, read="duckdb")
        except ParseError as exc:
            raise ConversionError(motivo=f"DuckDB SQL inválido: {exc}") from exc

        if not isinstance(node, exp.Select):
            raise ConversionError(motivo="O conversor aceita apenas uma instrução SELECT por vez.")
        return self._convert_select(node)

    def _convert_select(self, node: exp.Select) -> dict[str, Any]:
        with_ = node.args.get("with_")
        if with_ is not None:
            return self._convert_cte_chain(node, with_)
        if any(node.find_all(exp.Window)):
            raise ConversionError(motivo="Window functions ainda não são suportadas.")
        if node.args.get("qualify"):
            raise ConversionError(motivo="QUALIFY ainda não é suportado.")

        from_ = node.args.get("from_")
        if from_ is None:
            raise ConversionError(motivo="SELECT sem FROM ainda não tem contrato portátil nesta skill.")
        if isinstance(from_.this, exp.Subquery):
            return self._convert_linear_subquery(node, from_.this)
        if not isinstance(from_.this, exp.Table):
            raise ConversionError(motivo="FROM deve apontar para tabela ou subquery SELECT linear.")

        self.source = self._register_table(from_.this)
        stage: dict[str, Any] = {
            "lib/type": "mbql.stage/mbql",
            "source-table": self.source.portable,
        }
        return self._compile_stage(node, stage)

    def _convert_cte_chain(self, node: exp.Select, with_: exp.With) -> dict[str, Any]:
        if bool(with_.args.get("recursive")):
            raise ConversionError(motivo="WITH RECURSIVE ainda não é suportado.")
        if not with_.expressions:
            raise ConversionError(motivo="WITH sem CTE não é suportado.")

        stages: list[dict[str, Any]] = []
        previous_alias: str | None = None
        previous_name_map: dict[str, str] = {}

        for index, raw_cte in enumerate(with_.expressions):
            if not isinstance(raw_cte, exp.CTE) or not isinstance(raw_cte.this, exp.Select):
                raise ConversionError(motivo="Cada CTE da cadeia deve conter um SELECT.")
            alias = raw_cte.alias_or_name
            if not alias:
                raise ConversionError(motivo="Cada CTE da cadeia precisa de alias.")

            select = raw_cte.this
            self._validate_cross_stage_outputs(select)

            if index == 0:
                compiler = type(self)(database=self.database, default_schema=self.default_schema)
                compiled = compiler.convert(select.sql(dialect="duckdb"))
                stages.extend(compiled["stages"])
            else:
                from_ = select.args.get("from_")
                if (
                    from_ is None
                    or not isinstance(from_.this, exp.Table)
                    or previous_alias is None
                    or from_.this.name.lower() != previous_alias.lower()
                    or select.args.get("joins")
                ):
                    raise ConversionError(
                        motivo="Múltiplos CTEs só são suportados quando formam uma cadeia linear, "
                        "cada um consumindo exclusivamente o CTE anterior."
                    )
                compiler = type(self)(database=self.database, default_schema=self.default_schema)
                compiler.cross_stage_alias = previous_alias
                compiler.cross_stage_name_map = dict(previous_name_map)
                compiled = compiler._compile_stage(select, {"lib/type": "mbql.stage/mbql"})
                stages.extend(compiled["stages"])

            previous_alias = alias
            previous_name_map = self._output_name_map(select, compiler)

        outer = node.copy()
        outer.set("with_", None)
        from_ = outer.args.get("from_")
        if (
            from_ is None
            or not isinstance(from_.this, exp.Table)
            or previous_alias is None
            or from_.this.name.lower() != previous_alias.lower()
            or outer.args.get("joins")
        ):
            raise ConversionError(motivo="A query externa deve consumir exclusivamente o último CTE da cadeia linear.")

        self.cross_stage_alias = previous_alias
        self.cross_stage_name_map = dict(previous_name_map)
        self.source = None
        compiled_outer = self._compile_stage(outer, {"lib/type": "mbql.stage/mbql"})
        return {
            "lib/type": "mbql/query",
            "stages": [*stages, *compiled_outer["stages"]],
        }

    def _convert_linear_subquery(self, node: exp.Select, subquery: exp.Subquery) -> dict[str, Any]:
        if not isinstance(subquery.this, exp.Select):
            raise ConversionError(motivo="Subquery em FROM deve conter SELECT.")
        alias = subquery.alias_or_name
        if not alias:
            raise ConversionError(motivo="Subquery em FROM precisa de alias para refs cross-stage.")
        return self._convert_linear_source(node, subquery.this, alias)

    def _convert_linear_source(
        self,
        outer: exp.Select,
        inner: exp.Select,
        alias: str,
    ) -> dict[str, Any]:
        if outer.args.get("joins"):
            raise ConversionError(motivo="JOIN sobre subquery/CTE linear ainda não é suportado.")
        self._validate_cross_stage_outputs(inner)

        inner_converter = type(self)(database=self.database, default_schema=self.default_schema)
        inner_query = inner_converter.convert(inner.sql(dialect="duckdb"))
        self.cross_stage_alias = alias
        self.cross_stage_name_map = self._output_name_map(inner, inner_converter)
        self.source = None
        stage: dict[str, Any] = {"lib/type": "mbql.stage/mbql"}
        compiled = self._compile_stage(outer, stage)
        return {
            "lib/type": "mbql/query",
            "stages": [*inner_query["stages"], *compiled["stages"]],
        }


def convert_sql(
    sql: str,
    *,
    database: str,
    schema: str | None = "main",
    source_dialect: str = "duckdb",
    tables: Mapping[str, Mapping[str, str]] | None = None,
    primary_keys: Mapping[str, str] | None = None,
    guards: list[CaseSensitiveEquality | UniqueRowPerGroup] | None = None,
) -> dict[str, Any]:
    """Convert SQL from a source dialect to portable MBQL 5, without lossy fallback.

    With `tables` (the database's tables and columns) the query is first
    rewritten by `mbql_core.rewrite` (CTEs inlined, primary-key
    semijoins as joins, derived tables merged) where that keeps the result.
    """
    if tables is not None:
        sql = rewrite_for_mbql(
            sql,
            dialect=source_dialect,
            tables=tables,
            primary_keys=primary_keys,
            guards=guards,
        )
    if source_dialect.lower() != "duckdb":
        try:
            normalized = transpile(
                sql,
                read=source_dialect,
                write="duckdb",
                unsupported_level=ErrorLevel.RAISE,
            )
        except (ParseError, UnsupportedError, ValueError, KeyError) as exc:
            raise ConversionError(motivo=f"Falha ao normalizar SQL {source_dialect!r}: {exc}") from exc
        if len(normalized) != 1:
            raise ConversionError(motivo="A conversão exige exatamente uma instrução SQL.")
        sql = normalized[0]
    _refuse_renamed_final_breakout(sql)
    converter = Converter(database=database, default_schema=schema)
    query = converter.convert(sql)
    _name_final_aggregations(query, converter.aggregation_alias_names)
    return query


def _refuse_renamed_final_breakout(sql: str) -> None:
    """A grouped outer query whose grouped column has another name has no MBQL form.

    Metabase names a breakout column after the column itself and ignores a
    `name` option on it (the aggregations do take one), so `SELECT t.a AS b
    ... GROUP BY t.a` would come back as `a`.
    """
    try:
        tree = parse_one(sql, read="duckdb")
    except ParseError as exc:
        raise ConversionError(motivo=f"DuckDB SQL inválido: {exc}") from exc
    if not isinstance(tree, exp.Select) or tree.args.get("group") is None:
        return
    for projection in tree.expressions:
        if (
            isinstance(projection, exp.Alias)
            and isinstance(projection.this, exp.Column)
            and projection.alias.lower() != projection.this.name.lower()
        ):
            raise ConversionError(
                motivo=f"Coluna agrupada {projection.this.name!r} renomeada para "
                f"{projection.alias!r} na consulta final: o MBQL não dá nome a breakout."
            )


def _name_final_aggregations(query: dict[str, Any], names: Mapping[int, str]) -> None:
    """Give the outer query's aggregations their SQL aliases as column names.

    Only the final stage: an inner stage is read by machine name (`count`,
    `count_2`), so renaming it would break the stage that reads it.
    """
    aggregations = query["stages"][-1].get("aggregation", [])
    for index, name in names.items():
        if index < len(aggregations) and isinstance(aggregations[index][1], dict):
            aggregations[index][1]["name"] = name
