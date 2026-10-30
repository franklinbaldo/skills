#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "pydantic>=2.6",
# ]
# ///
"""
datajud.py — cliente de linha de comando para a API Publica do DataJud (CNJ).

A API expoe METADADOS processuais (capa + movimentacoes) indexados em
Elasticsearch, um indice por tribunal:
    POST https://api-publica.datajud.cnj.jus.br/api_publica_{sigla}/_search

NAO ha inteiro teor / texto de decisao aqui — apenas classe, assuntos, orgao
julgador, grau, datas e a LINHA DE MOVIMENTACAO (tabelas processuais unificadas
do CNJ). Para teor de acordao/voto/sentenca do TJRO use a skill juris-tjro.

Autenticacao: chave PUBLICA unica do CNJ (mesma para todos; pode ser trocada
pelo CNJ a qualquer momento — ver SKILL.md se comecar a dar 401).

Dependencias: cyclopts (CLI) e pydantic: o corpo da requisicao e a resposta da
API (`datajud_modelos.py`), as tabelas do acervo (`datajud_store.py`) e a
entrada e a saida de cada comando sao modelos. O acesso HTTP usa so a stdlib.

Modos:
    processo <CNJ>              capa + movimentacoes de um processo (todos os graus)
    lote     <arquivo>          muitos processos, resposta crua guardada em disco
    buscar   [filtros]          lista processos que casam com os filtros
    contar   [filtros]          apenas o total real (track_total_hits)
    facetas  [filtros] --por X  agregacao (quantos por classe/assunto/orgao/grau)
    codigos  <termo> --por X    descobre codigos de classe/assunto por nome
    estado   <CNJ> [--em DATA]  o processo como o acervo local o conhecia (sem API)
    historico <CNJ>             mudancas observadas de cada registro (sem API)
    novidades <desde>           o que mudou no acervo local desde um instante (sem API)
    banco                       linhas por tabela do acervo local
    migrar                      decompoe o acervo da versao anterior (#125)

Rode `python datajud.py -h` ou `python datajud.py <modo> -h` para detalhes.
"""

import sys
import urllib.request
from pathlib import Path
from typing import Annotated, Literal

import cyclopts
import datajud_store as store
from cyclopts import Parameter
from datajud_api import (
    DEFAULT_TRIBUNAL,
    FalhaHTTPTransitoria,
    _espera_retry_after,
    search,
)
from datajud_cnj import (
    cnj,
    familia_do_cnj,
    so_digitos,
    tribunal_do_cnj,
)
from datajud_comandos import (
    cmd_buscar,
    cmd_codigos,
    cmd_contar,
    cmd_facetas,
)
from datajud_consulta import (
    cmd_lote,
    cmd_processo,
    consultar,
    consultar_um,
    ler_processo,
)
from datajud_formatos import (
    CAPA_FIELDS,
    RUIDO,
    assuntos_str,
    classe_str,
    fmt_data_ajuiz,
    fmt_data_iso,
    grau_label,
    orgao_str,
)
from datajud_saidas import (
    ConsultaLote,
    FalhaIndice,
    ResumoLote,
    _imprimir,
)
from pydantic import BaseModel, ValidationError

# Reexportados: datajud_mcp.py e os testes usam estes nomes como `dj.<nome>`.
__all__ = [
    "CAPA_FIELDS",
    "ConsultaLote",
    "FalhaHTTPTransitoria",
    "FalhaIndice",
    "ResumoLote",
    "ValidationError",
    "_espera_retry_after",
    "assuntos_str",
    "classe_str",
    "consultar",
    "consultar_um",
    "familia_do_cnj",
    "ler_processo",
    "orgao_str",
    "search",
    "so_digitos",
    "store",
    "tribunal_do_cnj",
    "urllib",
]


