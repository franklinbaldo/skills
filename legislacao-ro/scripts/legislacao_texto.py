# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1"]
# ///
"""Texto de uma norma: estruturado (`versoes`) quando houver, senão OCR verbatim (`textos`)."""

from __future__ import annotations

import json
from typing import Any

from legislacao_citacao import parse_artigo
from legislacao_consultas import NaoEncontrado, UsoInvalido, aviso_rendicao, link_de, localizar, resumo_norma
from legislacao_dados import Acervo, DatasetIndisponivel

AVISO_VERSOES = (
    "texto estruturado por modelo a partir do OCR do PDF original: pode conter erros de reconhecimento e de "
    "estruturação; confira com o PDF antes de citar"
)
AVISO_TEXTOS = (
    "OCR bruto (verbatim) da publicação capturada, sem revisão: pode ter erros de reconhecimento; não é texto "
    "consolidado (não inclui alterações posteriores) e o PDF original prevalece"
)
AVISO_SUFIXO = (
    "a camada de texto é chaveada só por (tipo, número): como existem normas com o mesmo número e letras "
    "diferentes, este texto pode ser o de outra delas; confira com o PDF"
)
_FILHOS = ("par", "inc", "ali", "item")
_RANK_TIPO = {"ementa": 0, "preambulo": 1}


