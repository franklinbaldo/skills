# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest", "fastmcp>=2.0", "cyclopts>=3.0", "rich>=13.0", "requests"]
# ///
"""Lote e tribunal pelo número CNJ: as duas coisas que tornam acervo grande viável.

Nenhum teste toca a rede: `dj.search` é substituído por monkeypatch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud_mcp as mod  # noqa: E402

import datajud as dj  # noqa: E402


@pytest.mark.parametrize(
    ("numero", "indice"),
    [
        ("7009511-71.2024.8.22.0001", "tjro"),
        ("00000414520115140008", "trt14"),
        ("0000774-14.2019.4.01.4102", "trf1"),
        ("1000000-00.2024.8.26.0100", "tjsp"),
        ("0000001-00.2024.8.07.0001", "tjdft"),
        ("0126778-57.2022.1.00.0000", "stf"),
        ("0000001-00.2024.3.00.0000", "stj"),
        ("0707486-63.3202.1.82.2000", None),  # número malformado no cadastro: J=1, TR=82
        ("123", None),
    ],
)
def test_tribunal_sai_do_numero(numero, indice):
    assert dj.tribunal_do_cnj(numero) == indice


def _hit(numero: str, grau: str = "G1") -> dict:
    return {"_source": {"numeroProcesso": numero, "grau": grau, "movimentos": []}}


def test_lote_agrupa_por_tribunal_grava_cru_e_retoma(monkeypatch, tmp_path):
    chamadas: list[tuple[str, list[str]]] = []

    def search(body, tribunal="tjro", **_):
        numeros = body["query"]["terms"]["numeroProcesso"]
        chamadas.append((tribunal, numeros))
        # o primeiro processo do TJRO tem dois graus; o segundo não existe
        hits = [_hit(numeros[0], "G1"), _hit(numeros[0], "G2")] if tribunal == "tjro" else [
            _hit(n) for n in numeros]
        return {"hits": {"total": {"value": len(hits)}, "hits": hits}}

    monkeypatch.setattr(dj, "search", search)
    lista = tmp_path / "numeros.txt"
    lista.write_text(
        "7009511-71.2024.8.22.0001\n70095117120248220001\n"  # duplicata sem máscara
        "7000000-00.2024.8.22.0001\n0000774-14.2019.4.01.4102\n0707486-63.3202.1.82.2000\n",
        encoding="utf-8",
    )
    saida = tmp_path / "datajud"

    assert dj.cmd_lote(lista, saida, trabalhadores=2, as_json=True) == 0
    assert sorted(t for t, _ in chamadas) == ["tjro", "trf1"], "uma consulta por tribunal"
    gravado = json.loads((saida / "tjro" / "70095117120248220001.json").read_text(encoding="utf-8"))
    assert [h["_source"]["grau"] for h in gravado["hits"]] == ["G1", "G2"]
    vazio = json.loads((saida / "tjro" / "70000000020248220001.json").read_text(encoding="utf-8"))
    assert vazio["hits"] == [], "não encontrado também fica em disco"

    chamadas.clear()
    assert dj.cmd_lote(lista, saida, trabalhadores=2, as_json=True) == 0
    assert chamadas == [], "segunda execução lê do disco"


def test_lote_truncado_e_erro_e_nao_grava(monkeypatch, tmp_path):
    monkeypatch.setattr(
        dj, "search", lambda body, tribunal="tjro", **_: {"hits": {"total": {"value": 5000}, "hits": []}}
    )
    lista = tmp_path / "numeros.txt"
    lista.write_text("7009511-71.2024.8.22.0001\n", encoding="utf-8")

    assert dj.cmd_lote(lista, tmp_path / "datajud", trabalhadores=1, as_json=True) == 1
    assert not (tmp_path / "datajud" / "tjro").exists(), "truncado não vira 'não encontrado'"


def test_mcp_deduz_o_tribunal_do_numero(monkeypatch):
    vistos: list[str] = []

    def search(body, tribunal="tjro", **_):
        vistos.append(tribunal)
        return {"hits": {"hits": []}}

    monkeypatch.setattr(dj, "search", search)
    mod.datajud_processo("0000774-14.2019.4.01.4102")
    mod.datajud_processo("0000774-14.2019.4.01.4102", tribunal="tjro")

    assert vistos == ["trf1", "tjro"]
