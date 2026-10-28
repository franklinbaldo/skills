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

import json
import email.utils
import datetime
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated, Any, Literal

import cyclopts
import datajud_store as store
from cyclopts import Parameter
from datajud_modelos import Assunto, Codificado, Movimento, OrgaoJulgador, RequisicaoBusca
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

BASE = "https://api-publica.datajud.cnj.jus.br"
# Chave PUBLICA do CNJ — a mesma para todo mundo, documentada na wiki do DataJud.
# Se der 401, pegue a atualizada em https://datajud-wiki.cnj.jus.br/api-publica/acesso/
APIKEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
UA = "Mozilla/5.0 (datajud skill)"

DEFAULT_TRIBUNAL = "tjro"

# Campos de capa que queremos ver (evita puxar o array gigante de movimentos
# quando nao precisamos dele).
CAPA_FIELDS = [
    "numeroProcesso", "classe", "assuntos", "orgaoJulgador", "grau",
    "sistema", "formato", "dataAjuizamento", "dataHoraUltimaAtualizacao",
    "nivelSigilo", "tribunal",
]

# Códigos de movimento que não mudam o estado útil do processo. Ver a docstring
# de `datajud_mcp.py`: filtra-se o ruído, que é estável, e não os marcos, que não são.
RUIDO = {
    1051,  # Decurso de Prazo
    92,    # Publicação
    1061,  # Disponibilização no Diário da Justiça Eletrônico
    60,    # Expedição de documento
    581,   # Juntada
    # Medidos em 2026-10-19 num acervo de 3.448 processos (TJRO, TRT14, TRF1):
    # depois dos cinco acima, eram estes que ocupavam o "último marco" sem mudar
    # o estado do processo (petição sozinha respondia por 728).
    85,     # Petição (juntada de)
    51,     # Conclusão
    11010,  # Mero expediente
    12291,  # Movimentação processual (genérico)
    12263,  # Intimação (expedida)
    106,    # Mandado (expedido)
    12270,  # Documento
    10966,  # Mudança de classe processual
    14738,  # Retificação de classe processual
    14739,  # Evolução da classe processual
}

# Rotulos de grau conforme aparecem no acervo.
GRAU_LABEL = {
    "G1": "1o grau", "G2": "2o grau",
    "JE": "Juizado Especial", "TR": "Turma Recursal",
    "SUP": "Tribunal Superior",
}


# ----------------------------------------------------------------------------
# HTTP com retry/backoff — o rate limit do DataJud e a principal armadilha.
# Ha DOIS sabores de rejeicao:
#   1. HTTP 429 no gateway;
#   2. HTTP 200 com {"error": {"root_cause":[{"type":"es_rejected_execution_exception"}]}}
#      quando a fila de busca do Elasticsearch enche.
# Ambos sao transitorios e pedem backoff.
# ----------------------------------------------------------------------------
def _endpoint(tribunal):
    return f"{BASE}/api_publica_{tribunal.lower()}/_search"


def _is_es_rejection(d):
    if not isinstance(d, dict) or "error" not in d:
        return False
    erro = d.get("error")
    rc = erro.get("root_cause", []) if isinstance(erro, dict) else []
    return any("rejected_execution" in (c.get("type", "")) for c in rc)


def _guardar(tribunal, body, resposta=None, *, erro=None):
    """Toda resposta e toda falha de rede viram eventos duraveis no SQLite."""
    try:
        if resposta is None:
            store.registrar_erro(tribunal, body, erro or "erro sem descricao")
        else:
            store.registrar_resposta(
                tribunal, body, resposta, resultado="erro" if erro else "ok",
                erro=erro,
            )
    except (OSError, sqlite3.Error, ValueError, TypeError) as e:
        raise RuntimeError(f"falha ao persistir a observacao no SQLite: {e}") from e


