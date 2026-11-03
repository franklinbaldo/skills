# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""SQL-to-SQL rewrites that keep the result and bring a query into the converter's subset.

Each rewrite applies only where its equivalence holds by construction; any
other shape is left as it is, for the converter to accept or refuse.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlglot import exp, parse_one
from sqlglot.errors import OptimizeError, ParseError
from sqlglot.optimizer.merge_subqueries import merge_subqueries
from sqlglot.optimizer.qualify import qualify

from mbql_core.base import ConversionError
from mbql_core.rewrite_window import UniqueRowPerGroup, latest_per_group

# Funções cujo valor muda a cada avaliação: copiar uma CTE que as usa para
# cada referência poderia mudar o resultado.
_VOLATEIS = (exp.CurrentTimestamp, exp.CurrentDate, exp.CurrentTime, exp.Rand)

# Limite de passadas da semijunção derivada; nas consultas reais medidas a profundidade é 2 ou 3.
_PASSADAS = 8


def rewrite_for_mbql(
    sql: str,
    *,
    dialect: str,
    tables: Mapping[str, Mapping[str, str]],
    primary_keys: Mapping[str, str] | None = None,
    guards: list[CaseSensitiveEquality | UniqueRowPerGroup] | None = None,
) -> str:
    """Inline CTEs, qualify columns, turn primary-key semijoins into joins, merge subqueries.

    `tables` maps table -> column -> type; `primary_keys` maps table -> its
    single primary-key column. With `guards`, a case-sensitive equality on a
    table column becomes a plain one, and a latest-row-per-group window becomes
    two aggregations; each appends its precondition there, and the caller
    must check it before running the query (`case_sensitive_equalities`,
    `mbql_core.rewrite_window`).
    """
    try:
        tree = date_inside_min_max(inline_ctes(parse_one(sql, read=dialect)))
        tree = qualify(
            tree,
            schema={name: dict(columns) for name, columns in tables.items()},
            dialect=dialect,
            quote_identifiers=False,
        )
        if guards is not None:
            tree = case_sensitive_equalities(tree, guards)
            tree = latest_per_group(tree, guards.append, dialect)
        if primary_keys:
            tree = semijoins_to_joins(tree, primary_keys, derivadas=False)
        tree = _sem_alias_fora_da_projecao(merge_subqueries(tree))
        # A semijunção derivada vem depois da fusão: o merge reescreve o GROUP BY
        # que ela cria com o alias da projeção, o que não é SQL válido.
        # Uma subconsulta trazida para a junção pode ter seus próprios IN: repete
        # até a consulta parar de mudar (cada passada remove ao menos um IN).
        for _ in range(_PASSADAS):
            antes = tree.sql(dialect=dialect)
            tree = semijoins_to_joins(tree, primary_keys or {}, derivadas=True)
            if tree.sql(dialect=dialect) == antes:
                break
        return tree.sql(dialect=dialect)
    except (ParseError, OptimizeError, ValueError, KeyError) as exc:
        raise ConversionError(motivo=f"Falha ao reescrever a consulta: {exc}") from exc


@dataclass(frozen=True)
class CaseSensitiveEquality:
    """`CAST(table.column AS BINARY) = value`, rewritten as `table.column = value`.

    Byte-equal strings are equal under any collation, so the plain equality
    keeps every row the binary one keeps. It keeps no other row exactly when
    every value of the column equal to `value` under the collation is `value`
    itself: that is the precondition to check against the data.
    """

    table: str
    column: str
    value: str


_TIPOS_BINARIOS = (exp.DataType.Type.BINARY, exp.DataType.Type.VARBINARY, exp.DataType.Type.BLOB)