class Filtros(BaseModel):
    """Filtros comuns aos modos de busca/contagem/agregacao (entrada da CLI)."""

    tribunal: str = DEFAULT_TRIBUNAL
    """sigla do indice (padrao tjro). Ex.: stj, trf1, tjsp, tre-ro (o STF nao tem indice)."""
    classe: str | None = None
    """codigo da classe processual (use o modo `codigos` para descobrir)."""
    assunto: str | None = None
    """texto do assunto (match em assuntos.nome)."""
    assunto_codigo: str | None = None
    """codigo exato do assunto."""
    orgao: str | None = None
    """texto do orgao julgador (match)."""
    grau: Literal["G1", "G2", "JE", "TR", "SUP"] | None = None
    """grau do processo."""
    de: str | None = None
    """data de ajuizamento inicial (DD/MM/AAAA)."""
    ate: str | None = None
    """data de ajuizamento final (DD/MM/AAAA)."""


AsJson = Annotated[bool, Parameter(name=["--json"])]
FiltrosArg = Annotated[Filtros | None, Parameter(name="*")]

app = cyclopts.App(
    name="datajud",
    help="Consulta metadados processuais na API Publica do DataJud (CNJ).",
)


@app.command
def processo(
    numero: str,
    *,
    tribunal: str | None = None,
    so_origem: bool = False,
    movimentos: bool = False,
    json: AsJson = False,
) -> int:
    """Capa + movimentacoes de um processo, em todos os tribunais onde ele aparece.

    Por padrao procura na familia do numero: o tribunal de origem, os demais
    tribunais do estado de origem (TJ, TRT, TRF, TRE, TJM) e os superiores
    (STJ, TST, TSE, STM). O STF nao tem indice na API publica.

    Parameters
    ----------
    numero
        numero do processo (com ou sem mascara CNJ).
    tribunal
        consulta so este indice, sem deduzir familia.
    so_origem
        consulta so o tribunal de origem deduzido do numero.
    movimentos
        lista a linha completa de movimentacao.
    json
        emite JSON em vez do relatorio legivel.
    """
    return cmd_processo(numero, tribunal, movimentos, json, so_origem=so_origem)


@app.command
def lote(
    arquivo: Path,
    *,
    saida: Path | None = None,
    trabalhadores: int = 4,
    so_origem: bool = False,
    json: AsJson = False,
) -> int:
    """Observa muitos processos e acrescenta resultados ao SQLite append-only.

    Cada numero e procurado na familia (origem, estado, superiores) em lotes
    de ate 100 numeros por indice. O padrao nao cria JSON e reconsulta a API
    para registrar a data/hora de cada nova observacao; as versoes anteriores
    nunca sao sobrescritas. --saida habilita exportacao JSON legada.

    Parameters
    ----------
    arquivo
        texto com um numero de processo por linha (com ou sem mascara).
    saida
        exporta tambem JSONs nesse diretorio (opcional; legado).
    trabalhadores
        consultas simultaneas (padrao 4).
    so_origem
        consulta so o tribunal de origem (mais rapido; perde passagem por
        superior e transferencia entre ramos).
    json
        emite o resumo em JSON.
    """
    return cmd_lote(arquivo, saida, trabalhadores, so_origem, json)


@app.command
def buscar(
    *,
    filtros: FiltrosArg = None,
    recentes: bool = False,
    tamanho: int = 20,
    json: AsJson = False,
) -> int:
    """Lista processos que casam com os filtros.

    Parameters
    ----------
    recentes
        ordena por data de ajuizamento decrescente.
    tamanho
        numero de resultados (padrao 20).
    json
        emite JSON em vez do relatorio legivel.
    """
    return cmd_buscar(filtros or Filtros(), recentes, tamanho, json)


@app.command
def contar(*, filtros: FiltrosArg = None, json: AsJson = False) -> int:
    """Apenas o total real de processos no filtro.

    Parameters
    ----------
    json
        emite JSON em vez do relatorio legivel.
    """
    return cmd_contar(filtros or Filtros(), json)


@app.command
def facetas(
    *,
    filtros: FiltrosArg = None,
    por: Literal["classe", "assunto", "orgao", "grau", "sistema"],
    limite: int = 15,
    json: AsJson = False,
) -> int:
    """Agregacao: quantos processos por classe/assunto/orgao/grau.

    Parameters
    ----------
    por
        dimensao da agregacao.
    limite
        itens (padrao 15).
    json
        emite JSON em vez do relatorio legivel.
    """
    return cmd_facetas(filtros or Filtros(), por, limite, json)