def _espera_retry_after(cabecalhos, espera):
    """Respeita a janela informada pelo CNJ, limitada a 120 segundos."""
    valor = cabecalhos.get("Retry-After") if cabecalhos else None
    if valor:
        try:
            segundos = float(valor)
        except (ValueError, TypeError):
            try:
                data = email.utils.parsedate_to_datetime(valor)
                segundos = (data - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                segundos = espera
        return max(0, min(120, segundos))
    return espera


def search(body, tribunal=DEFAULT_TRIBUNAL, timeout=90, tentativas=5):
    url = _endpoint(tribunal)
    data = json.dumps(body).encode("utf-8")
    espera = 2.0
    ultimo_erro = None
    for n in range(1, tentativas + 1):
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json",
                     "Accept": "application/json",
                     "Authorization": f"APIKey {APIKEY}",
                     "User-Agent": UA},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resposta_bytes = r.read()
            try:
                d = json.loads(resposta_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                ultimo_erro = f"resposta HTTP sem JSON valido: {e}"
                _guardar(tribunal, body, erro=ultimo_erro)
                if n < tentativas:
                    time.sleep(espera)
                    espera = min(espera * 2, 30)
                    continue
                raise RuntimeError(ultimo_erro) from e

            if not isinstance(d, dict):
                _guardar(tribunal, body, erro="resposta nao e objeto JSON")
                raise RuntimeError("resposta DataJud sem formato JSON esperado")
            if "error" in d:
                ultimo_erro = f"DataJud: {str(d['error'])[:300]}"
                _guardar(tribunal, body, d, erro=ultimo_erro)
                if _is_es_rejection(d) and n < tentativas:
                    time.sleep(espera)
                    espera = min(espera * 2, 30)
                    continue
                raise RuntimeError(ultimo_erro)
            if not isinstance(d.get("hits"), dict):
                _guardar(tribunal, body, d, erro="resposta sem hits")
                raise RuntimeError("resposta DataJud sem hits: nao interpretar como ausencia")

            _guardar(tribunal, body, d)
            return d
        except urllib.error.HTTPError as e:
            corpo = ""
            try:
                corpo = e.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            ultimo_erro = f"HTTP {e.code}: {corpo}"
            _guardar(tribunal, body, erro=ultimo_erro)
            if e.code in (429, 500, 502, 503, 504) and n < tentativas:
                time.sleep(_espera_retry_after(e.headers, espera))
                espera = min(espera * 2, 30)
                continue
            if e.code == 401:
                raise RuntimeError(
                    "HTTP 401: a chave publica provavelmente foi trocada pelo CNJ. "
                    "Pegue a atual em https://datajud-wiki.cnj.jus.br/api-publica/acesso/ "
                    "e atualize APIKEY no topo deste script.") from e
            raise RuntimeError(ultimo_erro) from e
        except (urllib.error.URLError, TimeoutError) as e:
            ultimo_erro = f"rede: {e}"
            _guardar(tribunal, body, erro=ultimo_erro)
            if n < tentativas:
                time.sleep(espera)
                espera = min(espera * 2, 30)
                continue
            raise RuntimeError(ultimo_erro) from e
    raise RuntimeError(ultimo_erro or "falha desconhecida")


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def so_digitos(n):
    return re.sub(r"\D", "", n or "")


def cnj(n):
    """20 digitos -> NNNNNNN-DD.AAAA.J.TR.OOOO."""
    d = so_digitos(n)
    if len(d) == 20:
        return f"{d[0:7]}-{d[7:9]}.{d[9:13]}.{d[13:14]}.{d[14:16]}.{d[16:20]}"
    return n or ""


# Segmento J.TR do numero CNJ (Res. CNJ 65/2008). J: 1 STF, 3 STJ, 4 federal,
# 5 trabalho, 6 eleitoral, 7 militar da Uniao, 8 estadual, 9 militar estadual.
# TR: a UF (estadual, eleitoral, militar estadual), a regiao (TRT, TRF) ou 00
# (tribunal superior). O numero diz o tribunal de ORIGEM; o mesmo numero segue
# no STJ/TST quando o processo sobe (medido em 2026-10-19: 7 de 100 processos
# do TJRO com 2o grau estavam no indice `stj` com o numero do TJRO) e, raro,
# pode aparecer em outro ramo do mesmo estado depois de declinio de competencia.
_UF = {
    "01": "ac", "02": "al", "03": "ap", "04": "am", "05": "ba", "06": "ce",
    "07": "df", "08": "es", "09": "go", "10": "ma", "11": "mt", "12": "ms",
    "13": "mg", "14": "pa", "15": "pb", "16": "pr", "17": "pe", "18": "pi",
    "19": "rj", "20": "rn", "21": "rs", "22": "ro", "23": "rr", "24": "sc",
    "25": "se", "26": "sp", "27": "to",
}
_TRT_UFS = {
    1: ["rj"], 2: ["sp"], 3: ["mg"], 4: ["rs"], 5: ["ba"], 6: ["pe"], 7: ["ce"],
    8: ["pa", "ap"], 9: ["pr"], 10: ["df", "to"], 11: ["am", "rr"], 12: ["sc"],
    13: ["pb"], 14: ["ro", "ac"], 15: ["sp"], 16: ["ma"], 17: ["es"], 18: ["go"],
    19: ["al"], 20: ["se"], 21: ["rn"], 22: ["pi"], 23: ["mt"], 24: ["ms"],
}
_TRF_UFS = {
    1: ["ac", "am", "ap", "ba", "df", "go", "ma", "mt", "pa", "pi", "ro", "rr", "to"],
    2: ["rj", "es"], 3: ["sp", "ms"], 4: ["rs", "pr", "sc"],
    5: ["pe", "al", "ce", "pb", "rn", "se"], 6: ["mg"],
}
_TJM = {"mg", "rs", "sp"}
# Indices dos tribunais superiores na API publica. O STF nao tem indice
# (`api_publica_stf` responde index_not_found, medido em 2026-10-19).
SUPERIORES = ["stj", "tst", "tse", "stm"]


def _tj(uf):
    return "tjdft" if uf == "df" else f"tj{uf}"


def _tre(uf):
    return "tre-dft" if uf == "df" else f"tre-{uf}"


def tribunal_do_cnj(n):
    """Indice DataJud do tribunal de ORIGEM do numero CNJ, ou None se nao der.

    None tambem para o STF, que nao tem indice na API publica.
    """
    d = so_digitos(n)
    if len(d) != 20:
        return None
    j, tr = d[13], int(d[14:16])
    uf = _UF.get(d[14:16])
    if tr == 0:
        return {"3": "stj", "5": "tst", "6": "tse", "7": "stm"}.get(j)
    if j == "8" and uf:
        return _tj(uf)
    if j == "6" and uf:
        return _tre(uf)
    if j == "7" and 1 <= tr <= 12:
        return "stm"
    if j == "9" and uf in _TJM:
        return f"tjm{uf}"
    if j == "5" and tr in _TRT_UFS:
        return f"trt{tr}"
    if j == "4" and tr in _TRF_UFS:
        return f"trf{tr}"
    return None


def _ufs_do_cnj(d):
    j, tr = d[13], int(d[14:16])
    if j in "689" and d[14:16] in _UF:
        return [_UF[d[14:16]]]
    if j == "5":
        return _TRT_UFS.get(tr, [])
    # Federal: a regiao cobre varios estados (o TRF1, treze); o TR nao diz qual.
    return []


def familia_do_cnj(n):
    """Indices onde o processo pode estar: a origem, os tribunais do estado de
    origem (TJ, TRT, TRF, TRE e, onde existe, TJM) e os superiores.

    Vazia quando o numero nao revela tribunal (malformado, ou STF)."""
    d = so_digitos(n)
    origem = tribunal_do_cnj(n)
    if origem is None:
        return []
    indices = [origem]
    for uf in _ufs_do_cnj(d):
        indices += [_tj(uf), _tre(uf)]
        indices += [f"trt{r}" for r, ufs in _TRT_UFS.items() if uf in ufs]
        indices += [f"trf{r}" for r, ufs in _TRF_UFS.items() if uf in ufs]
        if uf in _TJM:
            indices.append(f"tjm{uf}")
    indices += SUPERIORES
    return list(dict.fromkeys(indices))


# ----------------------------------------------------------------------------
# Modelos de entrada e saida de `consultar` e do modo `lote`
# ----------------------------------------------------------------------------
def _validar_cnj(valor: str) -> str:
    d = so_digitos(valor)
    if len(d) != 20:
        raise ValueError(f"numero CNJ precisa de 20 digitos: {valor!r}")
    return cnj(d)


NumeroCNJ = Annotated[str, AfterValidator(_validar_cnj)]
"""Numero de processo com ou sem mascara; vira NNNNNNN-DD.AAAA.J.TR.OOOO."""


class FalhaIndice(BaseModel):
    """Indice que nao respondeu: o processo nao e ausente nele, so nao foi visto."""

    indice: str
    erro: str


class Registro(BaseModel):
    """Um registro (um grau) do processo num tribunal, como a API o devolveu.

    Guarda o hit cru (`_index`, `_source`) intacto: a capa e os movimentos sao
    o dado; as propriedades so leem o que todo consumidor precisa.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    indice_bruto: str = Field(default="", alias="_index")
    fonte: dict[str, Any] = Field(alias="_source")

    @property
    def tribunal(self) -> str:
        """`api_publica_tjro` -> `tjro`."""
        return self.indice_bruto.removeprefix("api_publica_")

    @property
    def numero(self) -> str:
        return self.fonte.get("numeroProcesso") or ""

    @property
    def grau(self) -> str | None:
        return self.fonte.get("grau")


class ConsultaLote(BaseModel):
    """Entrada de `consultar`: os numeros e onde procura-los."""

    numeros: list[NumeroCNJ]
    so_origem: bool = False
    """so o tribunal de origem, sem a familia (estado de origem + superiores)."""
    trabalhadores: int = Field(default=4, ge=1, le=16)
    """consultas simultaneas a API."""


class ProcessoConsultado(BaseModel):
    """Saida de `consultar` por processo; e tambem o JSON gravado pelo `lote`."""

    model_config = ConfigDict(populate_by_name=True)

    processo: NumeroCNJ
    origem: str | None
    """indice do tribunal de origem deduzido do numero (None: malformado ou STF)."""
    consultados: list[str]
    """indices perguntados; ausencia so vale para quem foi consultado e respondeu."""
    registros: list[Registro] = Field(default_factory=list, alias="hits")
    falhas: list[FalhaIndice] = Field(default_factory=list)

    @property
    def encontrado(self) -> bool:
        return bool(self.registros)

    @property
    def tribunais(self) -> list[str]:
        return list(dict.fromkeys(r.tribunal for r in self.registros))

    def para_disco(self) -> str:
        return self.model_dump_json(by_alias=True)


class FalhaLote(BaseModel):
    processo: NumeroCNJ
    indices: list[str]


class PresencaForaDaOrigem(BaseModel):
    processo: NumeroCNJ
    tambem_em: list[str]


class ResumoLote(BaseModel):
    """Saida do modo `lote`."""

    processos: int
    em_disco: int
    encontrados: int
    tambem_em_outro_tribunal: list[PresencaForaDaOrigem] = Field(default_factory=list)
    sem_tribunal: list[NumeroCNJ] = Field(default_factory=list)
    """numeros validos que nao revelam tribunal com indice na API (malformado, STF)."""
    invalidos: list[str] = Field(default_factory=list)
    """linhas do arquivo que nao sao numero CNJ."""
    falhas: list[FalhaLote] = Field(default_factory=list)
    saida: str


class DocumentoProcesso(BaseModel):
    """Um registro na saida `--json` do modo `processo`."""

    model_config = ConfigDict(populate_by_name=True)

    tribunal: str
    grau: str | None = None
    classe: Codificado | None = None
    assuntos: list[Assunto] | None = None
    orgao_julgador: OrgaoJulgador | None = Field(default=None, alias="orgaoJulgador")
    data_ajuizamento: str | None = Field(default=None, alias="dataAjuizamento")
    ultima_atualizacao: str | None = Field(default=None, alias="ultimaAtualizacao")
    movimentos: list[Movimento] | None = None
    """nulo sem `--movimentos`."""


class SaidaProcesso(BaseModel):
    """Saida `--json` do modo `processo`."""

    processo: NumeroCNJ
    consultados: list[str]
    falhas: list[FalhaIndice]
    documentos: list[DocumentoProcesso]


class ItemBusca(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    numero_processo: str = Field(alias="numeroProcesso")
    grau: str | None = None
    classe: Codificado | None = None
    assuntos: list[Assunto] | None = None
    orgao_julgador: str | None = Field(default=None, alias="orgaoJulgador")
    """nome do orgao."""
    data_ajuizamento: str | None = Field(default=None, alias="dataAjuizamento")


class SaidaBusca(BaseModel):
    """Saida `--json` do modo `buscar`."""

    tribunal: str
    total: int
    retornados: int
    resultados: list[ItemBusca]


class SaidaContagem(BaseModel):
    """Saida `--json` do modo `contar`."""

    tribunal: str
    total: int


class Faceta(BaseModel):
    chave: str | int
    qtd: int


class SaidaFacetas(BaseModel):
    """Saida `--json` do modo `facetas`."""

    tribunal: str
    total: int
    por: str
    buckets: list[Faceta]


class CodigoEncontrado(BaseModel):
    codigo: int | str
    nome: str
    qtd: int


class SaidaCodigos(BaseModel):
    """Saida `--json` do modo `codigos`."""

    por: str
    termo: str
    itens: list[CodigoEncontrado]


def _imprimir(modelo: BaseModel) -> None:
    print(modelo.model_dump_json(by_alias=True, indent=2))


def consultar(entrada: ConsultaLote) -> dict[str, ProcessoConsultado]:
    """Procura cada numero em todos os indices da sua familia (ou so na origem).

    Uma consulta `terms` por indice para ate LOTE numeros, em paralelo. Devolve
    um `ProcessoConsultado` por numero (chave: os 20 digitos). Indice que falha
    fica em `falhas`, e o processo nao deve ser tratado como ausente nele.
    """
    alvo: dict[str, ProcessoConsultado] = {}
    for n in entrada.numeros:
        indices = [tribunal_do_cnj(n)] if entrada.so_origem else familia_do_cnj(n)
        alvo[so_digitos(n)] = ProcessoConsultado(
            processo=n, origem=tribunal_do_cnj(n), consultados=[i for i in indices if i])
    por_indice: dict[str, list[str]] = {}
    for d, item in alvo.items():
        for i in item.consultados:
            por_indice.setdefault(i, []).append(d)
    tarefas = [(i, ds[k:k + LOTE]) for i, ds in por_indice.items() for k in range(0, len(ds), LOTE)]

    def rodar(tarefa):
        i, ds = tarefa

        def consultar_parte(numeros, subdividir=True):
            try:
                d = search(RequisicaoBusca(
                    size=len(numeros) * 10,
                    query={"terms": {"numeroProcesso": numeros}},
                ).bruto(), tribunal=i)
                hits = d.get("hits", {}).get("hits", [])
                total = d.get("hits", {}).get("total", {}).get("value", 0)
                if total > len(hits):
                    raise RuntimeError(f"resposta truncada em {i}: {len(hits)} de {total}")
                return [Registro.model_validate(h) for h in hits], []
            except (RuntimeError, ValidationError) as e:
                # Uma falha em 100 numeros nao deve invalidar os 100:
                # tente partes menores, mas sem recursao ilimitada.
                if subdividir and len(numeros) > 25 and (
                    "HTTP 429" in str(e) or "HTTP 504" in str(e)
                    or "HTTP 503" in str(e) or "HTTP 502" in str(e)
                ):
                    registros, falhas = [], []
                    for k in range(0, len(numeros), 25):
                        encontrados, erros = consultar_parte(numeros[k:k + 25], False)
                        registros.extend(encontrados)
                        falhas.extend(erros)
                    return registros, falhas
                return [], [(n, str(e)[:200]) for n in numeros]

        return consultar_parte(ds)

    with ThreadPoolExecutor(entrada.trabalhadores) as pool:
        futuros = {pool.submit(rodar, t): t for t in tarefas}
        for futuro in as_completed(futuros):
            i, ds = futuros[futuro]
            try:
                registros, falhas = futuro.result()
                for registro in registros:
                    if registro.numero in alvo:
                        alvo[registro.numero].registros.append(registro)
                for num, erro in falhas:
                    alvo[num].falhas.append(FalhaIndice(indice=i, erro=erro))
            except (RuntimeError, ValidationError) as e:
                for num in ds:
                    alvo[num].falhas.append(FalhaIndice(indice=i, erro=str(e)[:200]))
    for item in alvo.values():
        item.registros.sort(key=lambda r: (r.tribunal, r.grau or ""))
    return alvo


def fmt_data_ajuiz(s):
    """AAAAMMDDHHMMSS -> DD/MM/AAAA HH:MM."""
    s = (s or "").strip()
    m = re.match(r"(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?", s)
    if not m:
        return s
    ano, mes, dia, hh, mm = m.groups()
    out = f"{dia}/{mes}/{ano}"
    if hh and mm:
        out += f" {hh}:{mm}"
    return out


def fmt_data_iso(s):
    """ISO 2026-06-13T09:45:09Z -> DD/MM/AAAA HH:MM."""
    s = (s or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})", s)
    if not m:
        return s
    ano, mes, dia, hh, mm = m.groups()
    return f"{dia}/{mes}/{ano} {hh}:{mm}"


def _data14(s, fim=False):
    """DD/MM/AAAA ou AAAA-MM-DD -> AAAAMMDDHHMMSS (14 digitos, para range)."""
    s = (s or "").strip()
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        base = f"{m.group(3)}{m.group(2)}{m.group(1)}"
    else:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
        if m:
            base = f"{m.group(1)}{m.group(2)}{m.group(3)}"
        else:
            base = so_digitos(s)[:8]
    base = (base + "0" * 8)[:8]
    return base + ("235959" if fim else "000000")


def grau_label(g):
    return GRAU_LABEL.get(g, g or "—")


def classe_str(src):
    c = src.get("classe") or {}
    cod = c.get("codigo")
    nome = c.get("nome") or "—"
    return f"{nome} ({cod})" if cod is not None else nome


def assuntos_str(src, limite=4):
    a = src.get("assuntos") or []
    nomes = []
    vistos = set()
    for x in a:
        nome = x.get("nome")
        if nome and nome not in vistos:
            vistos.add(nome)
            nomes.append(nome)
    extra = ""
    if len(nomes) > limite:
        extra = f" (+{len(nomes) - limite})"
        nomes = nomes[:limite]
    return ("; ".join(nomes) + extra) if nomes else "—"


def orgao_str(src):
    o = src.get("orgaoJulgador") or {}
    return o.get("nome") or "—"


# ----------------------------------------------------------------------------
# Montagem de query a partir dos filtros comuns
# ----------------------------------------------------------------------------
def montar_query(args):
    must = []
    filt = []

    if getattr(args, "classe", None):
        filt.append({"term": {"classe.codigo": int(args.classe)}})
    if getattr(args, "assunto_codigo", None):
        filt.append({"term": {"assuntos.codigo": int(args.assunto_codigo)}})
    if getattr(args, "assunto", None):
        must.append({"match": {"assuntos.nome": args.assunto}})
    if getattr(args, "orgao", None):
        must.append({"match": {"orgaoJulgador.nome": args.orgao}})
    if getattr(args, "grau", None):
        filt.append({"term": {"grau.keyword": args.grau}})

    de = getattr(args, "de", None)
    ate = getattr(args, "ate", None)
    if de or ate:
        rng = {}
        if de:
            rng["gte"] = _data14(de, fim=False)
        if ate:
            rng["lte"] = _data14(ate, fim=True)
        filt.append({"range": {"dataAjuizamento": rng}})

    if not must and not filt:
        return {"match_all": {}}
    q = {"bool": {}}
    if must:
        q["bool"]["must"] = must
    if filt:
        q["bool"]["filter"] = filt
    return q


# ----------------------------------------------------------------------------
# Modo: processo
# ----------------------------------------------------------------------------
def consultar_um(numero: str, *, tribunal: str | None = None,
                 so_origem: bool = False) -> ProcessoConsultado:
    """Um processo: so no indice pedido, ou na familia do numero (o padrao)."""
    if not tribunal:
        return consultar(ConsultaLote(numeros=[numero], so_origem=so_origem))[so_digitos(numero)]
    d = search(RequisicaoBusca(size=50, query={"match": {"numeroProcesso": so_digitos(numero)}},
                               sort=[{"grau.keyword": "asc"}]).bruto(), tribunal=tribunal)
    registros = [Registro.model_validate(h) for h in d.get("hits", {}).get("hits", [])]
    for r in registros:
        r.indice_bruto = r.indice_bruto or f"api_publica_{tribunal}"
    return ProcessoConsultado(processo=numero, origem=tribunal_do_cnj(numero),
                              consultados=[tribunal], registros=registros)


def cmd_processo(numero: str, tribunal: str | None, movimentos: bool, as_json: bool,
                 so_origem: bool = False):
    nr = so_digitos(numero)
    item = consultar_um(numero, tribunal=tribunal, so_origem=so_origem)
    onde = ", ".join(i.upper() for i in item.consultados) or "nenhum indice (numero sem tribunal deduzivel)"
    for f in item.falhas:
        print(f"Aviso: {f.indice.upper()} nao respondeu ({f.erro}).", file=sys.stderr)
    if not item.encontrado:
        if item.falhas or not item.consultados:
            print(f"Consulta incompleta de {cnj(nr)} ({onde}): ausencia nao confirmada.",
                  file=sys.stderr)
        else:
            print(f"Nenhum processo {cnj(nr)} encontrado em {onde}.", file=sys.stderr)
        return 1

    if as_json:
        documentos = []
        for r in item.registros:
            src = r.fonte
            documentos.append(DocumentoProcesso.model_validate({
                "tribunal": r.tribunal,
                "grau": src.get("grau"),
                "classe": src.get("classe"),
                "assuntos": src.get("assuntos"),
                "orgaoJulgador": src.get("orgaoJulgador"),
                "dataAjuizamento": src.get("dataAjuizamento"),
                "ultimaAtualizacao": src.get("dataHoraUltimaAtualizacao"),
                "movimentos": src.get("movimentos") if movimentos else None,
            }))
        _imprimir(SaidaProcesso(processo=item.processo, consultados=item.consultados,
                                falhas=item.falhas, documentos=documentos))
        return 0

    print(f"Processo {item.processo} — {len(item.registros)} registro(s) em "
          f"{', '.join(t.upper() for t in item.tribunais)} (consultados: {onde})")
    print("=" * 92)
    for r in item.registros:
        src = r.fonte
        print(f"\n### {r.tribunal.upper()} · {grau_label(src.get('grau'))} — {classe_str(src)}")
        print(f"    assuntos: {assuntos_str(src)}")
        print(f"    orgao:    {orgao_str(src)}")
        print(f"    sistema:  {(src.get('sistema') or {}).get('nome','—')} | "
              f"formato: {(src.get('formato') or {}).get('nome','—')} | "
              f"sigilo: {src.get('nivelSigilo','—')}")
        print(f"    ajuizado: {fmt_data_ajuiz(src.get('dataAjuizamento'))} | "
              f"atualizado: {fmt_data_iso(src.get('dataHoraUltimaAtualizacao'))}")
        movs = src.get("movimentos") or []
        if movimentos and movs:
            movs_ord = sorted(movs, key=lambda m: m.get("dataHora", ""))
            print(f"    --- {len(movs_ord)} movimento(s) ---")
            for m in movs_ord:
                compl = ""
                ct = m.get("complementosTabelados") or []
                if ct:
                    vals = "; ".join(f"{c.get('descricao','')}={c.get('nome','')}"
                                     for c in ct if c.get("nome"))
                    if vals:
                        compl = f"  [{vals}]"
                print(f"      {fmt_data_iso(m.get('dataHora'))}  "
                      f"({m.get('codigo')}) {m.get('nome')}{compl}")
        elif movs:
            print(f"    movimentos: {len(movs)} (use --movimentos para listar)")
    return 0


# ----------------------------------------------------------------------------
# Modo: buscar
# ----------------------------------------------------------------------------
def cmd_buscar(filtros: "Filtros", recentes: bool, tamanho: int, as_json: bool):
    body = RequisicaoBusca(
        size=tamanho, track_total_hits=True, query=montar_query(filtros), source=CAPA_FIELDS,
        sort=[{"dataAjuizamento": "desc"}] if recentes else None,
    ).model_dump(by_alias=True, exclude_none=True)

    d = search(body, tribunal=filtros.tribunal)
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
    d = search(body, tribunal=filtros.tribunal)
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
    d = search(body, tribunal=filtros.tribunal)
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
    d = search(body, tribunal=tribunal)
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
LOTE = 100


def _arquivo_lote(saida: Path, numero: str) -> Path:
    return saida / (tribunal_do_cnj(numero) or "sem-tribunal") / f"{so_digitos(numero)}.json"


def ler_processo(saida: Path, numero: str) -> ProcessoConsultado | None:
    """Le o legado de JSON individual, se houver (SQLite e a fonte primaria)."""
    arquivo = _arquivo_lote(saida, numero)
    if not arquivo.exists():
        return None
    try:
        return ProcessoConsultado.model_validate_json(arquivo.read_text(encoding="utf-8"))
    except ValidationError:
        return None  # formato antigo ou corrompido: consulta de novo


def _ja_baixado(saida: Path, numero: str, so_origem: bool) -> bool:
    """Em disco e consultado em todos os indices pedidos agora."""
    gravado = ler_processo(saida, numero)
    pedidos = [tribunal_do_cnj(numero)] if so_origem else familia_do_cnj(numero)
    return gravado is not None and set(pedidos) <= set(gravado.consultados)


_CNJ = TypeAdapter(NumeroCNJ)


def cmd_lote(arquivo: Path, saida: Path | None, trabalhadores: int,
             so_origem: bool, as_json: bool):
    """SQLite e o padrao: cada execucao observa novamente a fonte.

    --saida preserva a exportacao JSON antiga, com a semantica antiga de pular
    JSONs ja completos. Em ambos os casos, cada chamada real a search() registra
    todas as respostas no SQLite append-only.
    """
    numeros, invalidos = [], []
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            numeros.append(_CNJ.validate_python(linha.strip()))
        except ValidationError:
            invalidos.append(linha.strip())
    numeros = list(dict.fromkeys(numeros))
    sem_tribunal = [n for n in numeros if tribunal_do_cnj(n) is None]
    pendentes = [
        n for n in numeros
        if tribunal_do_cnj(n) and (
            saida is None or not _ja_baixado(saida, n, so_origem)
        )
    ]
    print(f"{len(numeros)} processos; {len(pendentes)} a consultar"
          f"{' (so na origem)' if so_origem else ' (familia: origem + outros + superiores)'}",
          file=sys.stderr)
    resultado = consultar(ConsultaLote(
        numeros=pendentes, so_origem=so_origem, trabalhadores=trabalhadores
    ))
    destino_descr = str(saida or store.caminho_banco())
    resumo = ResumoLote(
        processos=len(numeros), em_disco=0, encontrados=0,
        sem_tribunal=sem_tribunal, invalidos=invalidos, saida=destino_descr,
    )
    validos = {}
    for item in resultado.values():
        if item.falhas:
            resumo.falhas.append(FalhaLote(
                processo=item.processo, indices=[f.indice for f in item.falhas]
            ))
            continue
        validos[so_digitos(item.processo)] = item
        if saida is not None:
            # Compatibilidade: exporta JSON apenas quando solicitado; cada
            # observacao vinda da rede ja foi armazenada no banco imutavel.
            destino = _arquivo_lote(saida, item.processo)
            destino.parent.mkdir(parents=True, exist_ok=True)
            temporario = destino.with_suffix(".json.tmp")
            temporario.write_text(item.para_disco(), encoding="utf-8")
            temporario.replace(destino)
    for n in numeros:
        if tribunal_do_cnj(n) is None:
            continue
        gravado = (ler_processo(saida, n) if saida is not None
                   else validos.get(so_digitos(n)))
        if gravado is None:
            continue
        resumo.em_disco += 1
        resumo.encontrados += gravado.encontrado
        outros = [t for t in gravado.tribunais if t != gravado.origem]
        if outros:
            resumo.tambem_em_outro_tribunal.append(
                PresencaForaDaOrigem(processo=gravado.processo, tambem_em=outros)
            )
    if as_json:
        print(resumo.model_dump_json(indent=2))
    else:
        print(f"{resumo.processos} processos; {resumo.em_disco} observados e "
              f"{resumo.encontrados} encontrados no DataJud, em {destino_descr}")
        if resumo.tambem_em_outro_tribunal:
            print(f"  {len(resumo.tambem_em_outro_tribunal)} tambem em outro tribunal")
        if resumo.sem_tribunal:
            print(f"  {len(resumo.sem_tribunal)} sem indice deduzivel")
        if resumo.invalidos:
            print(f"  {len(resumo.invalidos)} linhas invalidas")
        if resumo.falhas:
            print(f"  {len(resumo.falhas)} processos com indice sem resposta — "
                  "nao interpretados como ausentes")
    return 1 if resumo.falhas else 0


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
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