def case_sensitive_equalities(
    tree: exp.Expression, guards: list[CaseSensitiveEquality | UniqueRowPerGroup]
) -> exp.Expression:
    """Turn `CAST(t.c AS BINARY) = 'v'` into `t.c = 'v'` and record its precondition.

    Only when `t` names a table (not a subquery) in an enclosing scope and the
    other side is a string literal; anything else keeps the cast.
    """
    for igualdade in list(tree.find_all(exp.EQ)):
        lados = (igualdade.this, igualdade.expression)
        for cast, literal in (lados, lados[::-1]):
            if not (
                isinstance(cast, exp.Cast)
                and cast.to.is_type(*_TIPOS_BINARIOS)
                and isinstance(cast.this, exp.Column)
                and isinstance(literal, exp.Literal)
                and literal.is_string
            ):
                continue
            tabela = _tabela_do_alias(igualdade, cast.this.table)
            if tabela is None:
                continue
            guards.append(CaseSensitiveEquality(tabela, cast.this.name, literal.this))
            cast.replace(cast.this.copy())
            break
    return tree


def _tabela_do_alias(no: exp.Expression, alias: str) -> str | None:
    """The table an alias names in the scopes enclosing a node, or None."""
    escopo = no.parent_select
    while escopo is not None:
        fontes = [escopo.args.get("from_")] + list(escopo.args.get("joins") or [])
        for fonte in fontes:
            origem = fonte.this if fonte is not None else None
            if origem is not None and origem.alias_or_name == alias:
                return origem.name if isinstance(origem, exp.Table) else None
        escopo = escopo.parent_select if escopo.parent is not None else None
    return None


def date_inside_min_max(tree: exp.Expression) -> exp.Expression:
    """`CAST(MIN(x) AS DATE)` -> `MIN(CAST(x AS DATE))`, and the same for MAX.

    The cast from datetime to date never reverses the order of two values, so
    the date of the smallest value is the smallest date; MIN and MAX skip
    NULL either way.
    """
    for cast in list(tree.find_all(exp.Cast)):
        agregada = cast.this
        if isinstance(agregada, (exp.Min, exp.Max)) and cast.to.is_type(exp.DataType.Type.DATE):
            if len(agregada.expressions) == 0:
                interna = exp.Cast(this=agregada.this.copy(), to=cast.to.copy())
                cast.replace(type(agregada)(this=interna))
    return tree


def _sem_alias_fora_da_projecao(tree: exp.Expression) -> exp.Expression:
    """Drop the aliases `merge_subqueries` leaves outside a projection list.

    SQLGlot replaces a column by the merged projection, alias included, also
    inside GROUP BY, ON or WHERE (`GROUP BY t.a AS b`), which is not valid
    SQL; the expression itself is the same.
    """
    for alias in list(tree.find_all(exp.Alias)):
        pai = alias.parent
        if not (isinstance(pai, exp.Select) and alias.arg_key == "expressions"):
            alias.replace(alias.this)
    return tree


def inline_ctes(tree: exp.Expression) -> exp.Expression:
    """Replace each reference to a non-recursive CTE by a copy of its definition.

    A non-recursive CTE without volatile functions is a named subquery, so
    reading it twice is reading the same rows twice. A recursive CTE, or one
    that calls a volatile function, keeps the query as it is.
    """
    with_ = tree.args.get("with_")
    if not isinstance(with_, exp.With) or with_.args.get("recursive"):
        return tree
    if any(cte.this.find(*_VOLATEIS) for cte in with_.expressions):
        return tree
    definicoes: dict[str, exp.Expression] = {}
    for cte in with_.expressions:
        corpo = cte.this.copy()
        _substituir_referencias(corpo, definicoes)
        definicoes[cte.alias] = corpo
    tree.set("with_", None)
    _substituir_referencias(tree, definicoes)
    return tree


def _substituir_referencias(arvore: exp.Expression, definicoes: Mapping[str, exp.Expression]) -> None:
    for tabela in list(arvore.find_all(exp.Table)):
        if tabela.name in definicoes and not tabela.db and not tabela.catalog:
            tabela.replace(
                exp.Subquery(
                    this=definicoes[tabela.name].copy(),
                    alias=exp.TableAlias(this=exp.to_identifier(tabela.alias_or_name)),
                )
            )


