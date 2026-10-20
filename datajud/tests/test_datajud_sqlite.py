# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "cyclopts>=3.0", "pydantic>=2.6"]
# ///
"""Regressao do historico append-only; usa somente SQLite local e HTTP simulado."""

from __future__ import annotations

import io
import json
import sqlite3
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud as dj  # noqa: E402
import datajud_store as store  # noqa: E402


NUMERO = "70095117120248220001"


def hit(movimentos=None, *, score=1.0):
    return {
        "_index": "api_publica_tjro",
        "_id": "identificador-estavel",
        "_score": score,
        "_source": {
            "numeroProcesso": NUMERO,
            "grau": "G1",
            "orgaoJulgador": {"codigo": 101},
            "movimentos": movimentos or [],
        },
    }


def resposta(*hits):
    return {
        "took": 17,
        "_shards": {"total": 1, "successful": 1, "failed": 0},
        "hits": {"total": {"value": len(hits), "relation": "eq"}, "hits": list(hits)},
    }


def contagens(banco):
    return store.estatisticas(banco=banco)


def test_mesma_versao_e_nova_observacao_sem_update(tmp_path):
    banco = tmp_path / "datajud.sqlite"
    requisicao = {"query": {"term": {"numeroProcesso": NUMERO}}}

    store.registrar_resposta("tjro", requisicao, resposta(hit(score=1.0)), banco=banco)
    store.registrar_resposta("tjro", requisicao, resposta(hit(score=8.5)), banco=banco)

    total = contagens(banco)
    assert total["consultas"] == 2
    assert total["versoes"] == 1, "_score so muda a observacao, nao a versao"
    assert total["observacoes"] == 2, "cada retorno registra uma observacao"

    store.registrar_resposta(
        "tjro", requisicao,
        resposta(hit([{"codigo": 848, "dataHora": "2026-10-19T23:00:00Z"}])),
        banco=banco,
    )
    total = contagens(banco)
    assert total["consultas"] == 3
    assert total["versoes"] == 2, "versao anterior preservada"
    assert total["observacoes"] == 3
    versoes = store.historico(NUMERO, banco=banco)
    assert len(versoes) == 2
    assert sorted(item["observacoes"] for item in versoes) == [1, 2]
    assert versoes[0]["sha256"] != versoes[1]["sha256"]
    assert all(item["primeira_vista"] and item["ultima_vista"] for item in versoes)

    with sqlite3.connect(banco) as con:
        for tabela in ("consultas", "versoes_documento", "observacoes_documento"):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                con.execute(f"UPDATE {tabela} SET id = id WHERE id = 1")
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                con.execute(f"DELETE FROM {tabela} WHERE id = 1")
    assert contagens(banco)["observacoes"] == 3


def test_consulta_sem_hit_e_agregacoes_tambem_ficam_no_banco(tmp_path):
    banco = tmp_path / "eventos.sqlite"
    store.registrar_resposta(
        "tjro",
        {"size": 0, "aggs": {"c": {"terms": {"field": "classe.codigo"}}}},
        {"took": 12, "hits": {"total": {"value": 0}, "hits": []},
         "aggregations": {"c": {"buckets": [{"key": 1116, "doc_count": 2}]}}},
        banco=banco,
    )
    store.registrar_erro("stj", {"query": {"match_all": {}}}, "HTTP 504", banco=banco)
    assert contagens(banco)["consultas"] == 2
    assert contagens(banco)["versoes"] == 0
    assert contagens(banco)["observacoes"] == 0
    with sqlite3.connect(banco) as con:
        ok, falha = con.execute(
            "SELECT resultado, resposta_meta_json, erro FROM consultas ORDER BY id"
        ).fetchall()
    assert ok[0] == "ok"
    payload = json.loads(ok[1])
    assert payload["aggregations"]["c"]["buckets"][0]["doc_count"] == 2
    assert "hits" not in payload["hits"], "hits.hits sao armazenados por documento"
    assert falha[0] == "erro" and "504" in falha[2]


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
    assert dj.search({"query": {"term": {"numeroProcesso": NUMERO}}}, tribunal="tjro")["hits"]
    assert dj.search({"query": {"term": {"numeroProcesso": NUMERO}}}, tribunal="tjro")["hits"]
    assert contagens(banco)["consultas"] == 2
    assert contagens(banco)["versoes"] == 1
    assert contagens(banco)["observacoes"] == 2


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

    assert contagens(banco)["consultas"] == 1
    assert contagens(banco)["versoes"] == 0
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
    assert contagens(banco)["consultas"] == 2
    assert contagens(banco)["versoes"] == 1
    assert contagens(banco)["observacoes"] == 2
    assert sorted(x.name for x in tmp_path.iterdir()) == ["acervo.sqlite", "processos.txt"] or (
        # WAL e SHM podem existir dependendo do SQLite e do ambiente.
        not list(tmp_path.rglob("*.json"))
    )


def test_roteamento_df_e_justica_militar():
    assert dj.tribunal_do_cnj("0000001-00.2024.6.07.0001") == "tre-dft"
    assert "tre-dft" in dj.familia_do_cnj("0000001-00.2024.8.07.0001")
    assert "tre-df" not in dj.familia_do_cnj("0000001-00.2024.8.07.0001")
    assert dj.tribunal_do_cnj("0000001-00.2024.7.01.0001") == "stm"
