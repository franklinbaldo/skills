# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Conversion state, table registry and the leaf helpers every layer uses."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlglot import exp


class ConversionError(ValueError):
    """Raised when SQL cannot be translated without guessing semantics."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


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


def _safe_sql(node: exp.Expression) -> str:
    """Render an expression for diagnostics without letting sqlglot generator bugs escape."""
    try:
        return node.sql(dialect="duckdb")
    except Exception:  # noqa: BLE001 - só diagnóstico; o gerador do sqlglot pode levantar qualquer coisa
        return f"<{type(node).__name__}>"


class ConverterBase:
    """Conversion state, table registry and the leaf helpers every layer uses."""

    def __init__(self, *, database: str, default_schema: str | None = "main") -> None:
        self.database = database
        self.default_schema = default_schema
        self.tables: dict[str, TableRef] = {}
        # Nome de tabela usado por mais de um alias: só é erro se uma coluna o citar.
        self.ambiguous_names: set[str] = set()
        self.source: TableRef | None = None
        self.aggregation_aliases: dict[str, int] = {}
        self.aggregation_alias_outputs: dict[str, str] = {}
        # Índice da agregação -> alias SQL original, da última etapa compilada aqui.
        self.aggregation_alias_names: dict[int, str] = {}
        self.aggregation_expression_outputs: dict[str, str] = {}
        self.aggregation_expression_indices: dict[str, int] = {}
        self.projection_aliases: dict[str, exp.Expression] = {}
        self.projection_positions: list[exp.Expression] = []
        self.projection_position_aliases: list[str | None] = []
        self.breakout_aliases: set[str] = set()
        self.cross_stage_alias: str | None = None
        self.cross_stage_name_map: dict[str, str] = {}
        self.derived_join_name_maps: dict[str, dict[str, str]] = {}
        self._aggregation_name_counts: Counter[str] = Counter()

    def _register_table(self, table: exp.Table, *, joined: bool = False) -> TableRef:
        if table.catalog:
            raise ConversionError(
                motivo="Referência DuckDB catalog.schema.table não é traduzida automaticamente; "
                "passe o database do Metabase em --database e use schema.table."
            )
        schema = table.db or self.default_schema
        name = table.name
        alias = table.alias_or_name
        if not name:
            raise ConversionError(motivo="Tabela sem nome não é suportada.")
        ref = TableRef(
            database=self.database,
            schema=schema,
            table=name,
            alias=alias,
            join_alias=alias if joined else None,
        )
        existing = self.tables.get(alias.lower())
        if existing is not None and existing != ref:
            raise ConversionError(motivo=f"Alias de tabela ambíguo: {alias.lower()}")
        self.tables[alias.lower()] = ref
        nome = name.lower()
        if nome != alias.lower():
            anterior = self.tables.get(nome)
            if nome in self.ambiguous_names or (anterior is not None and anterior != ref):
                self.ambiguous_names.add(nome)
                self.tables.pop(nome, None)
            else:
                self.tables[nome] = ref
        return ref

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
        raise ConversionError(motivo=f"Tipo de JOIN ainda não suportado: {side or kind}")

    def _field(self, column: exp.Column) -> list[Any]:
        if column.table:
            derived_map = self.derived_join_name_maps.get(column.table.lower())
            if derived_map is not None:
                name = derived_map.get(column.name.lower(), column.name)
                return ["field", {"join-alias": column.table}, name]
        if self.cross_stage_alias is not None:
            if column.table and column.table.lower() != self.cross_stage_alias.lower():
                raise ConversionError(
                    motivo=f"Alias desconhecido em ref cross-stage {_safe_sql(column)!r}; esperado {self.cross_stage_alias!r}."
                )
            name = self.cross_stage_name_map.get(column.name.lower(), column.name)
            return ["field", {}, name]
        if column.table:
            if column.table.lower() in self.ambiguous_names:
                raise ConversionError(motivo=f"Alias de tabela ambíguo: {column.table.lower()}")
            ref = self.tables.get(column.table.lower())
            if ref is None:
                raise ConversionError(motivo=f"Tabela/alias desconhecido no campo {column.sql()!r}.")
        else:
            if self.source is None:
                raise AssertionError("source_not_initialized")
            if self.derived_join_name_maps or any(table.join_alias for table in self.tables.values()):
                raise ConversionError(
                    motivo=f"Coluna sem qualificação em query com JOIN é ambígua: {column.name!r}; "
                    "qualifique com o alias/tabela de origem."
                )
            ref = self.source
        options: dict[str, Any] = {}
        if ref.join_alias:
            options["join-alias"] = ref.join_alias
        return ["field", options, [ref.database, ref.schema, ref.table, column.name]]

    def _projection_at(self, ordinal: exp.Expression, *, label: str) -> tuple[exp.Expression, str | None]:
        if not isinstance(ordinal, exp.Literal) or ordinal.is_string:
            raise ConversionError(motivo=f"{label} ordinal deve ser inteiro literal.")
        try:
            position = int(ordinal.this)
        except ValueError as exc:
            raise ConversionError(motivo=f"{label} ordinal deve ser inteiro literal.") from exc
        if position < 1 or position > len(self.projection_positions):
            raise ConversionError(
                motivo=f"{label} ordinal fora do SELECT: {position}; há {len(self.projection_positions)} projeções."
            )
        index = position - 1
        return self.projection_positions[index], self.projection_position_aliases[index]

    @staticmethod
    def _is_aggregate(node: exp.Expression) -> bool:
        return isinstance(
            node,
            (
                exp.Count,
                exp.Sum,
                exp.Avg,
                exp.Min,
                exp.Max,
                exp.Median,
                exp.StddevPop,
                exp.VariancePop,
            ),
        )

    @staticmethod
    def _aggregate_machine_base(node: exp.Expression) -> str:
        if isinstance(node, exp.Count):
            # O Metabase chama a contagem distinta de "count", como a contagem
            # (metabase.lib.aggregation, column-name-method).
            return "count"
        for cls, name in (
            (exp.Sum, "sum"),
            (exp.Avg, "avg"),
            (exp.Min, "min"),
            (exp.Max, "max"),
            (exp.Median, "median"),
            (exp.StddevPop, "stddev"),
            (exp.VariancePop, "var"),
        ):
            if isinstance(node, cls):
                return name
        raise ConversionError(motivo=f"Agregação sem machine name conhecido: {node.sql(dialect='duckdb')}")

    @staticmethod
    def _expression_key(node: exp.Expression) -> str:
        return node.sql(dialect="duckdb", normalize=True).lower()

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
            return ConverterBase._flatten_and(node.this) + ConverterBase._flatten_and(node.expression)
        return [node]

    @staticmethod
    def _integer_literal(node: exp.Expression | None, label: str) -> int:
        if not isinstance(node, exp.Literal) or node.is_string:
            raise ConversionError(motivo=f"{label} deve ser inteiro literal.")
        try:
            value = int(node.this)
        except ValueError as exc:
            raise ConversionError(motivo=f"{label} deve ser inteiro literal.") from exc
        if value < 0:
            raise ConversionError(motivo=f"{label} não pode ser negativo.")
        return value
