# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest", "fastmcp>=2.0", "cyclopts>=3.0", "rich>=13.0", "requests"]
# ///
"""Família do número, lote e retomada: o que torna viável levantar um acervo grande.

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
        ("0600001-00.2024.6.22.0001", "tre-ro"),
        ("0000001-00.2024.9.13.0001", "tjmmg"),
        ("0000001-00.2024.3.00.0000", "stj"),
        ("0000001-00.2024.5.00.0000", "tst"),
        ("0126778-57.2022.1.00.0000", None),  # STF: sem índice na API pública
        ("0707486-63.3202.1.82.2000", None),  # número malformado no cadastro
        ("123", None),
    ],
)
def test_tribunal_de_origem_sai_do_numero(numero, indice):
    assert dj.tribunal_do_cnj(numero) == indice


def test_familia_cobre_o_estado_de_origem_e_os_superiores():
    assert dj.familia_do_cnj("7009511-71.2024.8.22.0001") == [
        "tjro", "tre-ro", "trt14", "trf1", "stj", "tst", "tse", "stm"]
    # TRT14 abrange RO e AC: os tribunais dos dois estados entram.
    trt = dj.familia_do_cnj("0000041-45.2011.5.14.0008")
    assert {"tjro", "tjac", "tre-ro", "tre-ac", "trf1"} <= set(trt)
    # Federal: a região não diz o estado; só o TRF e os superiores.
    assert dj.familia_do_cnj("0000774-14.2019.4.01.4102") == ["trf1", "stj", "tst", "tse", "stm"]
    assert "tjmmg" in dj.familia_do_cnj("1000000-00.2024.8.13.0024")
    assert dj.familia_do_cnj("0126778-57.2022.1.00.0000") == []


def _hit(numero: str, indice: str, grau: str = "G1") -> dict:
    return {"_index": f"api_publica_{indice}", "_source": {"numeroProcesso": numero, "grau": grau, "movimentos": []}}


def test_lote_procura_na_familia_grava_cru_e_retoma(monkeypatch, tmp_path):
    chamadas: list[str] = []
    tjro = "70095117120248220001"

    def search(body, tribunal="tjro", **_):
        chamadas.append(tribunal)
        numeros = body["query"]["terms"]["numeroProcesso"]
        hits = []
        if tribunal == "tjro" and tjro in numeros:
            hits = [_hit(tjro, "tjro", "G1"), _hit(tjro, "tjro", "G2")]
        if tribunal == "stj" and tjro in numeros:
            hits = [_hit(tjro, "stj", "SUP")]  # subiu ao STJ com o mesmo número
        return {"hits": {"total": {"value": len(hits)}, "hits": hits}}

    monkeypatch.setattr(dj, "search", search)
    lista = tmp_path / "numeros.txt"
    lista.write_text(
        f"7009511-71.2024.8.22.0001\n{tjro}\n"  # duplicata sem máscara
        "7000000-00.2024.8.22.0001\n0707486-63.3202.1.82.2000\n",
        encoding="utf-8",
    )
    saida = tmp_path / "datajud"

    assert dj.cmd_lote(lista, saida, trabalhadores=2, so_origem=False, as_json=True) == 0
    assert sorted(set(chamadas)) == sorted(dj.familia_do_cnj(tjro)), "um índice da família por consulta"
    assert len(chamadas) == len(dj.familia_do_cnj(tjro)), "os dois números do TJRO vão juntos"
    bruto = json.loads((saida / "tjro" / f"{tjro}.json").read_text(encoding="utf-8"))
    assert [h["_index"] for h in bruto["hits"]] == [
        "api_publica_stj", "api_publica_tjro", "api_publica_tjro"], "o hit cru é preservado"
    gravado = dj.ler_processo(saida, tjro)
    assert gravado.tribunais == ["stj", "tjro"]
    assert set(gravado.consultados) == set(dj.familia_do_cnj(tjro))
    assert gravado.processo == "7009511-71.2024.8.22.0001"
    vazio = dj.ler_processo(saida, "7000000-00.2024.8.22.0001")
    assert vazio is not None and not vazio.encontrado, "não encontrado também fica em disco"

    chamadas.clear()
    assert dj.cmd_lote(lista, saida, trabalhadores=2, so_origem=False, as_json=True) == 0
    assert chamadas == [], "segunda execução lê do disco"
    assert dj.cmd_lote(lista, saida, trabalhadores=2, so_origem=True, as_json=True) == 0
    assert chamadas == [], "o que já foi consultado na família cobre a origem"


def test_indice_que_falha_nao_vira_ausencia(monkeypatch, tmp_path):
    def search(body, tribunal="tjro", **_):
        if tribunal == "stj":
            raise RuntimeError("HTTP 504: NSX LB")
        return {"hits": {"total": {"value": 0}, "hits": []}}

    monkeypatch.setattr(dj, "search", search)
    lista = tmp_path / "numeros.txt"
    lista.write_text("7009511-71.2024.8.22.0001\n", encoding="utf-8")

    assert dj.cmd_lote(lista, tmp_path / "datajud", trabalhadores=1, so_origem=False, as_json=True) == 1
    assert not (tmp_path / "datajud" / "tjro").exists(), "nada vai a disco enquanto um índice não responde"


def test_lote_truncado_e_erro(monkeypatch, tmp_path):
    monkeypatch.setattr(
        dj, "search", lambda body, tribunal="tjro", **_: {"hits": {"total": {"value": 5000}, "hits": []}}
    )
    lista = tmp_path / "numeros.txt"
    lista.write_text("7009511-71.2024.8.22.0001\n", encoding="utf-8")

    assert dj.cmd_lote(lista, tmp_path / "datajud", trabalhadores=1, so_origem=True, as_json=True) == 1
    assert not (tmp_path / "datajud" / "tjro").exists(), "truncado não vira 'não encontrado'"


def test_modelos_de_entrada_validam_e_normalizam():
    entrada = dj.ConsultaLote(numeros=["70095117120248220001"], trabalhadores=2)
    assert entrada.numeros == ["7009511-71.2024.8.22.0001"]
    with pytest.raises(dj.ValidationError):
        dj.ConsultaLote(numeros=["123"])
    with pytest.raises(dj.ValidationError):
        dj.ConsultaLote(numeros=["70095117120248220001"], trabalhadores=0)


def test_lote_separa_linha_invalida(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        dj, "search", lambda body, tribunal="tjro", **_: {"hits": {"total": {"value": 0}, "hits": []}}
    )
    lista = tmp_path / "numeros.txt"
    lista.write_text("7009511-71.2024.8.22.0001\nprocesso sem número\n\n", encoding="utf-8")

    assert dj.cmd_lote(lista, tmp_path / "datajud", trabalhadores=1, so_origem=True, as_json=True) == 0
    resumo = dj.ResumoLote.model_validate_json(capsys.readouterr().out)
    assert resumo.invalidos == ["processo sem número"]
    assert resumo.processos == 1 and resumo.em_disco == 1 and resumo.encontrados == 0


def test_mcp_procura_na_familia_e_marca_o_tribunal(monkeypatch):
    numero = "00007741420194014102"
    vistos: list[str] = []

    def search(body, tribunal="tjro", **_):
        vistos.append(tribunal)
        hits = [_hit(numero, tribunal, "G2" if tribunal == "trf1" else "SUP")] if tribunal in ("trf1", "stj") else []
        return {"hits": {"total": {"value": len(hits)}, "hits": hits}}

    monkeypatch.setattr(dj, "search", search)
    saida = mod.datajud_processo("0000774-14.2019.4.01.4102")
    assert sorted(vistos) == sorted(dj.familia_do_cnj(numero))
    assert sorted(d["tribunal"] for d in saida["documentos"]) == ["STJ", "TRF1"]

    vistos.clear()
    mod.datajud_processo("0000774-14.2019.4.01.4102", tribunal="trf1")
    assert vistos == ["trf1"], "tribunal explícito consulta só ele"


def test_mcp_so_origem_consulta_so_o_tribunal_de_origem(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DATAJUD_SQLITE", str(tmp_path / "datajud.sqlite"))
    vistos: list[str] = []

    def search(body, tribunal="tjro", **_):
        vistos.append(tribunal)
        return {"hits": {"total": {"value": 0}, "hits": []}}

    monkeypatch.setattr(dj, "search", search)
    mod.datajud_processo("0000774-14.2019.4.01.4102", so_origem=True)
    assert vistos == ["trf1"]

    vistos.clear()
    mod.app(["processo", "0000774-14.2019.4.01.4102", "--so-origem", "--json"], result_action="return_value")
    assert vistos == ["trf1"], "a CLI da MCP aceita --so-origem, como a SKILL.md promete"