@app.command
def codigos(
    termo: str,
    *,
    por: Literal["classe", "assunto"] = "classe",
    tribunal: str = DEFAULT_TRIBUNAL,
    limite: int = 15,
    json: AsJson = False,
) -> int:
    """Descobre codigos de classe/assunto pelo nome.

    Parameters
    ----------
    termo
        parte do nome (ex.: 'execucao fiscal', 'aposentadoria').
    por
        dimensao a pesquisar.
    tribunal
        sigla do indice (padrao tjro).
    limite
        itens (padrao 15).
    json
        emite JSON em vez do relatorio legivel.
    """
    return cmd_codigos(termo, por, tribunal, limite, json)


@app.command
def banco(*, json: AsJson = False) -> int:
    """Linhas por tabela do acervo SQLite, sem acessar a API.

    Parameters
    ----------
    json
        emite `Estatisticas` em JSON.
    """
    dados = store.estatisticas()
    if json:
        _imprimir(dados)
    else:
        print(f"SQLite: {dados.banco} (versao {dados.versao})")
        for tabela, linhas in dados.tabelas.items():
            print(f"  {tabela:24} {linhas:>9}")
        print(f"  {dados.consultas_com_erro} consultas com erro")
    return 0


@app.command
def migrar(*, json: AsJson = False) -> int:
    """Converte para a versao atual o acervo de versao anterior (#125, #128).

    Roda sozinho na primeira abertura do banco; o comando existe para fazer a
    conversao (dezenas de segundos em milhares de documentos) num momento
    escolhido. O arquivo antigo fica ao lado, como backup. Idempotente.

    Parameters
    ----------
    json
        emite `ResultadoMigracao` em JSON.
    """
    resultado = store.migrar()
    if json:
        _imprimir(resultado)
    else:
        if resultado.origem == "nada":
            print("Acervo ja esta na versao atual.")
        else:
            print(f"Convertido de {resultado.origem}: {resultado.observacoes} observacoes; "
                  f"o arquivo anterior ficou em {resultado.backup}")
    return 0


@app.command
def historico(
    numero: str,
    *,
    limite: int = 100,
    detalhar: bool = False,
    json: AsJson = False,
) -> int:
    """Mudancas observadas de cada registro do processo, sem acessar a API.

    Parameters
    ----------
    numero
        numero do processo (com ou sem mascara CNJ).
    limite
        mudancas por registro, das mais recentes (padrao 100).
    detalhar
        lista os movimentos e assuntos que entraram e sairam.
    json
        emite `HistoricoProcesso` em JSON.
    """
    saida = store.historico(numero, limite=limite, detalhar=detalhar)
    if json:
        _imprimir(saida)
        return 0
    print(f"{len(saida.registros)} registro(s) de {cnj(numero)} no acervo local")
    for item in saida.registros:
        r = item.registro
        print(f"\n### {r.tribunal.upper()} {r.grau or ''}: {item.observacoes} observacoes, "
              f"de {item.primeira_vista[:19]} a {item.ultima_vista[:19]}")
        for m in item.mudancas:
            marcas = "primeira observacao" if m.primeira else (
                f"+{m.entraram} -{m.sairam}" + (" capa nova" if m.capa_nova else ""))
            print(f"  {m.observado_em[:19]}  {marcas}")
            for i in m.itens:
                sinal = "+" if i.evento == "entrou" else "-"
                quando = fmt_data_iso(i.data_hora) if i.data_hora else ""
                print(f"      {sinal} {i.tipo} {quando} ({i.codigo}) {i.nome or ''}")
    return 0


