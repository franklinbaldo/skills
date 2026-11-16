# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Projeção legível (modo `--formato texto`) dos resultados; o JSON é o próprio dicionário."""

from __future__ import annotations

from typing import Any

from legislacao_consultas import ROTULOS_VERBO

ROTULO_ESTAGIO = {
    "so-catalogada": "só catalogada (sem PDF preservado medido)",
    "preservada": "preservada (PDF no Internet Archive)",
    "legivel": "legível (OCR em `textos`)",
    "estruturada": "estruturada (`versoes`)",
    "nao-medido": "não medido",
}


def _avisos(dados: dict[str, Any]) -> list[str]:
    return [f"AVISO: {a}" for a in dados.get("avisos", [])]


def buscar(dados: dict[str, Any]) -> str:
    linhas = [f"{dados['total']} norma(s) no catálogo; exibindo {dados['retornados']} (modo: {dados['modo']})"]
    for i, r in enumerate(dados["resultados"], 1):
        linhas += [
            "",
            f"[{i}] {r['identificacao']}  ({r['citacao_curta']})",
            f"    situação no índice: {r['situacao_no_indice'] or 'n/d'} | estágio: {ROTULO_ESTAGIO[r['estagio']]}",
            f"    ementa: {r['ementa']}",
            f"    {r['link'] or '(sem link)'}",
            f"    norma_id: {r['norma_id']}",
        ]
    if dados.get("dica"):
        linhas += ["", f"({dados['dica']})"]
    return "\n".join([*linhas, "", *_avisos(dados)]).rstrip()


def _relacoes(grupos: dict[str, dict[str, list[dict[str, Any]]]]) -> list[str]:
    linhas: list[str] = []
    for lado, titulo, indice in (("saida", "Esta norma age sobre", 0), ("entrada", "Outras normas agem sobre esta", 1)):
        if not grupos[lado]:
            continue
        linhas += ["", f"{titulo}:"]
        for verbo, itens in grupos[lado].items():
            linhas.append(f"  {ROTULOS_VERBO[verbo][indice]} ({len(itens)}):")
            for it in itens:
                outra = it["outra_norma"]
                alvo = f"{outra['citacao_curta']} — {outra['identificacao']}" if outra else it["como_escrito"]
                marca = "" if it["resolvida"] else f"  [NÃO RESOLVIDA: {it['confianca']}; {it['nota'] or 's/ nota'}]"
                parcial = " (parcial)" if it["parcial"] else ""
                linhas.append(f"    - {alvo}{parcial}{marca}")
                linhas.append(f"      trecho ({it['fonte_relacao']}): {it['trecho']}")
                if outra and outra["link"]:
                    linhas.append(f"      {outra['link']}")
    return linhas


def norma(dados: dict[str, Any]) -> str:
    n, s, ln, c = dados["norma"], dados["situacao_no_indice"], dados["links"], dados["cobertura"]
    linhas = [
        f"{n['identificacao']}  ({n['citacao_curta']})",
        f"norma_id: {n['norma_id']}",
        f"ementa: {n['ementa']}",
        "",
        f"Situação no índice oficial: {s['valor'] or 'n/d'}  (evidências: {', '.join(s['evidencias']) or 'nenhuma'})",
        f"  {s['leitura']}",
        f"  {s['aviso']}",
        "",
        "Links:",
        f"  oficial: {ln['oficial'] or 'n/d'}",
        f"  Internet Archive: {ln['internet_archive'] or 'não preservada / não medido'}",
        *([f"  AVISO: {ln['aviso']}"] if ln.get("aviso") else []),
        f"Cobertura do Leizilla: {ROTULO_ESTAGIO[c['estagio']]}",
    ]
    if s.get("nota_relacoes"):
        linhas.append(f"  nota: {s['nota_relacoes']}")
    if dados["relacoes"] is None:
        linhas += ["", "Relações: NÃO CONSULTADAS (dataset indisponível; ver avisos)"]
    else:
        linhas += _relacoes(dados["relacoes"]) or ["", "Relações: nenhuma encontrada nas ementas"]
        linhas += ["", f"AVISO: {dados['relacoes']['aviso']}"]
    return "\n".join([*linhas, "", *_avisos(dados)]).rstrip()


def relacoes(dados: dict[str, Any]) -> str:
    n = dados["norma"]
    c = dados["contagem"]
    linhas = [
        f"{n['identificacao']}  ({n['citacao_curta']})",
        f"relações: {c['saida']} de saída, {c['entrada']} de entrada",
    ]
    linhas += _relacoes(dados["relacoes"])
    return "\n".join([*linhas, "", f"AVISO: {dados['aviso']}", *_avisos(dados)]).rstrip()


def texto(dados: dict[str, Any]) -> str:
    n = dados["norma"]
    linhas = [
        f"{n['identificacao']}  ({n['citacao_curta']})",
        f"FONTE DO TEXTO: {dados['fonte']} — {dados['descricao_da_fonte']}",
    ]
    if dados.get("recorte"):
        linhas.append(f"recorte: {dados['recorte']}")
    p = dados.get("proveniencia")
    if p:
        linhas.append(f"PDF: {p['pdf_url']}  | OCR: {p['ocr_motor']} | capturado em {p['capturado_em']}")
    linhas.append(f"melhor link: {dados['links']['melhor'] or 'n/d'}")
    linhas += [f"AVISO: {a}" for a in dados["avisos"]]
    linhas.append("")
    if dados["fonte"] == "versoes":
        for d in dados["dispositivos"]:
            marca = " [REVOGADO]" if d["revogado"] else ""
            linhas.append(f"[{d['path']}]{marca} {d['texto']}")
    else:
        linhas.append(dados["texto"] if dados["texto"] is not None else "(trecho indisponível; ver avisos)")
    return "\n".join(linhas).rstrip()
