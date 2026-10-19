#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
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

Dependencias: cyclopts (CLI). O acesso HTTP usa apenas a stdlib.

Modos:
    processo <CNJ>              capa + movimentacoes de um processo (todos os graus)
    buscar   [filtros]          lista processos que casam com os filtros
    contar   [filtros]          apenas o total real (track_total_hits)
    facetas  [filtros] --por X  agregacao (quantos por classe/assunto/orgao/grau)
    codigos  <termo> --por X    descobre codigos de classe/assunto por nome

Rode `python datajud.py -h` ou `python datajud.py <modo> -h` para detalhes.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import cyclopts
from cyclopts import Parameter

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
    rc = d.get("error", {}).get("root_cause", [])
    return any("rejected_execution" in (c.get("type", "")) for c in rc)


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
                d = json.loads(r.read().decode("utf-8"))
            if _is_es_rejection(d):
                ultimo_erro = "es_rejected_execution_exception (fila do ES cheia)"
                if n < tentativas:
                    time.sleep(espera)
                    espera = min(espera * 2, 30)
                    continue
                raise RuntimeError(ultimo_erro)
            return d
        except urllib.error.HTTPError as e:
            corpo = ""
            try:
                corpo = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            if e.code == 429 and n < tentativas:
                ultimo_erro = f"HTTP 429 (rate limit): {corpo}"
                time.sleep(espera)
                espera = min(espera * 2, 30)
                continue
            if e.code == 401:
                raise RuntimeError(
                    "HTTP 401: a chave publica provavelmente foi trocada pelo CNJ. "
                    "Pegue a atual em https://datajud-wiki.cnj.jus.br/api-publica/acesso/ "
                    "e atualize APIKEY no topo deste script.") from e
            raise RuntimeError(f"HTTP {e.code}: {corpo}") from e
        except urllib.error.URLError as e:
            ultimo_erro = f"rede: {e.reason}"
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


# Segmento J.TR do numero CNJ (Res. CNJ 65/2008): J=8 estadual (TR = UF),
# 5 trabalho, 4 federal, 3 STJ, 1 STF. Um acervo de orgao publico mistura
# TJ, TRT, TRF e tribunais superiores; deduzir o indice evita perguntar ao
# TJRO por processo que nunca esteve la.
_UF_TJ = {
    "01": "ac", "02": "al", "03": "ap", "04": "am", "05": "ba", "06": "ce",
    "07": "dft", "08": "es", "09": "go", "10": "ma", "11": "mt", "12": "ms",
    "13": "mg", "14": "pa", "15": "pb", "16": "pr", "17": "pe", "18": "pi",
    "19": "rj", "20": "rn", "21": "rs", "22": "ro", "23": "rr", "24": "sc",
    "25": "se", "26": "sp", "27": "to",
}


