# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8"]
# ///
"""Testes offline: nunca fazem requisicoes a API do CNJ."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "datajud_endpoints.py"
spec = importlib.util.spec_from_file_location("datajud_endpoints", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_total_e_particoes():
    assert {k: len(v) for k, v in mod.GRUPOS.items()} == {
        "estadual": 27, "eleitoral": 27, "trabalho": 24,
        "federal": 6, "superiores": 4, "militar_estadual": 3}
    assert len(mod.ALIASES) == 91
    assert sum(map(len, mod.GRUPOS.values())) == len(mod.ALIASES)


@pytest.mark.parametrize("alias", ["tjro", "trt14", "tre-ro", "trf1", "stj", "tse", "tjmmg"])
def test_endpoint(alias):
    assert mod.endpoint(alias) == (
        f"https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search")


@pytest.mark.parametrize("alias", ["stf", "TJRO", "../_cat", "tjxx", ""])
def test_alias_desconhecido_nao_produz_url(alias):
    with pytest.raises(ValueError):
        mod.endpoint(alias)


def test_inventario_offline_nao_acessa_rede(capsys):
    with patch.object(mod.urllib.request, "urlopen", side_effect=AssertionError("rede")):
        assert mod.executar() == 0
    assert '"total": 91' in capsys.readouterr().out


def test_probe_sem_chave_nao_acessa_rede(monkeypatch):
    monkeypatch.delenv("DATAJUD_API_KEY", raising=False)
    with patch.object(mod.urllib.request, "urlopen", side_effect=AssertionError("rede")):
        with pytest.raises(ValueError, match="DATAJUD_API_KEY"):
            mod.executar(probe=True, alias="tjro")


def test_feature_matrix():
    assert set(mod.FEATURE_QUERIES) == {
        "match_all", "term", "bool", "range", "aggs", "source", "sort"
    }
    assert all("size" in q for q in mod.FEATURE_QUERIES.values())


def test_journal_append_only_e_resume(tmp_path):
    path = tmp_path / "probe.jsonl"
    key = mod._observation_key("tjro", "match_all")
    mod._append_event(path, {"key": key, "ok": True, "observed_at": "2026-10-21T00:00:00Z"})
    mod._append_event(path, {"key": "falhou", "ok": False})
    with path.open("a", encoding="utf-8") as out:
        out.write('{"incompleto":')
    assert mod._sucessos(path) == {key}
    assert len(path.read_text(encoding="utf-8").splitlines()) == 3


def test_probe_feature_e_corpo_minimo():
     from unittest.mock import MagicMock

    resposta = MagicMock()
    resposta.status = 200
    resposta.read.return_value = b'{"hits": {"total": {"value": 0}}}'
    context = MagicMock()
    context.__enter__.return_value = resposta
    with patch.object(mod.urllib.request, "urlopen", return_value=context) as urlopen:
        r = mod.probe("tjro", "fake-key", feature="range")
    assert r["ok"] is True
    request = urlopen.call_args.args[0]
    import json
    payload = json.loads(request.data)
    assert "range" in payload["query"]
    assert payload["size"] == 0


def test_probe_nao_considera_falha_shard_sucesso():
    from unittest.mock import MagicMock
    resposta = MagicMock()
    resposta.status = 200
    resposta.read.return_value = b'{"hits": {}, "_shards": {"failed": 1}}'
    context = MagicMock()
    context.__enter__.return_value = resposta
    with patch.object(mod.urllib.request, "urlopen", return_value=context):
        r = mod.probe("tjro", "fake-key")
    assert r["ok"] is False
    assert r["categoria"] == "parcial"


def test_resume_pula_sucesso_sem_rede(monkeypatch, tmp_path):
    path = tmp_path / "journal.jsonl"
    key = mod._observation_key("tjro", "match_all")
    mod._append_event(path, {"key": key, "ok": True})
    monkeypatch.setenv("DATAJUD_API_KEY", "fake-key")
    with patch.object(mod, "probe", side_effect=AssertionError("rede")):
        assert mod.executar(probe=True, alias="tjro", journal=path, resume=True) == 0
