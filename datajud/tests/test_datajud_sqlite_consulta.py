# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "cyclopts>=3.0", "pydantic>=2.6"]
# ///
"""Consulta gravando no acervo: `search`, `lote` e as saidas da CLI; HTTP simulado."""

from __future__ import annotations

import io
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud_api as dj_api  # noqa: E402
import datajud_store as store  # noqa: E402
from datajud_dados_teste import (  # noqa: E402
    ANTIGOS,
    NUMERO,
    REQUISICAO,
    hit,
    mov,
    registrar,
    resposta,
    tabelas,
)

import datajud as dj  # noqa: E402


def test_search_realmente_registra_toda_resposta_sem_configuracao_extra(monkeypatch, tmp_path):
    banco = tmp_path / "acervo.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))
    recebidas = [resposta(hit(score=1.0)), resposta(hit(score=2.0))]

    class HTTPResposta:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(self.body).encode("utf-8")

    monkeypatch.setattr(dj.urllib.request, "urlopen",
                        lambda *_a, **_kw: HTTPResposta(recebidas.pop(0)))
    assert dj.search(REQUISICAO, tribunal="tjro")["hits"]
    assert dj.search(REQUISICAO, tribunal="tjro")["hits"]
    t = tabelas(banco)
    assert (t["consultas"], t["registros"], t["observacoes"], t["vistas"]) == (2, 1, 1, 1)


def test_search_registra_falha_sem_criar_falso_nao_encontrado(monkeypatch, tmp_path):
    banco = tmp_path / "erros.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))

    def erro(*_a, **_kw):
        raise HTTPError(
            "https://example.test", 503, "service unavailable", {}, io.BytesIO(b"gateway")
        )

    monkeypatch.setattr(dj.urllib.request, "urlopen", erro)
    with pytest.raises(RuntimeError, match="HTTP 503"):
        dj.search({"query": {"match_all": {}}}, tribunal="tjro", tentativas=1)

    t = tabelas(banco)
    assert t["consultas"] == 1 and t["observacoes"] == 0
    with sqlite3.connect(banco) as con:
        assert con.execute("SELECT resultado FROM consultas").fetchone()[0] == "erro"


def test_lote_padrao_nao_exporta_json_e_observa_outra_vez(monkeypatch, tmp_path):
    banco = tmp_path / "acervo.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))
    entrada = tmp_path / "processos.txt"
    entrada.write_text("7009511-71.2024.8.22.0001\n", encoding="utf-8")

    class HTTPResposta:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(resposta(hit())).encode()

    monkeypatch.setattr(dj.urllib.request, "urlopen",
                        lambda *_a, **_kw: HTTPResposta())
    assert dj.cmd_lote(entrada, None, 1, True, True) == 0
    assert dj.cmd_lote(entrada, None, 1, True, True) == 0
    t = tabelas(banco)
    assert (t["consultas"], t["registros"], t["observacoes"], t["vistas"], t["movimentos"]) == (
        2, 1, 1, 1, 2)
    assert not list(tmp_path.rglob("*.json"))


def test_cli_estado_historico_e_banco_emitem_os_modelos(monkeypatch, tmp_path, capsys):
    banco = tmp_path / "acervo.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))
    registrar(banco, hit())

    assert dj.app(result_action="return_value", tokens=["estado", NUMERO, "--json"]) == 0
    saida = store.EstadoProcesso.model_validate_json(capsys.readouterr().out)
    assert len(saida.registros[0].movimentos) == 2

    assert dj.app(result_action="return_value", tokens=["historico", NUMERO, "--json"]) == 0
    assert store.HistoricoProcesso.model_validate_json(capsys.readouterr().out).registros

    assert dj.app(result_action="return_value", tokens=["banco", "--json"]) == 0
    assert store.Estatisticas.model_validate_json(capsys.readouterr().out)["movimentos"] == 2

    assert dj.app(result_action="return_value", tokens=["estado", "0000000-00.2024.8.22.0001"]) == 1


