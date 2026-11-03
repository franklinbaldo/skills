# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Portable MBQL 5 to the id-based form `/api/dataset` runs, from `/api/database/<id>/metadata`.

The Agent API runs portable MBQL by name, but a Metabase may keep it off
("AI features are not enabled"). `/api/dataset` runs MBQL 5 from a
query-builder account, with numeric table and field ids: `CatalogoMbql`
reads the metadata JSON and `resolver_ids` rewrites the query.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mbql_core.base import ConversionError


@dataclass(frozen=True)
class _CampoRemoto:
    id: int
    name: str
    base_type: str
    semantic_type: str | None = None


@dataclass(frozen=True)
class _TabelaRemota:
    id: int
    name: str
    fields: list[_CampoRemoto]


class CatalogoMbql:
    """Tables and columns of one Metabase database: names, ids and base types."""

    def __init__(self, tabelas: list[_TabelaRemota]) -> None:
        por_nome: dict[str, list[_TabelaRemota]] = {}
        for tabela in tabelas:
            por_nome.setdefault(tabela.name, []).append(tabela)
        self._tabelas = por_nome
        self._campos = {campo.id: campo for tabela in tabelas for campo in tabela.fields}

    def _tabela(self, nome: str) -> _TabelaRemota:
        candidatas = self._tabelas.get(nome, [])
        if not candidatas:
            raise ConversionError(motivo=f"tabela {nome} não existe nos metadados do Metabase")
        if len(candidatas) > 1:
            raise ConversionError(motivo=f"tabela {nome} é ambígua entre esquemas do Metabase")
        return candidatas[0]

    def tabela(self, nome: str) -> int:
        """The table id; an unknown or ambiguous name has no representation."""
        return self._tabela(nome).id

    def colunas(self, nome: str) -> dict[str, str]:
        """Column name -> base type of one table, as Metabase knows it."""
        return {campo.name: campo.base_type for campo in self._tabela(nome).fields}

    def campo(self, tabela: str, coluna: str) -> int:
        """The field id of one column; an unknown column has no representation."""
        for campo in self._tabela(tabela).fields:
            if campo.name == coluna:
                return campo.id
        raise ConversionError(motivo=f"coluna {tabela}.{coluna} não existe nos metadados do Metabase")

    def esquema(self) -> dict[str, dict[str, str]]:
        """Tables with a unique name and their columns, for flattening subqueries."""
        return {
            nome: {campo.name: "TEXT" for campo in tabelas[0].fields}
            for nome, tabelas in self._tabelas.items()
            if len(tabelas) == 1
        }

    def chaves_primarias(self) -> dict[str, str]:
        """Table -> its primary-key column, for tables with a unique name and one key."""
        chaves: dict[str, str] = {}
        for nome, tabelas in self._tabelas.items():
            pks = [campo.name for campo in tabelas[0].fields if campo.semantic_type == "type/PK"]
            if len(tabelas) == 1 and len(pks) == 1:
                chaves[nome] = pks[0]
        return chaves

    def do_id(self, campo_id: int) -> tuple[str, str]:
        """Name and base type of a field already resolved to its id."""
        campo = self._campos[campo_id]
        return campo.name, campo.base_type


def _ref_portavel(valor: Any, tamanho: int) -> bool:
    return (
        isinstance(valor, list)
        and len(valor) == tamanho
        and all(isinstance(parte, str) or parte is None for parte in valor)
    )


def _clausula(valor: Any) -> bool:
    return isinstance(valor, list) and len(valor) >= 2 and isinstance(valor[1], dict)


# Agregações cujo resultado é sempre uma contagem inteira.
_CONTAGENS = frozenset({"count", "distinct"})


_TIPOS_INTEIROS = frozenset({"type/Integer", "type/BigInteger"})


_FUNCOES_DE_TEXTO = frozenset({"text", "substring", "concat", "lower", "upper", "trim", "ltrim", "rtrim", "replace"})


# Nome da coluna de cada agregação no Metabase (metabase.lib.aggregation,
# column-name-method); repetido na etapa, ganha _2, _3...
_NOME_DA_AGREGACAO = {
    "distinct": "count",
    "cum-count": "count",
    "cum-sum": "sum",
    "count-where": "count_where",
}


Colunas = dict[str, str | None]


class _Contexto:
    """Columns a ref by bare name can reach inside one stage."""

    def __init__(self, fonte: Colunas, juncoes: dict[str, Colunas]) -> None:
        self.fonte = fonte
        self.juncoes = juncoes
        self.expressoes: Colunas = {}

    def tipo(self, nome: str, juncao: Any) -> str:
        colunas = self.juncoes.get(juncao, {}) if isinstance(juncao, str) else self.fonte
        tipo = colunas.get(nome)
        if tipo is None:
            raise ConversionError(motivo=f"a coluna {nome} vem de uma etapa anterior com tipo desconhecido")
        return tipo


