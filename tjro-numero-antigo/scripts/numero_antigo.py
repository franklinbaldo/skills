#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
# ]
# ///
"""Converte número antigo de processo do TJRO (FFF.AAAA.SSSSSS-D) para o APPG e o CNJ, e procura no DataJud.

Aceita as grafias que aparecem em matrícula, ofício e sistema: com ou sem
pontuação, ano com 4 ou 2 dígitos (`006.01.000138-2`), sequencial sem os zeros
à esquerda (`006.2001.138-2`) e sem o dígito verificador (`006.2001.000138`;
aí gera os 10 candidatos). O foro (FFF) é obrigatório: sem ele não há como
saber a comarca.

Saídas por número:

- APPG ("Número Processo Antigo"): 14 dígitos sem pontuação, FFFAAAASSSSSSD.
- CNJ: sequencial = SSSSSS + D (7 dígitos), origem = 0FFF, dígito verificador
  pelo módulo 97 (Res. CNJ 65/2008).

Com --datajud, todos os candidatos vão numa única consulta `terms` à API
pública do DataJud (TJRO), com nova tentativa em HTTP 429.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Annotated

from cyclopts import App, Parameter

app = App(name="numero-antigo", help=__doc__)

# Chave pública da API do DataJud, a mesma para todos
# (https://datajud-wiki.cnj.jus.br/api-publica/acesso/). Com HTTP 401, pegue a atual na wiki.
APIKEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
URL = "https://api-publica.datajud.cnj.jus.br/api_publica_tjro/_search"
PIVO_ANO = 30  # ano com 2 dígitos: até 30 → 20xx; acima → 19xx

# Foro (FFF) → comarca, como no seletor do APPG em 03/11/2026.
COMARCAS = {
    "001": "Porto Velho",
    "002": "Ariquemes",
    "003": "Jaru",
    "004": "Ouro Preto do Oeste",
    "005": "Ji-Paraná",
    "006": "Presidente Médici",
    "007": "Cacoal",
    "008": "Espigão do Oeste",
    "009": "Pimenta Bueno",
    "010": "Rolim de Moura",
    "011": "Alvorada do Oeste",
    "012": "Colorado do Oeste",
    "013": "Cerejeiras",
    "014": "Vilhena",
    "015": "Guajará-Mirim",
    "016": "Costa Marques",
    "017": "Alta Floresta",
    "018": "Santa Luzia do Oeste",
    "019": "Machadinho do Oeste",
    "020": "Nova Brasilândia do Oeste",
    "021": "Buritis",
    "022": "São Miguel do Guaporé",
    "023": "São Francisco do Guaporé",
}

PONTUADO = re.compile(r"^\s*(\d{3})[.\-/ ](\d{2}|\d{4})[.\-/ ](\d{1,6})(?:[-.](\d))?\s*$")
CORRIDO = re.compile(r"^\s*(\d{3})(\d{4})(\d{6})(\d)?\s*$")


def ler_antigo(texto: str) -> tuple[str, str, str, str | None]:
    """(foro, ano com 4 dígitos, sequencial com 6, dígito ou None)."""
    m = PONTUADO.match(texto) or CORRIDO.match(texto.replace(".", "").replace("-", ""))
    if not m:
        raise ValueError(f"não é número antigo do TJRO (FFF.AAAA.SSSSSS-D): {texto!r}")
    foro, ano, seq, dig = m.groups()
    if len(ano) == 2:
        ano = ("20" if int(ano) <= PIVO_ANO else "19") + ano
    return foro, ano, seq.zfill(6), dig


def cnj(seq7: str, ano: str, origem: str) -> str:
    """Os 20 dígitos do CNJ, com o dígito verificador pelo módulo 97."""
    dv = 98 - int(f"{seq7}{ano}822{origem}00") % 97
    return f"{seq7}{dv:02d}{ano}822{origem}"


def mascara(n: str) -> str:
    return f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13]}.{n[14:16]}.{n[16:]}"


def converter(texto: str) -> dict:
    foro, ano, seq, dig = ler_antigo(texto)
    digitos = [dig] if dig is not None else [str(d) for d in range(10)]
    candidatos = [
        {
            "antigo": f"{foro}.{ano}.{seq}-{d}",
            "appg": f"{foro}{ano}{seq}{d}",
            "cnj": mascara(cnj(seq + d, ano, f"0{foro}")),
        }
        for d in digitos
    ]
    return {
        "entrada": texto.strip(),
        "comarca": COMARCAS.get(foro, f"foro {foro} desconhecido"),
        "digito_informado": dig is not None,
        "candidatos": candidatos,
    }


def consultar_datajud(numeros: list[str]) -> list[dict]:
    consulta = {
        "size": max(len(numeros), 10),
        "query": {"terms": {"numeroProcesso": numeros}},
        "_source": ["numeroProcesso", "classe.nome", "orgaoJulgador.nome", "dataAjuizamento", "grau"],
    }
    corpo = json.dumps(consulta).encode()
    cabecalhos = {"Authorization": f"APIKey {APIKEY}", "Content-Type": "application/json"}
    for tentativa in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, data=corpo, headers=cabecalhos), timeout=60) as r:
                return [h["_source"] for h in json.load(r)["hits"]["hits"]]
        except urllib.error.HTTPError as erro:
            if erro.code != 429:
                raise
            time.sleep(5 * (tentativa + 1))
    raise RuntimeError("DataJud: HTTP 429 persistente; tente de novo em alguns minutos")


def anexar_datajud(linhas: list[dict], todas_origens: bool) -> None:
    alvo: dict[str, dict] = {}
    for linha in linhas:
        if "erro" in linha:
            continue
        linha["datajud"] = []
        for c in linha["candidatos"]:
            foro, ano, seq, d = ler_antigo(c["antigo"])
            alvo[cnj(seq + d, ano, f"0{foro}")] = linha
            if todas_origens:
                for o in range(1, 100):
                    alvo.setdefault(cnj(seq + d, ano, f"{o:04d}"), linha)
    numeros = list(alvo)
    for i in range(0, len(numeros), 1000):
        for achado in consultar_datajud(numeros[i : i + 1000]):
            alvo[achado["numeroProcesso"]]["datajud"].append(
                {
                    "cnj": mascara(achado["numeroProcesso"]),
                    "classe": (achado.get("classe") or {}).get("nome"),
                    "orgao": (achado.get("orgaoJulgador") or {}).get("nome"),
                    "ajuizamento": achado.get("dataAjuizamento"),
                    "grau": achado.get("grau"),
                }
            )


@app.default
def main(
    numeros: Annotated[
        list[str] | None,
        Parameter(help="Números antigos; sem eles, lê um por linha do stdin."),
    ] = None,
    *,
    datajud: Annotated[bool, Parameter(help="Procura os CNJ no DataJud (TJRO), em lote.")] = False,
    todas_origens: Annotated[
        bool,
        Parameter(help="No DataJud, tenta também as origens 0001 a 0099 (processo redistribuído)."),
    ] = False,
    json_saida: Annotated[bool, Parameter(name="--json", help="Saída em JSON.")] = False,
) -> int:
    entradas = numeros or [linha for linha in sys.stdin.read().splitlines() if linha.strip()]
    linhas: list[dict] = []
    for texto in entradas:
        try:
            linhas.append(converter(texto))
        except ValueError as erro:
            linhas.append({"entrada": texto.strip(), "erro": str(erro)})

    if datajud:
        anexar_datajud(linhas, todas_origens)

    if json_saida:
        print(json.dumps(linhas, ensure_ascii=False, indent=2))
    else:
        for linha in linhas:
            if "erro" in linha:
                print(f"ERRO {linha['entrada']}: {linha['erro']}")
                continue
            aviso = "" if linha["digito_informado"] else "  (sem dígito: 10 candidatos)"
            print(f"{linha['entrada']}  [{linha['comarca']}]{aviso}")
            for c in linha["candidatos"]:
                print(f"   {c['antigo']}  APPG {c['appg']}  CNJ {c['cnj']}")
            if datajud:
                if not linha["datajud"]:
                    print("   DataJud: não encontrado")
                for d in linha["datajud"]:
                    print(f"   DataJud: {d['cnj']} | {d['classe']} | {d['orgao']} | {d['ajuizamento']} | {d['grau']}")
    return 1 if any("erro" in linha for linha in linhas) else 0


if __name__ == "__main__":
    raise SystemExit(app())