def tribunal_do_cnj(n):
    """Sigla do indice DataJud deduzida do numero CNJ, ou None se nao der."""
    d = so_digitos(n)
    if len(d) != 20:
        return None
    j, tr = d[13], d[14:16]
    if j == "8":
        return f"tj{_UF_TJ[tr]}" if tr in _UF_TJ else None
    if j == "5":
        return f"trt{int(tr)}"
    if j == "4":
        return f"trf{int(tr)}"
    # Tribunal superior tem TR 00; J=1 com outro TR é número malformado no cadastro.
    return {"3": "stj", "1": "stf"}.get(j) if tr == "00" else None


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
def cmd_processo(numero: str, tribunal: str, movimentos: bool, as_json: bool):
    nr = so_digitos(numero)
    body = {
        "size": 50,
        "query": {"match": {"numeroProcesso": nr}},
        "sort": [{"grau.keyword": "asc"}],
    }
    d = search(body, tribunal=tribunal)
    hits = d.get("hits", {}).get("hits", [])
    if not hits:
        print(f"Nenhum processo {cnj(nr)} encontrado em {tribunal.upper()}.",
              file=sys.stderr)
        return 1

    if as_json:
        out = []
        for h in hits:
            src = h["_source"]
            out.append({
                "grau": src.get("grau"),
                "classe": src.get("classe"),
                "assuntos": src.get("assuntos"),
                "orgaoJulgador": src.get("orgaoJulgador"),
                "dataAjuizamento": src.get("dataAjuizamento"),
                "ultimaAtualizacao": src.get("dataHoraUltimaAtualizacao"),
                "movimentos": src.get("movimentos") if movimentos else "(omitido; use --movimentos)",
            })
        print(json.dumps({"processo": cnj(nr), "tribunal": tribunal.upper(),
                          "documentos": out}, ensure_ascii=False, indent=2))
        return 0

    print(f"Processo {cnj(nr)} — {tribunal.upper()} — {len(hits)} registro(s) de grau")
    print("=" * 92)
    for h in hits:
        src = h["_source"]
        print(f"\n### {grau_label(src.get('grau'))} — {classe_str(src)}")
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
    query = montar_query(filtros)
    body = {
        "size": tamanho,
        "track_total_hits": True,
        "query": query,
        "_source": CAPA_FIELDS,
    }
    if recentes:
        body["sort"] = [{"dataAjuizamento": "desc"}]

    d = search(body, tribunal=filtros.tribunal)
    total = d.get("hits", {}).get("total", {}).get("value", 0)
    hits = d.get("hits", {}).get("hits", [])

    if as_json:
        out = []
        for h in hits:
            src = h["_source"]
            out.append({
                "numeroProcesso": cnj(src.get("numeroProcesso", "")),
                "grau": src.get("grau"),
                "classe": src.get("classe"),
                "assuntos": src.get("assuntos"),
                "orgaoJulgador": (src.get("orgaoJulgador") or {}).get("nome"),
                "dataAjuizamento": src.get("dataAjuizamento"),
            })
        print(json.dumps({"tribunal": filtros.tribunal.upper(), "total": total,
                          "retornados": len(out), "resultados": out},
                         ensure_ascii=False, indent=2))
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
    body = {"size": 0, "track_total_hits": True, "query": montar_query(filtros)}
    d = search(body, tribunal=filtros.tribunal)
    total = d.get("hits", {}).get("total", {}).get("value", 0)
    if as_json:
        print(json.dumps({"tribunal": filtros.tribunal.upper(), "total": total},
                         ensure_ascii=False))
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
    body = {
        "size": 0,
        "track_total_hits": True,
        "query": montar_query(filtros),
        "aggs": {"f": {"terms": {"field": campo, "size": limite}}},
    }
    d = search(body, tribunal=filtros.tribunal)
    total = d.get("hits", {}).get("total", {}).get("value", 0)
    buckets = d.get("aggregations", {}).get("f", {}).get("buckets", [])
    if as_json:
        print(json.dumps({"tribunal": filtros.tribunal.upper(), "total": total,
                          "por": por,
                          "buckets": [{"chave": b["key"], "qtd": b["doc_count"]}
                                      for b in buckets]},
                         ensure_ascii=False, indent=2))
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
    body = {
        "size": 0,
        "query": {"match": {match_field: termo}},
        "aggs": {
            "nomes": {
                "terms": {"field": campo_nome, "size": limite},
                "aggs": {"cod": {"terms": {"field": campo_cod, "size": 1}}},
            }
        },
    }
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
        print(json.dumps({"por": por, "termo": termo,
                          "itens": [{"codigo": c, "nome": n, "qtd": q}
                                    for c, n, q in linhas]},
                         ensure_ascii=False, indent=2))
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


def _arquivo_lote(saida: Path, numero: str, tribunal: str) -> Path:
    return saida / tribunal / f"{so_digitos(numero)}.json"


def baixar_lote(numeros: list[str], tribunal: str, saida: Path) -> int:
    """Uma requisicao para ate LOTE processos do mesmo indice; grava um arquivo por
    processo, inclusive o vazio (nao encontrado), para nao perguntar de novo."""
    d = search(
        {"size": LOTE * 10,
         "query": {"terms": {"numeroProcesso": [so_digitos(n) for n in numeros]}}},
        tribunal=tribunal,
    )
    hits = d.get("hits", {}).get("hits", [])
    total = d.get("hits", {}).get("total", {}).get("value", 0)
    if total > len(hits):
        raise RuntimeError(f"resposta truncada em {tribunal}: {len(hits)} de {total}")
    por_numero = {so_digitos(n): [] for n in numeros}
    for h in hits:
        por_numero.setdefault(h["_source"].get("numeroProcesso", ""), []).append(h)
    for n in numeros:
        arquivo = _arquivo_lote(saida, n, tribunal)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(
            json.dumps({"processo": cnj(n), "tribunal": tribunal,
                        "hits": por_numero[so_digitos(n)]}, ensure_ascii=False),
            encoding="utf-8",
        )
    return len(numeros)


