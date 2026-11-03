# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Latest-row-per-group windows rewritten as aggregations, under a checked precondition.

`ROW_NUMBER() OVER (PARTITION BY p ORDER BY a DESC, k DESC)`, kept only at
position one, picks per group the row with the largest `a` and, among those,
the largest `k`; MySQL puts NULL last in a descending sort, so a group whose
`a` is all NULL keeps its largest `k`. Two aggregations say the same: the
largest `a` per group, then the largest `k` among the rows that have it (or
among all rows, when the group has no `a`). Joining back by `(p, k)` keeps
exactly that row when `k` is unique and not null and `p` is not null in the
source: the precondition the caller checks (`UniqueRowPerGroup`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlglot import exp


@dataclass(frozen=True)
class UniqueRowPerGroup:
    """In `source` (SQL), `key` is unique and not null and `group` is not null."""

    source: str
    group: str
    key: str


def latest_per_group(tree: exp.Expression, record: Callable[[UniqueRowPerGroup], None], dialect: str) -> exp.Expression:
    """Rewrite each latest-row-per-group window that has the exact supported shape."""
    for janela in list(tree.find_all(exp.Window)):
        alvo = _forma_suportada(janela)
        if alvo is None:
            continue
        consumidor, interna, posicao, primeira, p, a, k = alvo
        sem_janela = interna.copy()
        sem_janela.set(
            "expressions",
            [e for e in sem_janela.expressions if e.alias_or_name != posicao],
        )
        fonte = sem_janela.sql(dialect=dialect)
        record(UniqueRowPerGroup(fonte, p, k))
        alias = consumidor.args["from_"].this.alias_or_name
        escolha = _escolha(sem_janela, p, a, k)
        consumidor.args["from_"].this.replace(
            exp.Subquery(this=sem_janela, alias=exp.TableAlias(this=exp.to_identifier(alias)))
        )
        consumidor.append(
            "joins",
            exp.Join(
                this=exp.Subquery(this=escolha, alias=exp.TableAlias(this=exp.to_identifier("escolha"))),
                kind="INNER",
                on=exp.and_(
                    exp.EQ(this=exp.column(p, table=alias), expression=exp.column(p, table="escolha")),
                    exp.EQ(
                        this=exp.column(k, table=alias),
                        expression=exp.column("k_escolhido", table="escolha"),
                    ),
                ),
            ),
        )
        consumidor.set("where", None)
        for projecao in consumidor.expressions:
            coluna = projecao.this if isinstance(projecao, exp.Alias) else projecao
            if isinstance(coluna, exp.Column) and coluna.name == posicao:
                coluna.replace(exp.Literal.number(primeira))
    return tree


def _escolha(fonte: exp.Select, p: str, a: str, k: str) -> exp.Select:
    """`SELECT p, MAX(k) AS k_escolhido` over the rows with the group's largest `a`."""
    maximos = (
        exp.select(exp.column(p, table="w3"), exp.alias_(exp.Max(this=exp.column(a, table="w3")), "a_max"))
        .from_(exp.Subquery(this=fonte.copy(), alias=exp.TableAlias(this=exp.to_identifier("w3"))))
        .group_by(exp.column(p, table="w3"))
    )
    return (
        exp.select(
            exp.column(p, table="w2"),
            exp.alias_(exp.Max(this=exp.column(k, table="w2")), "k_escolhido"),
        )
        .from_(exp.Subquery(this=fonte.copy(), alias=exp.TableAlias(this=exp.to_identifier("w2"))))
        .join(
            exp.Subquery(this=maximos, alias=exp.TableAlias(this=exp.to_identifier("maximos"))),
            on=exp.EQ(this=exp.column(p, table="w2"), expression=exp.column(p, table="maximos")),
            join_type="LEFT",
        )
        .where(
            exp.or_(
                exp.EQ(this=exp.column(a, table="w2"), expression=exp.column("a_max", table="maximos")),
                exp.Is(this=exp.column("a_max", table="maximos"), expression=exp.Null()),
            )
        )
        .group_by(exp.column(p, table="w2"))
    )


def _forma_suportada(
    janela: exp.Window,
) -> tuple[exp.Select, exp.Select, str, int, str, str, str] | None:
    """The consumer, window query, position alias, first position and p, a, k; or None."""
    if not isinstance(janela.this, exp.RowNumber):
        return None
    no = janela.parent
    primeira = 1
    if isinstance(no, exp.Sub) and no.this is janela and _numero(no.expression) == 1:
        primeira, no = 0, no.parent
    if not isinstance(no, exp.Alias) or not isinstance(no.parent, exp.Select):
        return None
    posicao, interna = no.alias, no.parent
    particao = janela.args.get("partition_by") or []
    ordem = janela.args.get("order")
    criterios = ordem.expressions if ordem is not None else []
    if len(particao) != 1 or len(criterios) != 2 or not all(c.args.get("desc") for c in criterios):
        return None
    colunas = [particao[0], criterios[0].this, criterios[1].this]
    if not all(isinstance(c, exp.Column) for c in colunas):
        return None
    # WHERE e junções ficam em W': a janela numera as linhas que eles deixam.
    if any(interna.args.get(k) for k in ("group", "having", "limit", "offset", "distinct", "with_")):
        return None
    if sum(1 for e in interna.expressions if e.find(exp.Window)) != 1:
        return None
    nomes = _saidas(interna, colunas)
    if nomes is None:
        return None
    p, a, k = nomes
    sub = interna.parent
    consumidor = sub.parent_select if isinstance(sub, exp.Subquery) else None
    if consumidor is None or consumidor.args.get("from_") is None or consumidor.args["from_"].this is not sub:
        return None
    if any(consumidor.args.get(k) for k in ("joins", "group", "having", "with_")):
        return None
    filtro = consumidor.args.get("where")
    if filtro is None or not _filtra_primeira(filtro.this, posicao, primeira):
        return None
    return consumidor, interna, posicao, primeira, p, a, k


def _saidas(interna: exp.Select, colunas: list[exp.Column]) -> tuple[str, str, str] | None:
    """Output names under which the window query projects p, a and k as plain columns."""
    nomes: list[str] = []
    for coluna in colunas:
        achado = None
        for projecao in interna.expressions:
            base = projecao.this if isinstance(projecao, exp.Alias) else projecao
            if isinstance(base, exp.Column) and base.name == coluna.name and base.table == coluna.table:
                achado = projecao.alias_or_name
        if achado is None:
            return None
        nomes.append(achado)
    return nomes[0], nomes[1], nomes[2]


def _filtra_primeira(condicao: exp.Expression, posicao: str, primeira: int) -> bool:
    return (
        isinstance(condicao, exp.EQ)
        and isinstance(condicao.this, exp.Column)
        and condicao.this.name == posicao
        and _numero(condicao.expression) == primeira
    )


def _numero(no: exp.Expression) -> int | None:
    if isinstance(no, exp.Literal) and not no.is_string and no.this.isdigit():
        return int(no.this)
    return None
