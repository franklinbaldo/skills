# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.6",
# ]
# ///
"""Número CNJ: dígitos, máscara, tribunal de origem e família de tribunais."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator


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