class _Resolvedor:
    """Rewrite one portable MBQL 5 query into the id-based form `/api/dataset` runs.

    Stages are walked in order. Each one resolves `[db, schema, table(, column)]`
    refs to ids, lists its expressions (named in their options) and records the
    columns it hands to the next stage. A later-stage ref by bare name gets the
    base type of that column; a column whose type is unknown refuses the query.
    """

    def __init__(self, catalogo: CatalogoMbql, database: str) -> None:
        self._catalogo = catalogo
        self._database = database

    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        estagios, _ = self._estagios(query.get("stages", []))
        return {**query, "stages": estagios}

    def _estagios(self, estagios: list[Any]) -> tuple[list[Any], Colunas]:
        saida: list[Any] = []
        anteriores: Colunas = {}
        for estagio in estagios:
            if not isinstance(estagio, dict):
                raise ConversionError(motivo="uma etapa ou junção da consulta MBQL não tem a forma esperada")
            resolvido, anteriores = self._estagio(estagio, anteriores)
            saida.append(resolvido)
        return saida, anteriores

    def _estagio(self, estagio: dict[str, Any], anteriores: Colunas) -> tuple[dict[str, Any], Colunas]:
        fonte: Colunas = dict(anteriores)
        saida: dict[str, Any] = {}
        tabela = estagio.get("source-table")
        if isinstance(tabela, list) and _ref_portavel(tabela, 3):
            self._conferir_banco(tabela[0])
            saida["source-table"] = self._catalogo.tabela(tabela[2])
            fonte = dict(self._catalogo.colunas(tabela[2]))
        juncoes: dict[str, Colunas] = {}
        if "joins" in estagio:
            saida["joins"] = [self._juncao(juncao, juncoes) for juncao in estagio["joins"]]
        contexto = _Contexto(fonte, juncoes)
        if "joins" in saida:
            saida["joins"] = [
                {**juncao, "conditions": self._valor(juncao["conditions"], contexto)} for juncao in saida["joins"]
            ]
        expressoes: Colunas = {}
        if isinstance(estagio.get("expressions"), dict):
            lista = []
            for nome, clausula in estagio["expressions"].items():
                resolvida = self._valor(clausula, contexto)
                if not _clausula(resolvida):
                    raise ConversionError(
                        motivo=f"a expressão {nome} não tem a forma [operador, opções, ...] do MBQL 5"
                    )
                opcoes = {**resolvida[1], "lib/expression-name": nome}
                lista.append([resolvida[0], opcoes, *resolvida[2:]])
                expressoes[nome] = self._tipo(resolvida, expressoes)
                contexto.expressoes[nome] = expressoes[nome]
            saida["expressions"] = lista
        for chave, valor in estagio.items():
            if chave not in saida and chave != "expressions":
                saida[chave] = self._valor(valor, contexto)
        return saida, self._colunas_de_saida(saida, fonte, expressoes)

    def _juncao(self, juncao: Any, juncoes: dict[str, Colunas]) -> dict[str, Any]:
        if not isinstance(juncao, dict):
            raise ConversionError(motivo="uma etapa ou junção da consulta MBQL não tem a forma esperada")
        estagios, colunas = self._estagios(juncao.get("stages", []))
        alias = juncao.get("alias")
        if isinstance(alias, str):
            juncoes[alias] = colunas
        # As condições citam a junção e a fonte da etapa externa: são
        # resolvidas no contexto da etapa, depois de todas as junções.
        return {**juncao, "stages": estagios, "conditions": juncao.get("conditions", [])}

    def _valor(self, valor: Any, contexto: _Contexto) -> Any:
        if isinstance(valor, dict):
            return {chave: self._valor(item, contexto) for chave, item in valor.items()}
        if not isinstance(valor, list):
            return valor
        if len(valor) == 3 and valor[0] == "field" and isinstance(valor[1], dict):
            opcoes = self._valor(valor[1], contexto)
            ref = valor[2]
            if _ref_portavel(ref, 4):
                self._conferir_banco(ref[0])
                return ["field", opcoes, self._catalogo.campo(ref[2], ref[3])]
            if isinstance(ref, str):
                tipo = contexto.tipo(ref, opcoes.get("join-alias"))
                return ["field", {"base-type": tipo, **opcoes}, ref]
        return [self._valor(item, contexto) for item in valor]

    def _tipo(self, clausula: list[Any], expressoes: Colunas) -> str | None:
        """Base type of an expression: only a plain column ref has a known one."""
        if clausula[0] == "field" and isinstance(clausula[2], int):
            return self._catalogo.do_id(clausula[2])[1]
        if clausula[0] == "field":
            tipo = clausula[1].get("base-type")
            return tipo if isinstance(tipo, str) else None
        if clausula[0] == "expression" and isinstance(clausula[2], str):
            return expressoes.get(clausula[2])
        if clausula[0] == "date":
            return "type/Date"
        if clausula[0] in _FUNCOES_DE_TEXTO:
            return "type/Text"
        if clausula[0] == "integer":
            # `integer` compila para CAST(... AS SIGNED), que no MySQL é BIGINT.
            return "type/BigInteger"
        if clausula[0] == "coalesce":
            return self._tipo_do_coalesce(clausula[2:], expressoes)
        return None

    def _tipo_do_coalesce(self, argumentos: list[Any], expressoes: Colunas) -> str | None:
        """One type for every non-literal argument, and literals that fit it; else unknown."""
        tipos = {self._tipo(arg, expressoes) for arg in argumentos if _clausula(arg)}
        if len(tipos) != 1 or None in tipos:
            return None
        tipo = tipos.pop()
        literais = [arg for arg in argumentos if not _clausula(arg)]
        if tipo in _TIPOS_INTEIROS and all(type(arg) is int for arg in literais):
            return tipo
        if tipo == "type/Text" and all(isinstance(arg, str) for arg in literais):
            return tipo
        return None

    def _colunas_de_saida(self, estagio: dict[str, Any], fonte: Colunas, expressoes: Colunas) -> Colunas:
        if "aggregation" in estagio or "breakout" in estagio:
            colunas = dict(self._nome_e_tipo(ref, expressoes) for ref in estagio.get("breakout", []))
            return {**colunas, **self._agregacoes(estagio.get("aggregation", []), expressoes)}
        if "fields" in estagio:
            return dict(self._nome_e_tipo(ref, expressoes) for ref in estagio["fields"])
        return {**fonte, **expressoes}

    def _agregacoes(self, agregacoes: list[Any], expressoes: Colunas) -> Colunas:
        """Metabase's names for a stage's aggregations (`count`, `count_2`, ...) and types.

        Only a type fixed by the operation is known: a count is an integer, and
        min/max have the type of the column they read. Any other aggregation is
        `None`, so a later stage that cites it refuses the query.
        """
        colunas: Colunas = {}
        vistos: dict[str, int] = {}
        for clausula in agregacoes:
            if not _clausula(clausula):
                raise ConversionError(motivo="uma coluna de saída da consulta MBQL não tem a forma esperada")
            operador = clausula[0]
            base = _NOME_DA_AGREGACAO.get(operador, operador)
            vistos[base] = vistos.get(base, 0) + 1
            nome = base if vistos[base] == 1 else f"{base}_{vistos[base]}"
            if isinstance(clausula[1].get("name"), str):
                nome = clausula[1]["name"]
            tipo: str | None = None
            if operador in _CONTAGENS:
                tipo = "type/BigInteger"
            elif operador in ("min", "max") and len(clausula) == 3 and _clausula(clausula[2]):
                tipo = self._tipo(clausula[2], expressoes)
            colunas[nome] = tipo
        return colunas

    def _nome_e_tipo(self, ref: Any, expressoes: Colunas) -> tuple[str, str | None]:
        if _clausula(ref) and ref[0] == "field" and isinstance(ref[2], int):
            return self._catalogo.do_id(ref[2])
        if _clausula(ref) and ref[0] == "field" and isinstance(ref[2], str):
            tipo = ref[1].get("base-type")
            return ref[2], tipo if isinstance(tipo, str) else None
        if _clausula(ref) and ref[0] == "expression" and isinstance(ref[2], str):
            return ref[2], expressoes.get(ref[2])
        raise ConversionError(motivo="uma coluna de saída da consulta MBQL não tem a forma esperada")

    def _conferir_banco(self, nome: str | None) -> None:
        if nome != self._database:
            raise ConversionError(motivo=f"a consulta referencia o banco {nome}, não {self._database}")


def resolver_ids(query: dict[str, Any], catalogo: CatalogoMbql, *, database: str) -> dict[str, Any]:
    """The id-based MBQL 5 query `/api/dataset` runs, from the converter's portable one."""
    return _Resolvedor(catalogo, database).query(query)


def catalogo_de_metadados(metadados: dict[str, Any]) -> CatalogoMbql:
    """The catalog of one `/api/database/<id>/metadata?include_hidden=true` response."""
    try:
        tabelas = [
            _TabelaRemota(
                id=int(tabela["id"]),
                name=str(tabela["name"]),
                fields=[
                    _CampoRemoto(
                        id=int(campo["id"]),
                        name=str(campo["name"]),
                        base_type=str(campo["base_type"]),
                        semantic_type=campo.get("semantic_type"),
                    )
                    for campo in tabela["fields"]
                ],
            )
            for tabela in metadados["tables"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ConversionError(motivo=f"metadados do Metabase em formato inesperado: {exc}") from exc
    return CatalogoMbql(tabelas)