@app.command
def estado(
    numero: str,
    *,
    em: str | None = None,
    movimentos: bool = False,
    json: AsJson = False,
) -> int:
    """O processo como o acervo local o conhecia, sem acessar a API.

    Parameters
    ----------
    numero
        numero do processo (com ou sem mascara CNJ).
    em
        data (AAAA-MM-DD, ate o fim do dia em UTC) ou instante ISO; omitido,
        o estado mais recente observado.
    movimentos
        lista todos os movimentos vigentes (sem a flag, so os cinco ultimos).
    json
        emite `EstadoProcesso` em JSON.
    """
    saida = store.estado(numero, em=em)
    if json:
        _imprimir(saida)
        return 0 if saida.registros else 1
    if not saida.registros:
        ate = f" ate {saida.em}" if saida.em else ""
        print(f"{cnj(numero)} nao foi observado{ate} no acervo local.", file=sys.stderr)
        return 1
    for item in saida.registros:
        r, capa = item.registro, item.capa
        print(f"### {r.tribunal.upper()} · {grau_label(r.grau)} — observado em {item.observado_em[:19]}")
        if capa:
            c = capa.capa
            print(f"    classe:   {c.classe_nome} ({c.classe_codigo})")
            print(f"    orgao:    {capa.orgao.nome if capa.orgao else '—'}")
            print(f"    ajuizado: {fmt_data_ajuiz(c.data_ajuizamento)}")
        if item.assuntos is None:
            print("    assuntos: nunca vieram numa consulta (recorte de campos)")
        else:
            print(f"    assuntos: {', '.join(a.nome or str(a.codigo) for a in item.assuntos) or '—'}")
        if item.movimentos is None:
            print("    movimentos: nunca vieram numa consulta (recorte de campos)")
            continue
        lista = item.movimentos if movimentos else item.movimentos[-5:]
        print(f"    {len(item.movimentos)} movimento(s) vigente(s), vistos em "
              f"{item.movimentos_observados_em[:19]}{'' if movimentos else '; os ultimos:'}")
        for mv in lista:
            print(f"      {fmt_data_iso(mv.movimento.data_hora)}  ({mv.tipo.codigo}) {mv.tipo.nome}")
    return 0


@app.command
def novidades(
    desde: str,
    *,
    numeros: Path | None = None,
    todos: bool = False,
    json: AsJson = False,
) -> int:
    """O que mudou no acervo local desde um instante, sem acessar a API.

    Movimentos que entraram ou sairam, capas novas e processos que apareceram
    noutro tribunal ou grau. A primeira observacao de um registro e linha de
    base e nao novidade. Para saber o que mudou na fonte, rode antes o `lote`.

    Parameters
    ----------
    desde
        data (AAAA-MM-DD, desde o inicio do dia em UTC) ou instante ISO.
    numeros
        restringe aos processos deste arquivo (um CNJ por linha).
    todos
        lista tambem os movimentos de rotina (RUIDO); sem a flag, so os marcos.
    json
        emite `Novidades` em JSON, com todos os movimentos e o campo `marco`.
    """
    lista = None
    if numeros is not None:
        lista = [x.strip() for x in numeros.read_text(encoding="utf-8").splitlines() if x.strip()]
    saida = store.novidades(desde, numeros=lista, ruido=RUIDO)
    if json:
        _imprimir(saida)
        return 0
    print(f"{len(saida.processos)} processo(s) com novidade entre {saida.desde[:19]} e {saida.ate[:19]}")
    for processo in saida.processos:
        novo = " (primeira observacao)" if processo.processo_novo else ""
        print(f"\n### {cnj(processo.numero)}{novo}")
        for item in processo.registros:
            r = item.registro
            sinais = []
            if item.registro_novo and not processo.processo_novo:
                sinais.append(f"registro novo, com {item.movimentos_iniciais} movimento(s)")
            if item.capa_nova:
                sinais.append("capa nova")
            print(f"    {r.tribunal.upper()} · {grau_label(r.grau)}{': ' + '; '.join(sinais) if sinais else ''}")
            for m in item.movimentos:
                if todos or m.marco:
                    sinal = "+" if m.evento == "entrou" else "-"
                    print(f"      {sinal} {fmt_data_iso(m.data_hora)}  ({m.codigo}) {m.nome}")
            rotina = sum(not m.marco for m in item.movimentos)
            if rotina and not todos:
                print(f"      ({rotina} movimento(s) de rotina; --todos lista)")
    return 0


def main(tokens=None) -> int:
    try:
        return app(tokens) or 0
    except RuntimeError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
