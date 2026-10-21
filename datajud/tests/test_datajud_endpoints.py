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
        assert mod.main([]) == 0
    assert '"total": 91' in capsys.readouterr().out


def test_probe_sem_chave_nao_acessa_rede(monkeypatch):
    monkeypatch.delenv("DATAJUD_API_KEY", raising=False)
    with patch.object(mod.urllib.request, "urlopen", side_effect=AssertionError("rede")):
        with pytest.raises(SystemExit) as err:
            mod.main(["--probe", "--alias", "tjro"])
    assert err.value.code == 2
