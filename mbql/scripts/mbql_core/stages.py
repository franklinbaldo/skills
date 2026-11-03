# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""One MBQL stage: projection, grouping, joins, limit and cross-stage names."""

from __future__ import annotations

from typing import Any

from sqlglot import exp

from mbql_core.aggregations import AggregationCompiler
from mbql_core.base import ConversionError, _safe_sql


class StageCompiler(AggregationCompiler):
    """One MBQL stage: projection, grouping, joins, limit and cross-stage names."""

    def convert(self, sql: str) -> dict[str, Any]:
        """Compile a whole SELECT; a derived join needs it for its subquery.

        The top layer (`mbql_core.converter.Converter`) implements it.
        """
        raise NotImplementedError

    def _compile_stage(self, node: exp.Select, stage: dict[str, Any]) -> dict[str, Any]:
        self._register_projection_metadata(node)

        joins = node.args.get("joins") or []
        if joins:
            stage["joins"] = [self._join(join) for join in joins]

        where = node.args.get("where")
        if where is not None:
            stage["filters"] = [self._expr(where.this)]

        group = node.args.get("group")
        group_exprs = self._resolve_group_exprs(group)
        if group_exprs:
            stage["breakout"] = [self._expr(item) for item in group_exprs]

        distinct = bool(node.args.get("distinct"))
        simple_distinct = (
            distinct
            and bool(node.expressions)
            and all(isinstance(item, exp.Column) for item in node.expressions)
            and not group_exprs
            and node.args.get("having") is None
        )
        if distinct and not simple_distinct:
            raise ConversionError(
                motivo="SELECT DISTINCT só tem contrato seguro para uma coluna direta; "
                "expressões/aliases/formas compostas permanecem ambíguas."
            )

        if simple_distinct:
            stage["breakout"] = [self._expr(item) for item in node.expressions]
        else:
            self._project(node, stage, group_exprs)

        order = node.args.get("order")
        if order is not None:
            stage["order-by"] = [self._order(item) for item in order.expressions]

        self._apply_limit_offset(node, stage)

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

    def _register_projection_metadata(self, node: exp.Select) -> None:
        self.projection_positions = []
        self.projection_position_aliases = []
        for projection in node.expressions:
            expression, alias = self._unwrap_alias(projection)
            self.projection_positions.append(expression)
            self.projection_position_aliases.append(alias)
            if alias:
                key = alias.lower()
                existing = self.projection_aliases.get(key)
                if existing is not None and existing != expression:
                    raise ConversionError(motivo=f"Alias de projeção ambíguo: {alias!r}.")
                self.projection_aliases[key] = expression

    def _resolve_group_exprs(self, group: exp.Group | None) -> list[exp.Expression]:
        if group is None:
            return []
        resolved: list[exp.Expression] = []
        for item in group.expressions:
            expression = item
            if isinstance(item, exp.Literal) and not item.is_string:
                expression, _ = self._projection_at(item, label="GROUP BY")
            elif isinstance(item, exp.Column) and not item.table:
                expression = self.projection_aliases.get(item.name.lower(), item)
            if self._is_aggregate(expression):
                raise ConversionError(motivo="GROUP BY não pode resolver para uma agregação.")
            resolved.append(expression)
        return resolved

    def _project(self, node: exp.Select, stage: dict[str, Any], group_exprs: list[exp.Expression]) -> None:
        aggregations: list[Any] = []
        fields: list[Any] = []
        expressions: dict[str, Any] = {}
        has_aggregate = False

        for projection in node.expressions:
            expression, alias = self._unwrap_alias(projection)
            if isinstance(expression, exp.Star):
                if len(node.expressions) != 1 or group_exprs:
                    raise ConversionError(motivo="SELECT * só é suportado como projeção única sem GROUP BY.")
                continue

            if self._is_aggregate(expression):
                has_aggregate = True
                idx = len(aggregations)
                aggregations.append(self._aggregate(expression))
                self.aggregation_expression_indices[self._expression_key(expression)] = idx
                output_name = self._register_aggregation_output(expression)
                if alias:
                    self.aggregation_aliases[alias.lower()] = idx
                    self.aggregation_alias_names[idx] = alias
                    self.aggregation_alias_outputs[alias.lower()] = output_name
                continue

            if group_exprs:
                if not self._matches_any(expression, group_exprs):
                    raise ConversionError(motivo=f"Projeção não agregada fora do GROUP BY: {_safe_sql(expression)}")
                if alias:
                    self.breakout_aliases.add(alias.lower())
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

    def _apply_limit_offset(self, node: exp.Select, stage: dict[str, Any]) -> None:
        limit = node.args.get("limit")
        offset = node.args.get("offset")
        if offset is None:
            if limit is not None:
                stage["limit"] = self._integer_literal(limit.expression, "LIMIT")
            return
        if limit is None:
            raise ConversionError(motivo="OFFSET sem LIMIT não tem mapeamento MBQL exato para page/items.")
        items = self._integer_literal(limit.expression, "LIMIT")
        offset_value = self._integer_literal(offset.expression, "OFFSET")
        if items == 0:
            raise ConversionError(motivo="LIMIT 0 com OFFSET não pode ser representado como page/items.")
        if offset_value % items:
            raise ConversionError(
                motivo="OFFSET não alinhado ao LIMIT não é representável exatamente por MBQL page/items; "
                f"OFFSET={offset_value}, LIMIT={items}."
            )
        stage["page"] = {"page": offset_value // items + 1, "items": items}

    def _join(self, join: exp.Join) -> dict[str, Any]:
        alias: str | None = None
        stages: list[dict[str, Any]]

        if isinstance(join.this, exp.Table):
            table = self._register_table(join.this, joined=True)
            alias = table.join_alias
            stages = [{"lib/type": "mbql.stage/mbql", "source-table": table.portable}]
        elif isinstance(join.this, exp.Subquery) and isinstance(join.this.this, exp.Select):
            alias = join.this.alias_or_name
            if not alias:
                raise ConversionError(motivo="JOIN em subquery precisa de alias.")
            self._validate_cross_stage_outputs(join.this.this)
            inner_converter = type(self)(database=self.database, default_schema=self.default_schema)
            inner_query = inner_converter.convert(join.this.this.sql(dialect="duckdb"))
            stages = inner_query["stages"]
            self.derived_join_name_maps[alias.lower()] = self._output_name_map(join.this.this, inner_converter)
        else:
            raise ConversionError(motivo="JOIN suporta tabela direta ou subquery SELECT linear.")

        on = join.args.get("on")
        if on is None:
            raise ConversionError(motivo="JOIN sem ON ainda não é suportado.")
        parts = self._flatten_and(on)
        if isinstance(join.this, exp.Table) and alias:
            own = [part for part in parts if self._only_columns_of(part, alias)]
            if own:
                # `JOIN b ON k AND p(b)` == `JOIN (SELECT * FROM b WHERE p(b)) ON k`,
                # for INNER and LEFT alike: the filter goes to the join's stage.
                filtered = exp.select("*").from_(join.this.copy()).where(exp.and_(*(part.copy() for part in own)))
                inner = type(self)(database=self.database, default_schema=self.default_schema)
                stages = inner.convert(filtered.sql(dialect="duckdb"))["stages"]
                parts = [part for part in parts if all(part is not mine for mine in own)]
            if not parts:
                raise ConversionError(motivo="JOIN ON sem condição que ligue as duas tabelas.")
        conditions = [self._expr(part) for part in parts]
        allowed = {"=", "!=", "<", "<=", ">", ">="}
        if any(not isinstance(clause, list) or not clause or clause[0] not in allowed for clause in conditions):
            raise ConversionError(motivo="JOIN ON suporta apenas comparações ligadas por AND.")
        return {
            "alias": alias,
            "strategy": self._join_strategy(join),
            "stages": stages,
            "conditions": conditions,
        }

    @staticmethod
    def _only_columns_of(part: exp.Expression, alias: str) -> bool:
        """A predicate that reads only the joined table, with no subquery inside."""
        if any(part.find_all(exp.Subquery, exp.Select)):
            return False
        columns = list(part.find_all(exp.Column))
        return bool(columns) and all(column.table.lower() == alias.lower() for column in columns)

    def _output_name_map(self, select: exp.Select, compiler: "StageCompiler") -> dict[str, str]:
        mapping: dict[str, str] = {}
        grouped = select.args.get("group") is not None
        for projection in select.expressions:
            expression, alias = self._unwrap_alias(projection)
            if isinstance(expression, exp.Star):
                continue
            if self._is_aggregate(expression):
                if alias:
                    machine = compiler.aggregation_alias_outputs.get(alias.lower())
                    if machine is not None:
                        mapping[alias.lower()] = machine
                continue
            if alias:
                if grouped and isinstance(expression, exp.Column):
                    mapping[alias.lower()] = expression.name
                else:
                    mapping[alias.lower()] = alias
                continue
            if isinstance(expression, exp.Column):
                actual = (
                    compiler.cross_stage_name_map.get(expression.name.lower(), expression.name)
                    if compiler.cross_stage_alias is not None
                    else expression.name
                )
                mapping[expression.name.lower()] = actual
        return mapping

    def _validate_cross_stage_outputs(self, inner: exp.Select) -> None:
        grouped = inner.args.get("group") is not None
        for projection in inner.expressions:
            expression, alias = self._unwrap_alias(projection)
            if self._is_aggregate(expression):
                if not alias:
                    raise ConversionError(
                        motivo="Agregação em fonte derivada precisa de alias SQL explícito para resolver o machine name MBQL."
                    )
                continue
            if grouped and not isinstance(expression, exp.Column):
                raise ConversionError(
                    motivo="Breakout por expressão dentro de fonte derivada ainda não tem machine name cross-stage estável."
                )
            if not grouped and not isinstance(expression, (exp.Column, exp.Star)) and not alias:
                raise ConversionError(
                    motivo="Expressão sem alias em fonte derivada não tem machine name cross-stage estável."
                )
