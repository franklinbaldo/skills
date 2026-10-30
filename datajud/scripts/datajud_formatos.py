# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.6",
# ]
# ///
"""Campos da capa, códigos de ruído, formatação de datas e rótulos, e a query de busca."""

from __future__ import annotations

import re

from datajud_cnj import so_digitos

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