def cmd_lote(arquivo: Path, saida: Path, trabalhadores: int, as_json: bool):
    numeros = list(dict.fromkeys(
        cnj(linha.strip()) for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if so_digitos(linha)))
    sem_tribunal = [n for n in numeros if tribunal_do_cnj(n) is None]
    pendentes: dict[str, list[str]] = {}
    for n in numeros:
        t = tribunal_do_cnj(n)
        if t and not _arquivo_lote(saida, n, t).exists():
            pendentes.setdefault(t, []).append(n)
    lotes = [(t, ns[i:i + LOTE]) for t, ns in pendentes.items() for i in range(0, len(ns), LOTE)]
    feitos, falhas = len(numeros) - sum(len(ns) for _, ns in lotes) - len(sem_tribunal), []
    with ThreadPoolExecutor(max(1, trabalhadores)) as pool:
        futuros = {pool.submit(baixar_lote, ns, t, saida): (t, ns) for t, ns in lotes}
        for futuro in as_completed(futuros):
            t, ns = futuros[futuro]
            try:
                feitos += futuro.result()
            except RuntimeError as e:
                falhas.append({"tribunal": t, "processos": len(ns), "erro": str(e)[:200]})
            print(f"\r{feitos}/{len(numeros)} processos em disco", end="", file=sys.stderr)
    print(file=sys.stderr)
    encontrados = sum(
        1 for n in numeros if tribunal_do_cnj(n)
        and _arquivo_lote(saida, n, tribunal_do_cnj(n)).exists()
        and json.loads(_arquivo_lote(saida, n, tribunal_do_cnj(n)).read_text(encoding="utf-8"))["hits"])
    resumo = {"processos": len(numeros), "em_disco": feitos, "encontrados": encontrados,
              "sem_tribunal": sem_tribunal, "falhas": falhas, "saida": str(saida)}
    if as_json:
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
    else:
        print(f"{len(numeros)} processos; {feitos} em disco ({encontrados} encontrados no DataJud) em {saida}")
        if sem_tribunal:
            print(f"  sem tribunal deduzivel pelo numero: {', '.join(sem_tribunal)}")
        for f in falhas:
            print(f"  falha em {f['tribunal']} ({f['processos']} processos): {f['erro']} — rode de novo")
    return 1 if falhas else 0


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
@dataclass
class Filtros:
    """Filtros comuns aos modos de busca/contagem/agregacao."""

    tribunal: str = DEFAULT_TRIBUNAL
    """sigla do indice (padrao tjro). Ex.: stj, trf1, tjsp, stf."""
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
FiltrosArg = Annotated[Filtros, Parameter(name="*")]

app = cyclopts.App(
    name="datajud",
    help="Consulta metadados processuais na API Publica do DataJud (CNJ).",
)


@app.command
def processo(
    numero: str,
    *,
    tribunal: str | None = None,
    movimentos: bool = False,
    json: AsJson = False,
) -> int:
    """Capa + movimentacoes de um processo (todos os graus).

    Parameters
    ----------
    numero
        numero do processo (com ou sem mascara CNJ).
    tribunal
        sigla do indice; omitida, sai do numero CNJ (J.TR), e tjro se nao der.
    movimentos
        lista a linha completa de movimentacao.
    json
        emite JSON em vez do relatorio legivel.
    """
    alvo = tribunal or tribunal_do_cnj(numero) or DEFAULT_TRIBUNAL
    return cmd_processo(numero, alvo, movimentos, json)


@app.command
def lote(
    arquivo: Path,
    *,
    saida: Path = Path("datajud"),
    trabalhadores: int = 4,
    json: AsJson = False,
) -> int:
    """Baixa muitos processos de uma vez e guarda a resposta crua de cada um.

    O tribunal sai do numero CNJ; cada tribunal vai em consultas de ate 100
    processos. Grava `<saida>/<tribunal>/<numero>.json` (capa e movimentos de
    todos os graus, ou lista vazia se nao encontrado) e pula o que ja esta em
    disco, entao rodar de novo retoma de onde parou.

    Parameters
    ----------
    arquivo
        texto com um numero de processo por linha (com ou sem mascara).
    saida
        diretorio dos JSON (padrao ./datajud).
    trabalhadores
        consultas simultaneas (padrao 4).
    json
        emite o resumo em JSON.
    """
    return cmd_lote(arquivo, saida, trabalhadores, json)


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


def main(tokens=None) -> int:
    try:
        return app(tokens) or 0
    except RuntimeError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
