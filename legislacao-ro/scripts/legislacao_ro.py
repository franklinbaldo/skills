#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "duckdb>=1.1",
# ]
# ///
"""
legislacao_ro.py — consulta à legislação estadual de Rondônia a partir dos datasets abertos do Leizilla.

Lê (somente leitura, sem credencial) quatro Parquet publicados pelo Leizilla: `catalogo` (uma linha por norma
listada pela Casa Civil), `relacoes` (extraídas das ementas), `textos` (OCR verbatim) e `versoes` (normas
estruturadas). Tenta o espelho do portal e cai para o Internet Archive; guarda cópia em cache local com checagem
de frescor (padrão 24 h).

Modos:
    buscar   <assunto ou citação>   normas por assunto (ementa/título) ou por citação ("LC 68/1992")
    norma    <citação|norma_id>     tudo sobre uma norma: situação no índice, links, cobertura, relações
    texto    <citação|norma_id>     texto da norma (estruturado se houver, senão OCR), opcionalmente um artigo
    relacoes <citação|norma_id>     relações nos dois sentidos, com o trecho da ementa de cada uma

Saída em JSON por padrão; `--formato texto` para leitura humana.
Rode `python legislacao_ro.py -h` ou `python legislacao_ro.py <modo> -h` para detalhes.
"""

import json
import os
import sys
from dataclasses import dataclass
from typing import Annotated, Any, Literal

import cyclopts
from cyclopts import Parameter
from legislacao_citacao import TIPOS, normalizar_tipo
from legislacao_consultas import NaoEncontrado, UsoInvalido
from legislacao_consultas import buscar as consulta_buscar
from legislacao_consultas import norma as consulta_norma
from legislacao_consultas import relacoes as consulta_relacoes
from legislacao_dados import TTL_PADRAO_HORAS, Acervo, DatasetIndisponivel, Origens
from legislacao_saidas import buscar as saida_buscar
from legislacao_saidas import norma as saida_norma
from legislacao_saidas import relacoes as saida_relacoes
from legislacao_saidas import texto as saida_texto
from legislacao_texto import texto as consulta_texto

Formato = Literal["json", "texto"]


@dataclass
class Fontes:
    """De onde ler os datasets (padrão: espelho do portal, depois Internet Archive, com cache local)."""

    base_url: str | None = None
    """URL ou diretório com catalogo.parquet, relacoes.parquet, textos.parquet e versoes.parquet
    (env LEGISLACAO_RO_BASE_URL)."""
    catalogo: str | None = None
    """caminho local ou URL do catálogo (env LEGISLACAO_RO_CATALOGO)."""
    relacoes: str | None = None
    """caminho local ou URL das relações (env LEGISLACAO_RO_RELACOES)."""
    textos: str | None = None
    """caminho local ou URL da camada de texto (env LEGISLACAO_RO_TEXTOS)."""
    versoes: str | None = None
    """caminho local ou URL das normas estruturadas (env LEGISLACAO_RO_VERSOES)."""
    atualizar: bool = False
    """revalida os datasets no servidor mesmo com cache fresco."""
    offline: bool = False
    """usa só o cache local; nunca acessa a rede."""
    cache_dir: str | None = None
    """diretório de cache (env LEGISLACAO_RO_CACHE; padrão ~/.cache/legislacao-ro)."""
    ttl_horas: float | None = None
    """validade do cache em horas (env LEGISLACAO_RO_TTL_HORAS; padrão 24)."""


def _origens(fontes: Fontes | None) -> Origens:
    f = fontes or Fontes()
    ttl = f.ttl_horas
    if ttl is None:
        ttl = float(os.environ.get("LEGISLACAO_RO_TTL_HORAS", TTL_PADRAO_HORAS))
    return Origens(f.base_url, f.catalogo, f.relacoes, f.textos, f.versoes, f.atualizar, f.offline, f.cache_dir, ttl)


def _emitir(dados: dict[str, Any], formato: Formato, projetar: Any) -> None:
    if formato == "texto":
        print(projetar(dados))
    else:
        print(json.dumps(dados, ensure_ascii=False, indent=2, default=str))


def _executar(fontes: Fontes | None, formato: Formato, consulta: Any, projetar: Any) -> int:
    """Roda `consulta(acervo)`, emite o resultado e traduz erros esperados em mensagem + código de saída."""
    import duckdb

    acervo = Acervo(_origens(fontes))
    try:
        dados = consulta(acervo)
    except UsoInvalido as erro:
        print(f"Erro de uso: {erro}", file=sys.stderr)
        return 2
    except DatasetIndisponivel as erro:
        print(f"Erro: {erro}. Use --base-url/--{erro.nome.split(',')[0]} para apontar outra fonte.", file=sys.stderr)
        return 3
    except NaoEncontrado as erro:
        print(f"Não encontrado: {erro}", file=sys.stderr)
        for aviso in dict.fromkeys(acervo.avisos):
            print(f"AVISO: {aviso}", file=sys.stderr)
        if formato == "json" and erro.detalhe:
            print(json.dumps({"erro": str(erro), **erro.detalhe}, ensure_ascii=False, indent=2, default=str))
        return 1
    except duckdb.Error as erro:
        print(f"Erro ao ler um dataset (formato inesperado ou arquivo corrompido): {erro}", file=sys.stderr)
        return 3
    _emitir(dados, formato, projetar)
    return 1 if dados.get("recusa") else 0