def semijoins_to_joins(
    tree: exp.Expression, primary_keys: Mapping[str, str], *, derivadas: bool = True
) -> exp.Expression:
    """`WHERE x IN (SELECT pk FROM t WHERE p) AND q` -> `JOIN t ON x = t.pk AND p WHERE q`.

    Exact when the subquery reads one table and projects its primary key, with
    no grouping, distinct, ordering or limit: the key is unique and not null,
    so the join neither repeats nor drops a row the IN would keep, and a NULL
    `x` is dropped by both. Any other uncorrelated one-column subquery becomes
    `JOIN (SELECT t.k FROM ... GROUP BY t.k) ON x = k`: the grouping keeps the
    join from repeating rows, and a NULL on either side matches nothing, which WHERE
    also drops. Only a top-level conjunct of WHERE is rewritten; an IN under
    OR or NOT stays as it is.
    """
    contador = 0
    for select in list(tree.find_all(exp.Select)):
        where = select.args.get("where")
        if where is None:
            continue
        conjuncts = list(where.this.flatten()) if isinstance(where.this, exp.And) else [where.this]
        restantes: list[exp.Expression] = []
        for conjunct in conjuncts:
            alvo = _semijoin_por_pk(conjunct, primary_keys)
            if alvo is None:
                derivada = _semijoin_derivado(conjunct) if derivadas else None
                if derivada is None:
                    restantes.append(conjunct)
                    continue
                contador += 1
                interna, coluna_saida = derivada
                novo_alias = f"semi_{contador}"
                select.append(
                    "joins",
                    exp.Join(
                        this=exp.Subquery(this=interna, alias=exp.TableAlias(this=exp.to_identifier(novo_alias))),
                        kind="INNER",
                        on=exp.EQ(
                            this=conjunct.this.copy(),
                            expression=exp.column(coluna_saida, table=novo_alias),
                        ),
                    ),
                )
                continue
            tabela, chave, filtro, alias_interno = alvo
            contador += 1
            novo_alias = f"semi_{tabela.name}_{contador}"
            condicao: exp.Expression = exp.EQ(this=conjunct.this.copy(), expression=exp.column(chave, table=novo_alias))
            if filtro is not None:
                filtro = filtro.copy()
                for coluna in filtro.find_all(exp.Column):
                    if coluna.table == alias_interno:
                        coluna.set("table", exp.to_identifier(novo_alias))
                condicao = exp.and_(condicao, filtro)
            select.append(
                "joins",
                exp.Join(
                    this=exp.Table(
                        this=exp.to_identifier(tabela.name),
                        alias=exp.TableAlias(this=exp.to_identifier(novo_alias)),
                    ),
                    kind="INNER",
                    on=condicao,
                ),
            )
        if len(restantes) != len(conjuncts):
            select.set("where", exp.Where(this=exp.and_(*restantes)) if restantes else None)
        if derivadas:
            contador = _semijoins_aninhados(select, contador)
    return tree


def _semijoins_aninhados(select: exp.Select, contador: int) -> int:
    """An IN nested under AND/OR only: `LEFT JOIN (S grouped by k) s ON x = s.k`, `s.k IS NOT NULL`.

    With no NOT between the IN and WHERE, a NULL and a false both drop the
    row in the end, so `x IN (S)` and `s.k IS NOT NULL` filter alike; the
    grouped subquery has each key once, so the LEFT JOIN repeats no row.
    """
    where = select.args.get("where")
    if where is None:
        return contador
    for no in list(where.find_all(exp.In)):
        if no.parent_select is not select or not _contexto_positivo(no, where):
            continue
        derivada = _semijoin_derivado(no)
        if derivada is None:
            continue
        contador += 1
        interna, coluna_saida = derivada
        novo_alias = f"semi_{contador}"
        select.append(
            "joins",
            exp.Join(
                this=exp.Subquery(this=interna, alias=exp.TableAlias(this=exp.to_identifier(novo_alias))),
                side="LEFT",
                on=exp.EQ(this=no.this.copy(), expression=exp.column(coluna_saida, table=novo_alias)),
            ),
        )
        no.replace(exp.Not(this=exp.Is(this=exp.column(coluna_saida, table=novo_alias), expression=exp.Null())))
    return contador