def _ordenar(itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordem de leitura: raízes por `ordem` global; filhos (via `parent`) por `ordem` dentro do pai, em profundidade."""
    por_path = {i["path"]: i for i in itens}
    filhos: dict[str, list[dict[str, Any]]] = {}
    raizes: list[dict[str, Any]] = []
    for item in itens:
        pai = item["parent"]
        if pai and pai in por_path and pai != item["path"]:
            filhos.setdefault(pai, []).append(item)
        else:
            raizes.append(item)

    def chave(i: dict[str, Any]) -> tuple[int, int, str]:
        return (i["ordem"], _RANK_TIPO.get(i["tipo"], 2), i["path"])

    saida: list[dict[str, Any]] = []
    pilha = sorted(raizes, key=chave, reverse=True)
    while pilha:
        atual = pilha.pop()
        saida.append(atual)
        pilha.extend(sorted(filhos.get(atual["path"], []), key=chave, reverse=True))
    return saida


def _subarvore(itens: list[dict[str, Any]], raiz: str) -> list[dict[str, Any]]:
    filhos: dict[str, list[str]] = {}
    for i in itens:
        if i["parent"]:
            filhos.setdefault(i["parent"], []).append(i["path"])
    alvo, pilha = {raiz}, [raiz]
    while pilha:
        for filho in filhos.get(pilha.pop(), []):
            if filho not in alvo:
                alvo.add(filho)
                pilha.append(filho)
    return [i for i in itens if i["path"] in alvo]


def _caminho_artigo(artigo: str) -> str:
    lido = parse_artigo(artigo)
    if lido is None:
        raise UsoInvalido(f"--artigo '{artigo}' não é um número de artigo (ex.: 5, 5-A)")
    numero, letra = lido
    return f"art-{numero}-{letra}" if letra else f"art-{numero}"


def _estruturado(acervo: Acervo, linha: dict[str, Any], artigo: str | None, dispositivo: str | None) -> dict | None:
    if not acervo.opcional("versoes"):
        return None
    leis = acervo.consulta(
        "SELECT DISTINCT lei_id FROM versoes WHERE fontes LIKE ? ORDER BY lei_id", [f'%"{linha["texto_id"]}"%']
    )
    if not leis:
        return None
    lei_id = leis[0]["lei_id"]
    linhas = acervo.consulta(
        "SELECT dispositivo_path AS path, dispositivo_tipo AS tipo, dispositivo_ordem AS ordem, "
        "dispositivo_parent_path AS parent, dispositivo_revogado AS revogado, em, texto, quality "
        "FROM (SELECT *, row_number() OVER (PARTITION BY dispositivo_path ORDER BY em DESC) AS rn "
        "FROM versoes WHERE lei_id = ?) WHERE rn = 1",
        [lei_id],
    )
    itens = _ordenar(linhas)
    alvo = _caminho_artigo(artigo) if artigo else dispositivo
    if alvo:
        if alvo not in {i["path"] for i in itens}:
            artigos = sorted(
                {
                    int(i["path"].split("-")[1])
                    for i in itens
                    if i["path"].startswith("art-") and i["path"].split("-")[1].isdigit()
                }
            )
            raise NaoEncontrado(
                f"dispositivo '{alvo}' não consta da versão estruturada (artigos presentes: "
                f"{', '.join(map(str, artigos)) or 'nenhum'}); tente --fonte textos",
                {"artigos_estruturados": artigos},
            )
        itens = _subarvore(itens, alvo)
    avisos = [AVISO_VERSOES]
    if leis[1:]:
        avisos.append(f"mais de uma lei estruturada para esta norma ({len(leis)}); usada: {lei_id}")
    return {
        "fonte": "versoes",
        "descricao_da_fonte": "texto estruturado (um registro por dispositivo, versão mais recente registrada)",
        "lei_id": lei_id,
        "recorte": alvo,
        "dispositivos": [
            {k: i[k] for k in ("path", "tipo", "texto", "revogado", "quality")} | {"em": str(i["em"])} for i in itens
        ],
        "avisos": avisos,
    }


def _fatia_artigo(linha: dict[str, Any], artigo: str) -> tuple[str | None, str | None, bool]:
    """(trecho, motivo da recusa, é o último artigo) pelas âncoras de artigo, só se a sequência fecha."""
    lido = parse_artigo(artigo)
    if lido is None:
        raise UsoInvalido(f"--artigo '{artigo}' não é um número de artigo (ex.: 5, 5-A)")
    if not linha["artigos_fecham"]:
        return None, "a sequência de artigos não fecha nesta norma: navegação por artigo não é confiável", False
    ancoras = sorted(json.loads(linha["ancoras"] or "[]"), key=lambda a: a["ini"])
    numero, letra = lido
    indices = [k for k, a in enumerate(ancoras) if a["n"] == numero and (a.get("sufixo") or "").lower() == letra]
    if len(indices) != 1:
        motivo = "âncora ambígua (marcador repetido)" if indices else f"art. {numero}{letra.upper()} sem âncora"
        return (
            None,
            f"{motivo}; a norma tem {linha['artigos_total']} artigos lidos (último: {linha['artigos_ultimo']})",
            False,
        )
    k = indices[0]
    ultimo = k + 1 >= len(ancoras)
    fim = len(linha["texto"]) if ultimo else ancoras[k + 1]["ini"]
    return linha["texto"][ancoras[k]["ini"] : fim].strip(), None, ultimo


def _so_textos(acervo: Acervo, linha: dict[str, Any], artigo: str | None, maximo: int) -> dict | None:
    if not acervo.opcional("textos"):
        return None
    achados = acervo.consulta("SELECT * FROM textos WHERE texto_id = ?", [linha["texto_id"]])
    if not achados:
        return None
    texto = achados[0]
    avisos = [AVISO_TEXTOS]
    if texto["rendicao"]:
        avisos.append(
            f"rendição capturada: '{texto['rendicao']}' (compilada = compilação da Casa Civil, não publicação)"
        )
    recorte, recusa = None, None
    conteudo = texto["texto"]
    if artigo:
        recorte = artigo
        conteudo, recusa, ultimo = _fatia_artigo(texto, artigo)
        if ultimo:
            avisos.append("último artigo: o trecho vai até o fim do texto e pode incluir fecho, data e assinaturas")
    elif maximo > 0 and len(conteudo) > maximo:
        conteudo = conteudo[:maximo]
        avisos.append(f"texto truncado em {maximo} caracteres de {texto['num_caracteres']}")
    return {
        "fonte": "textos",
        "descricao_da_fonte": "OCR verbatim do PDF preservado no Internet Archive",
        "texto_id": texto["texto_id"],
        "recorte": recorte,
        "texto": conteudo,
        "recusa": recusa,
        "proveniencia": {
            k: texto[k]
            for k in ("rendicao", "pdf_url", "texto_url", "ocr_motor", "capturado_em", "sha256_fonte", "num_caracteres")
        }
        | {k: texto[k] for k in ("artigos_fecham", "artigos_total", "artigos_ultimo")},
        "avisos": avisos,
    }


def texto(
    acervo: Acervo,
    referencia: str,
    *,
    artigo: str | None = None,
    dispositivo: str | None = None,
    fonte: str = "auto",
    maximo: int = 0,
) -> dict[str, Any]:
    if fonte not in ("auto", "versoes", "textos"):
        raise UsoInvalido("--fonte deve ser auto, versoes ou textos")
    if artigo and dispositivo:
        raise UsoInvalido("use --artigo ou --dispositivo, não os dois")
    if dispositivo and fonte == "textos":
        raise UsoInvalido("--dispositivo só existe na fonte estruturada (versoes)")
    if artigo:
        _caminho_artigo(artigo)
    linha = localizar(acervo, referencia)
    quer = [n for n, usa in (("versoes", fonte in ("auto", "versoes")), ("textos", fonte in ("auto", "textos"))) if usa]
    if not any(acervo.opcional(n) for n in quer):
        raise DatasetIndisponivel(", ".join(quer), [acervo.ausentes[n] for n in quer if n in acervo.ausentes])
    achado: dict[str, Any] | None = None
    if fonte in ("auto", "versoes"):
        achado = _estruturado(acervo, linha, artigo, dispositivo)
    if achado is None and fonte in ("auto", "textos") and not dispositivo:
        achado = _so_textos(acervo, linha, artigo, maximo)
    cabecalho = {
        "norma": resumo_norma(linha),
        "links": {"oficial": linha["url_oficial"], "internet_archive": linha["url_ia"], "melhor": link_de(linha)},
    }
    if achado is None:
        raise NaoEncontrado(
            "esta norma não tem texto na fonte pedida: o catálogo a conhece, mas Leizilla ainda não publicou o texto "
            "(consulte o PDF oficial)",
            cabecalho,
        )
    avisos = list(achado.pop("avisos"))
    if aviso_rendicao(linha):
        avisos.append(aviso_rendicao(linha))
    precisa_sufixo = (
        bool(linha["sufixo"])
        or acervo.consulta("SELECT count(*) AS n FROM catalogo WHERE texto_id = ?", [linha["texto_id"]])[0]["n"] > 1
    )
    if precisa_sufixo:
        avisos.append(AVISO_SUFIXO)
    if achado.get("recusa"):
        avisos.append(achado["recusa"])
    return {
        **cabecalho,
        **achado,
        "avisos": avisos + list(dict.fromkeys(acervo.avisos)),
    }