app = cyclopts.App(name="legislacao-ro", help="Legislação estadual de Rondônia (datasets abertos do Leizilla).")


@app.command(name="buscar")
def buscar_cmd(
    consulta: str = "",
    *,
    tipo: str | None = None,
    ano: int | None = None,
    de: int | None = None,
    ate: int | None = None,
    situacao: Literal["revogada", "retificada", "tem-compilada", "sem-indicacao-de-revogacao"] | None = None,
    limite: int = 20,
    formato: Formato = "json",
    fontes: Annotated[Fontes, Parameter(name="*")] = None,  # type: ignore[assignment]
) -> int:
    """Busca normas por assunto (ementa/título) ou por citação.

    Parameters
    ----------
    consulta
        assunto ("plano de carreira"; todos os termos devem casar, sem acento, como início de palavra) ou citação
        ("LC 68/1992", "Lei 1.234", "Decreto 12345"). Ordem: número exato primeiro, depois as mais recentes.
    tipo
        lei, lc, decreto ou decreto-lei.
    ano
        ano exato da norma.
    de
        ano inicial (inclusive).
    ate
        ano final (inclusive).
    situacao
        situação no índice oficial (não é vigência): revogada, retificada, tem-compilada ou sem-indicacao-de-revogacao.
    limite
        máximo de resultados (padrão 20).
    formato
        json (padrão) ou texto.
    """
    canonico = None
    if tipo:
        canonico = normalizar_tipo(tipo)
        if canonico is None:
            print(f"Tipo inválido: {tipo}. Válidos: {', '.join(TIPOS)}", file=sys.stderr)
            return 2
    return _executar(
        fontes,
        formato,
        lambda a: consulta_buscar(
            a, consulta, tipo=canonico, ano=ano, de=de, ate=ate, situacao=situacao, limite=limite
        ),
        saida_buscar,
    )


@app.command(name="norma")
def norma_cmd(
    referencia: str,
    *,
    formato: Formato = "json",
    fontes: Annotated[Fontes, Parameter(name="*")] = None,  # type: ignore[assignment]
) -> int:
    """Tudo sobre uma norma: título, data, ementa, situação no índice (com evidência), links, cobertura e relações.

    Parameters
    ----------
    referencia
        citação ("LC 68/1992", "Lei 1.234", "Decreto 12345") ou norma_id (leizilla-raw-ro-casacivil-lc-00068).
    formato
        json (padrão) ou texto.
    """
    return _executar(fontes, formato, lambda a: consulta_norma(a, referencia), saida_norma)


@app.command(name="texto")
def texto_cmd(
    referencia: str,
    *,
    artigo: str | None = None,
    dispositivo: str | None = None,
    fonte: Literal["auto", "versoes", "textos"] = "auto",
    max: int = 0,  # noqa: A002
    formato: Formato = "json",
    fontes: Annotated[Fontes, Parameter(name="*")] = None,  # type: ignore[assignment]
) -> int:
    """Texto da norma, sempre dizendo de qual fonte veio (estruturada `versoes` ou OCR `textos`).

    Parameters
    ----------
    referencia
        citação ou norma_id.
    artigo
        só este artigo (ex.: 5, 5-A). No OCR só funciona quando a sequência de artigos fecha.
    dispositivo
        caminho de um dispositivo estruturado (ex.: art-5-par-2); só na fonte `versoes`.
    fonte
        auto (estruturada se houver, senão OCR), versoes ou textos.
    max
        trunca o OCR em N caracteres (0 = sem limite); ignorado com --artigo.
    formato
        json (padrão) ou texto.
    """
    return _executar(
        fontes,
        formato,
        lambda a: consulta_texto(a, referencia, artigo=artigo, dispositivo=dispositivo, fonte=fonte, maximo=max),
        saida_texto,
    )


@app.command(name="relacoes")
def relacoes_cmd(
    referencia: str,
    *,
    direcao: Literal["ambas", "saida", "entrada"] = "ambas",
    verbo: Literal["altera", "revoga", "acrescenta", "da-nova-redacao", "regulamenta", "prorroga", "outro"]
    | None = None,
    formato: Formato = "json",
    fontes: Annotated[Fontes, Parameter(name="*")] = None,  # type: ignore[assignment]
) -> int:
    """Relações da norma nos dois sentidos, com o trecho da ementa que produziu cada uma.

    Parameters
    ----------
    referencia
        citação ou norma_id.
    direcao
        saida (a norma age: altera, revoga...), entrada (a norma sofre: alterada por...) ou ambas.
    verbo
        só este verbo.
    formato
        json (padrão) ou texto.
    """
    return _executar(fontes, formato, lambda a: consulta_relacoes(a, referencia, direcao, verbo), saida_relacoes)


def main(tokens: list[str] | None = None) -> int:
    """Roda a CLI e devolve o código de saída (versões novas do Cyclopts chamam sys.exit por conta própria)."""
    try:
        resultado = app(tokens)
    except SystemExit as saida:
        return saida.code if isinstance(saida.code, int) else 1
    return resultado if isinstance(resultado, int) else 0


if __name__ == "__main__":
    sys.exit(main())