def _contexto_positivo(no: exp.Expression, where: exp.Where) -> bool:
    """Whether only AND, OR and parentheses lie between a node and its WHERE."""
    pai = no.parent
    while pai is not None and pai is not where:
        if not isinstance(pai, (exp.And, exp.Or, exp.Paren)):
            return False
        pai = pai.parent
    return pai is where


_BLOQUEIAM_SEMIJOIN = ("joins", "group", "having", "limit", "offset", "distinct", "order", "with_")


def _semijoin_por_pk(
    conjunct: exp.Expression, primary_keys: Mapping[str, str]
) -> tuple[exp.Table, str, exp.Expression | None, str] | None:
    """The table, key, filter and inner alias of a primary-key IN, or None."""
    if not isinstance(conjunct, exp.In) or not isinstance(conjunct.this, exp.Column):
        return None
    consulta = conjunct.args.get("query")
    interna = consulta.this if isinstance(consulta, exp.Subquery) else consulta
    if not isinstance(interna, exp.Select) or any(interna.args.get(k) for k in _BLOQUEIAM_SEMIJOIN):
        return None
    origem = interna.args.get("from_")
    tabela = origem.this if origem is not None else None
    if not isinstance(tabela, exp.Table) or len(interna.expressions) != 1:
        return None
    projetada = interna.expressions[0]
    projetada = projetada.this if isinstance(projetada, exp.Alias) else projetada
    chave = primary_keys.get(tabela.name)
    if not isinstance(projetada, exp.Column) or chave is None or projetada.name != chave:
        return None
    where = interna.args.get("where")
    if where is not None and where.find(exp.Subquery, exp.Select):
        return None
    return tabela, chave, where.this if where is not None else None, tabela.alias_or_name


def _semijoin_derivado(conjunct: exp.Expression) -> tuple[exp.Select, str] | None:
    """`SELECT t.k FROM ... GROUP BY t.k` and the name of `k`, for an uncorrelated IN, or None."""
    if not isinstance(conjunct, exp.In) or not isinstance(conjunct.this, exp.Column):
        return None
    consulta = conjunct.args.get("query")
    interna = consulta.this if isinstance(consulta, exp.Subquery) else consulta
    if not isinstance(interna, exp.Select) or len(interna.expressions) != 1:
        return None
    if any(interna.args.get(chave) for chave in ("limit", "offset", "with_")):
        return None
    if isinstance(interna.expressions[0], exp.Star) or _correlacionada(interna):
        return None
    copia = interna.copy()
    projetada = copia.expressions[0]
    base = projetada.this if isinstance(projetada, exp.Alias) else projetada
    if not isinstance(base, exp.Column) or not base.name:
        return None
    if copia.args.get("group") or copia.args.get("having") or copia.args.get("distinct"):
        return None
    copia.set("expressions", [base])
    copia.set("group", exp.Group(expressions=[base.copy()]))
    copia.set("order", None)
    return copia, base.name


def _correlacionada(interna: exp.Select) -> bool:
    """Whether a column inside the subquery names a source defined outside it."""
    fontes = {tabela.alias_or_name for tabela in interna.find_all(exp.Table)}
    fontes |= {sub.alias_or_name for sub in interna.find_all(exp.Subquery) if sub.alias_or_name}
    return any(coluna.table and coluna.table not in fontes for coluna in interna.find_all(exp.Column))