def test_roteamento_df_e_justica_militar():
    assert dj.tribunal_do_cnj("0000001-00.2024.6.07.0001") == "tre-dft"
    assert "tre-dft" in dj.familia_do_cnj("0000001-00.2024.8.07.0001")
    assert "tre-df" not in dj.familia_do_cnj("0000001-00.2024.8.07.0001")
    assert dj.tribunal_do_cnj("0000001-00.2024.7.01.0001") == "stm"


def test_numero_sem_indice_nao_e_ausencia_confirmada(monkeypatch, tmp_path, capsys):
    """Número do STF: nenhum índice consultado, logo nada foi observado."""
    import datajud_mcp as mod

    monkeypatch.setenv("DATAJUD_SQLITE", str(tmp_path / "datajud.sqlite"))
    monkeypatch.setattr(dj_api, "search", lambda *a, **k: pytest.fail("não deveria consultar"))
    saida = mod.datajud_processo("0126778-57.2022.1.00.0000")
    assert saida.encontrado is False and saida.completo is False

    assert dj.cmd_processo("0126778-57.2022.1.00.0000", None, False, False) == 1
    assert "incompleta" in capsys.readouterr().err


def test_falha_de_indice_nao_vira_nenhum_encontrado(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DATAJUD_SQLITE", str(tmp_path / "datajud.sqlite"))

    def search(body, tribunal="tjro", **_):
        if tribunal == "stj":
            raise RuntimeError("HTTP 504: NSX LB")
        return {"hits": {"total": {"value": 0}, "hits": []}}

    monkeypatch.setattr(dj_api, "search", search)
    assert dj.cmd_processo("7009511-71.2024.8.22.0001", None, False, False) == 1
    erro = capsys.readouterr().err
    assert "incompleta" in erro and "Nenhum processo" not in erro


def test_novidades_separa_linha_de_base_marco_e_rotina(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit())
    base = store.novidades("2000-01-01", ruido=dj.RUIDO, banco=banco)
    (processo,) = base.processos
    assert processo.processo_novo and processo.registros[0].registro_novo
    assert processo.registros[0].movimentos_iniciais == 2 and processo.registros[0].movimentos == []

    with sqlite3.connect(banco) as con:
        depois_da_base = con.execute("SELECT MAX(observado_em) FROM observacoes").fetchone()[0]
    marco = mov(848, "2026-10-18T09:00:00Z", "Transito em julgado")
    rotina = mov(581, "2026-10-18T10:00:00Z", "Juntada")
    registrar(banco, hit([*ANTIGOS, marco, rotina]))
    stj = hit([mov(26, "2026-10-18T11:00:00Z", "Distribuicao")])
    stj["_index"], stj["_id"] = "api_publica_stj", "STJ_SUP_" + NUMERO
    stj["_source"]["grau"] = "SUP"
    store.registrar_resposta("stj", REQUISICAO, resposta(stj), banco=banco)

    agora = store.novidades(datetime.fromisoformat(depois_da_base) + timedelta(microseconds=1),
                            ruido=dj.RUIDO, banco=banco)
    (processo,) = agora.processos
    assert not processo.processo_novo
    tjro, stj_reg = sorted(processo.registros, key=lambda r: r.registro.tribunal, reverse=True)
    assert [(m.codigo, m.marco, m.evento) for m in tjro.movimentos] == [
        (848, True, "entrou"), (581, False, "entrou")]
    assert stj_reg.registro_novo and stj_reg.movimentos_iniciais == 1
    assert store.novidades("2000-01-01", numeros=["0000000-00.2024.8.22.0001"], banco=banco).processos == []


def test_cli_novidades_emite_o_modelo(monkeypatch, tmp_path, capsys):
    banco = tmp_path / "acervo.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))
    registrar(banco, hit())
    assert dj.app(result_action="return_value", tokens=["novidades", "2000-01-01", "--json"]) == 0
    saida = store.Novidades.model_validate_json(capsys.readouterr().out)
    assert saida.processos[0].processo_novo
    assert dj.app(result_action="return_value", tokens=["novidades", "2000-01-01"]) == 0
    assert "primeira observacao" in capsys.readouterr().out
