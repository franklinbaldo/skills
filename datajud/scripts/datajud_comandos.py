# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.6",
# ]
# ///
"""Comandos de busca agregada: `buscar`, `contar`, `facetas` e `codigos`."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import datajud_api as api
from datajud_cnj import cnj
from datajud_formatos import CAPA_FIELDS, assuntos_str, classe_str, fmt_data_ajuiz, grau_label, montar_query, orgao_str
from datajud_modelos import RequisicaoBusca
from datajud_saidas import (
    CodigoEncontrado,
    Faceta,
    ItemBusca,
    SaidaBusca,
    SaidaCodigos,
    SaidaContagem,
    SaidaFacetas,
    _imprimir,
)

if TYPE_CHECKING:
    from datajud import Filtros


def cmd_buscar(filtros: "Filtros", recentes: bool, tamanho: int, as_json: bool):
    body = RequisicaoBusca(
        size=tamanho, track_total_hits=True, query=montar_query(filtros), source=CAPA_FIELDS,
        sort=[{"dataAjuizamento": "desc"}] if recentes else None,
    ).model_dump(by_alias=True, exclude_none=True)

    d = api.search(body, tribunal=filtros.tribunal)
    total = d.get("hits", {}).get("total", {}).get("value", 0)
    hits = d.get("hits", {}).get("hits", [])

    if as_json:
        resultados = [
            ItemBusca.model_validate({
                "numeroProcesso": cnj(src.get("numeroProcesso", "")),
                "grau": src.get("grau"),
                "classe": src.get("classe"),
                "assuntos": src.get("assuntos"),
                "orgaoJulgador": (src.get("orgaoJulgador") or {}).get("nome"),
                "dataAjuizamento": src.get("dataAjuizamento"),
            })
            for src in (h["_source"] for h in hits)
        ]
        _imprimir(SaidaBusca(tribunal=filtros.tribunal.upper(), total=total,
                             retornados=len(resultados), resultados=resultados))
        return 0

    print(f"{total} processo(s) no acervo de {filtros.tribunal.upper()} para o filtro "
          f"| exibindo {len(hits)}")
    print("=" * 92)
    for i, h in enumerate(hits, 1):
        src = h["_source"]
        print(f"\n[{i}] {cnj(src.get('numeroProcesso',''))} | {grau_label(src.get('grau'))} "
              f"| {classe_str(src)}")
        print(f"    assuntos: {assuntos_str(src)}")
        print(f"    orgao:    {orgao_str(src)} | ajuizado: "
              f"{fmt_data_ajuiz(src.get('dataAjuizamento'))}")
    if not hits:
        print("\n(nenhum resultado)")
    return 0


# ----------------------------------------------------------------------------
# Modo: contar
# ----------------------------------------------------------------------------
def cmd_contar(filtros: "Filtros", as_json: bool):
    body = RequisicaoBusca(size=0, track_total_hits=True, query=montar_query(filtros)).bruto()
    d = api.search(body, tribunal=filtros.tribunal)
    total = d.get("hits", {}).get("total", {}).get("value", 0)
    if as_json:
        _imprimir(SaidaContagem(tribunal=filtros.tribunal.upper(), total=total))
    else:
        print(f"{total} processo(s) em {filtros.tribunal.upper()} para o filtro.")
    return 0


# ----------------------------------------------------------------------------
# Modo: facetas
# ----------------------------------------------------------------------------
FACET_FIELD = {
    "classe": "classe.nome.keyword",
    "assunto": "assuntos.nome.keyword",
    "orgao": "orgaoJulgador.nome.keyword",
    "grau": "grau.keyword",
    "sistema": "sistema.nome.keyword",
}


def cmd_facetas(filtros: "Filtros", por: str, limite: int, as_json: bool):
    campo = FACET_FIELD[por]
    body = RequisicaoBusca(
        size=0, track_total_hits=True, query=montar_query(filtros),
        aggs={"f": {"terms": {"field": campo, "size": limite}}},
    ).bruto()
    d = api.search(body, tribunal=filtros.tribunal)
    total = d.get("hits", {}).get("total", {}).get("value", 0)
    buckets = d.get("aggregations", {}).get("f", {}).get("buckets", [])
    if as_json:
        _imprimir(SaidaFacetas(
            tribunal=filtros.tribunal.upper(), total=total, por=por,
            buckets=[Faceta(chave=b["key"], qtd=b["doc_count"]) for b in buckets],
        ))
        return 0
    print(f"Panorama por {por} — {filtros.tribunal.upper()} "
          f"(total no filtro: {total})")
    print("=" * 92)
    for b in buckets:
        print(f"  {b['doc_count']:>9}  {b['key']}")
    return 0


# ----------------------------------------------------------------------------
# Modo: codigos (descobre codigo de classe/assunto pelo nome, via agregacao)
# ----------------------------------------------------------------------------
def cmd_codigos(termo: str, por: str, tribunal: str, limite: int, as_json: bool):
    if por == "classe":
        campo_cod, campo_nome = "classe.codigo", "classe.nome.keyword"
        match_field = "classe.nome"
    else:
        campo_cod, campo_nome = "assuntos.codigo", "assuntos.nome.keyword"
        match_field = "assuntos.nome"
    body = RequisicaoBusca(
        size=0,
        query={"match": {match_field: termo}},
        aggs={
            "nomes": {
                "terms": {"field": campo_nome, "size": limite},
                "aggs": {"cod": {"terms": {"field": campo_cod, "size": 1}}},
            }
        },
    ).bruto()
    d = api.search(body, tribunal=tribunal)
    buckets = d.get("aggregations", {}).get("nomes", {}).get("buckets", [])
    # a agregacao lista TODOS os nomes dos processos que casaram (em assunto, um
    # processo tem varios); filtramos para os nomes que de fato contem o termo.
    termos = [t for t in re.split(r"\s+", termo.lower()) if t]
    linhas = []
    for b in buckets:
        nome_l = b["key"].lower()
        if termos and not all(t in nome_l for t in termos):
            continue
        cods = b.get("cod", {}).get("buckets", [])
        cod = cods[0]["key"] if cods else "?"
        linhas.append((cod, b["key"], b["doc_count"]))
    linhas.sort(key=lambda x: -x[2])
    if as_json:
        _imprimir(SaidaCodigos(por=por, termo=termo, itens=[
            CodigoEncontrado(codigo=c, nome=n, qtd=q) for c, n, q in linhas
        ]))
        return 0
    print(f"Codigos de {por} contendo \"{termo}\" em {tribunal.upper()}")
    print("=" * 92)
    for c, n, q in linhas:
        print(f"  codigo {str(c):>6}  {n}   (~{q} processos)")
    if not linhas:
        print("  (nada encontrado)")
    return 0


# ----------------------------------------------------------------------------
# Modo: lote (muitos processos, resposta crua guardada em disco)
# ----------------------------------------------------------------------------
# A API leva dezenas de segundos por requisicao com 1 ou com 100 processos
# (medido em 2026-10-19: ~40 s); um por um, um acervo de 3.448 processos
# levaria horas. Uma consulta `terms` por tribunal, em lotes, levou ~6 min.
