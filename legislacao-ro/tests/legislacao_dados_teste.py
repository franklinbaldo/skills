# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1"]
# ///
"""Parquet minúsculos construídos em memória para os testes offline (nada binário é versionado)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from legislacao_citacao import normalizar_busca  # noqa: E402

CATALOGO_COLUNAS = {
    "norma_id": "VARCHAR", "ente": "VARCHAR", "fonte": "VARCHAR", "tipo": "VARCHAR", "numero": "INTEGER",
    "sufixo": "VARCHAR", "situacao": "VARCHAR", "titulo": "VARCHAR", "data": "VARCHAR", "ano": "INTEGER",
    "decada": "INTEGER", "ementa": "VARCHAR", "coddoc": "INTEGER", "entradas": "INTEGER", "arquivos": "VARCHAR",
    "arquivos_listados": "INTEGER", "arquivos_preservados": "INTEGER", "preservada": "BOOLEAN",
    "com_texto": "BOOLEAN", "legivel": "BOOLEAN", "estruturada": "BOOLEAN", "ia_item": "VARCHAR",
    "texto_id": "VARCHAR", "catalogo_obtido_em": "VARCHAR", "identidade_incerta": "BOOLEAN",
    "rendicoes": "VARCHAR", "situacao_norma": "VARCHAR", "situacao_evidencias": "VARCHAR", "busca": "VARCHAR",
    "url_oficial": "VARCHAR", "url_ia": "VARCHAR", "link_publico": "VARCHAR",
}  # fmt: skip
V02 = {
    "identidade_incerta",
    "rendicoes",
    "situacao_norma",
    "situacao_evidencias",
    "busca",
    "url_oficial",
    "url_ia",
    "link_publico",
}
RELACOES_COLUNAS = {
    "relacao_id": "VARCHAR", "origem_id": "VARCHAR", "verbo": "VARCHAR", "verbo_texto": "VARCHAR",
    "parcial": "BOOLEAN", "alvo_tipo": "VARCHAR", "alvo_categoria": "VARCHAR", "alvo_numero": "INTEGER",
    "alvo_sufixo": "VARCHAR", "alvo_data": "VARCHAR", "alvo_ano": "INTEGER", "alvo_texto": "VARCHAR",
    "alvo_id": "VARCHAR", "confianca": "VARCHAR", "nota": "VARCHAR", "trecho": "VARCHAR", "fonte_relacao": "VARCHAR",
}  # fmt: skip
TEXTOS_COLUNAS = {
    "texto_id": "VARCHAR", "tipo": "VARCHAR", "numero": "INTEGER", "rendicao": "VARCHAR", "pdf_url": "VARCHAR",
    "texto_url": "VARCHAR", "ocr_motor": "VARCHAR", "capturado_em": "VARCHAR", "sha256_fonte": "VARCHAR",
    "num_caracteres": "INTEGER", "artigos_fecham": "BOOLEAN", "artigos_total": "INTEGER",
    "artigos_ultimo": "INTEGER", "ancoras": "VARCHAR", "texto": "VARCHAR",
}  # fmt: skip
VERSOES_COLUNAS = {
    "lei_id": "VARCHAR", "dispositivo_path": "VARCHAR", "dispositivo_tipo": "VARCHAR", "dispositivo_ordem": "INTEGER",
    "dispositivo_parent_path": "VARCHAR", "dispositivo_revogado": "BOOLEAN", "em": "DATE", "ate": "DATE",
    "texto": "VARCHAR", "fontes": "VARCHAR", "quality": "VARCHAR",
}  # fmt: skip


def nid(tipo: str, numero: int, sufixo: str = "") -> str:
    return f"leizilla-raw-ro-casacivil-{tipo}-{numero:05d}{sufixo}"


def _gravar(destino: Path, colunas: dict[str, str], linhas: list[dict[str, Any]]) -> Path:
    con = duckdb.connect()
    ddl = ", ".join(f"{c} {t}" for c, t in colunas.items())
    con.execute(f"CREATE TABLE t ({ddl})")
    marcas = ", ".join("?" for _ in colunas)
    con.executemany(f"INSERT INTO t VALUES ({marcas})", [[linha.get(c) for c in colunas] for linha in linhas])
    con.execute(f"COPY t TO '{destino}' (FORMAT PARQUET)")
    con.close()
    return destino


def linha_catalogo(tipo: str, numero: int, data: str, ementa: str, sufixo: str = "", **extra: Any) -> dict[str, Any]:
    rotulo = {"lei": "Lei", "lc": "Lei Complementar", "decreto": "Decreto", "decreto-lei": "Decreto-Lei"}[tipo]
    titulo = f"{rotulo} n. {numero}{sufixo.upper()}, de {data[8:]}-{data[5:7]}-{data[:4]}"
    base = {
        "norma_id": nid(tipo, numero, sufixo), "ente": "ro", "fonte": "casacivil", "tipo": tipo, "numero": numero,
        "sufixo": sufixo, "situacao": "listada", "titulo": titulo, "data": data, "ano": int(data[:4]),
        "ementa": ementa, "arquivos": json.dumps([{"nome": "x.pdf", "url": f"https://oficial/{tipo}{numero}.pdf",
        "rendicao": "original"}]), "texto_id": nid(tipo, numero), "identidade_incerta": False,
        "rendicoes": "original", "situacao_norma": "sem-indicacao-de-revogacao", "situacao_evidencias": "",
        "url_oficial": f"https://oficial/{tipo}{numero}.pdf", "link_publico": f"https://oficial/{tipo}{numero}.pdf",
        "busca": normalizar_busca(f"{titulo} {ementa}"),
    }  # fmt: skip
    return base | extra


def catalogo_linhas() -> list[dict[str, Any]]:
    return [
        linha_catalogo(
            "lc", 68, "1992-12-09", "Dispõe sobre o Regime Jurídico dos Servidores Públicos.",
            situacao_norma="tem-compilada", situacao_evidencias="rendicao-compilada", rendicoes="compilada",
            preservada=True, legivel=True, estruturada=True,
            url_ia="https://ia/lc68.pdf", link_publico="https://ia/lc68.pdf",
        ),
        linha_catalogo("lc", 1, "1984-11-14", "Dispõe sobre o Estatuto antigo.", situacao_norma="revogada",
                       situacao_evidencias="anotacao-na-ementa"),
        linha_catalogo("lc", 100, "2001-03-05", "Altera a Lei Complementar nº 68, de 9 de dezembro de 1992 e a Resolução 5."),
        linha_catalogo("lc", 101, "2003-05-06", "Mantém o disposto na Lei Complementar n. 68 sobre educação."),
        linha_catalogo("lei", 1234, "2005-06-07", "Institui o Plano de Carreira dos profissionais da Educação.",
                       preservada=True, legivel=True, estruturada=False),
        linha_catalogo("lei", 80, "1990-01-02", "Cria o Parque Estadual."),
        linha_catalogo("decreto", 12345, "2010-08-09", "Regulamenta a Lei 1234 (plano de carreira).",
                       situacao_norma="revogada", situacao_evidencias="rendicao-revogado,anotacao-na-ementa"),
        linha_catalogo("decreto-lei", 9, "1982-01-01", "Dispõe sobre o nove."),
        linha_catalogo("decreto-lei", 9, "1982-02-02", "Dispõe sobre o nove A.", sufixo="a"),
        linha_catalogo("lei", 7000, "2021-01-01", "Orçamento — Crédito Suplementar para Saúde."),
    ]  # fmt: skip


def relacoes_linhas() -> list[dict[str, Any]]:
    def rel(rid: str, origem: str, verbo: str, alvo_id: str | None, texto: str, **kw: Any) -> dict[str, Any]:
        base = {
            "relacao_id": rid, "origem_id": origem, "verbo": verbo, "verbo_texto": verbo, "parcial": False,
            "alvo_texto": texto, "alvo_id": alvo_id, "confianca": "resolvida" if alvo_id else "nao-resolvida",
            "nota": None if alvo_id else "tipo-sem-indice", "trecho": f"{verbo} {texto}", "fonte_relacao": "ementa",
        }  # fmt: skip
        return base | kw

    return [
        rel("r1", nid("lc", 100), "altera", nid("lc", 68), "Lei Complementar nº 68, de 9 de dezembro de 1992"),
        rel("r2", nid("lc", 100), "altera", None, "Resolução 5"),
        rel("r3", nid("lc", 68), "revoga", nid("lc", 1), "Lei Complementar n. 1", fonte_relacao="anotacao-do-indice"),
        rel("r4", nid("decreto", 12345), "regulamenta", nid("lei", 1234), "Lei 1234", parcial=True),
    ]  # fmt: skip


def _ancoras(texto: str, n: int) -> str:
    achados = [
        {"n": k, "sufixo": None, "ini": texto.index(f"Art. {k}º"), "fim": texto.index(f"Art. {k}º") + 7}
        for k in range(1, n + 1)
    ]
    return json.dumps(achados)


TEXTO_FECHA = "DECRETA:\nArt. 1º Primeiro artigo.\nArt. 2º Segundo artigo.\nArt. 3º Terceiro.\nPalácio, 7 de junho."
TEXTO_ABERTO = "Texto ilegível Art. 1º e depois Art. 4º solto."


def textos_linhas() -> list[dict[str, Any]]:
    base = {"rendicao": "", "pdf_url": "https://ia/x.pdf", "texto_url": "https://ia/x_djvu.txt", "ocr_motor": "tesseract",
            "capturado_em": "2026-06-20", "sha256_fonte": "abc"}  # fmt: skip
    return [
        base | {"texto_id": nid("lei", 1234), "tipo": "lei", "numero": 1234, "num_caracteres": len(TEXTO_FECHA),
                "artigos_fecham": True, "artigos_total": 3, "artigos_ultimo": 3, "ancoras": _ancoras(TEXTO_FECHA, 3),
                "texto": TEXTO_FECHA},
        base | {"texto_id": nid("decreto", 12345), "tipo": "decreto", "numero": 12345,
                "num_caracteres": len(TEXTO_ABERTO), "artigos_fecham": False, "artigos_total": 0,
                "artigos_ultimo": 0, "ancoras": "[]", "texto": TEXTO_ABERTO},
        base | {"texto_id": nid("decreto-lei", 9), "tipo": "decreto-lei", "numero": 9, "num_caracteres": 5,
                "artigos_fecham": False, "artigos_total": 0, "artigos_ultimo": 0, "ancoras": "[]", "texto": "nove."},
    ]  # fmt: skip


def versoes_linhas() -> list[dict[str, Any]]:
    lei = "leizilla-ro-lei-complementar-00068-1992"
    fontes = json.dumps([{"ia_id": nid("lc", 68), "diverge": False}])

    def disp(path: str, tipo: str, ordem: int, pai: str | None, texto: str, **kw: Any) -> dict[str, Any]:
        base = {"lei_id": lei, "dispositivo_path": path, "dispositivo_tipo": tipo, "dispositivo_ordem": ordem,
                "dispositivo_parent_path": pai, "dispositivo_revogado": False, "em": "1992-12-09", "ate": None,
                "texto": texto, "fontes": fontes, "quality": None}  # fmt: skip
        return base | kw

    return [
        disp("ementa", "ementa", 0, None, "Dispõe sobre o Regime Jurídico."),
        disp("art-1", "artigo", 1, None, "Esta Lei estabelece o regime."),
        disp("art-5", "artigo", 2, None, "São direitos dos servidores:"),
        disp("art-5-inc-1", "inciso", 0, "art-5", "férias;"),
        disp("art-5-inc-2", "inciso", 1, "art-5", "licença;"),
        disp("art-5-par-1", "paragrafo", 2, "art-5", "Parágrafo primeiro."),
        disp("art-5-par-1-inc-1", "inciso", 0, "art-5-par-1", "item do parágrafo;"),
        disp("art-5-par-1", "paragrafo", 2, "art-5", "Parágrafo primeiro (antigo).", em="1990-01-01", ate="1992-12-08"),
        disp("art-6", "artigo", 3, None, "Outro artigo."),
    ]  # fmt: skip


def gravar_todos(pasta: Path, *, catalogo_v01: bool = False, sem: tuple[str, ...] = ()) -> Path:
    """Grava os quatro datasets em `pasta` (nomes `{nome}.parquet`); `sem` omite alguns."""
    pasta.mkdir(parents=True, exist_ok=True)
    colunas = {c: t for c, t in CATALOGO_COLUNAS.items() if not (catalogo_v01 and c in V02)}
    mapa = {
        "catalogo": (colunas, catalogo_linhas()),
        "relacoes": (RELACOES_COLUNAS, relacoes_linhas()),
        "textos": (TEXTOS_COLUNAS, textos_linhas()),
        "versoes": (VERSOES_COLUNAS, versoes_linhas()),
    }
    for nome, (cols, linhas) in mapa.items():
        if nome not in sem:
            _gravar(pasta / f"{nome}.parquet", cols, linhas)
    return pasta
