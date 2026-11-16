# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "duckdb>=1.1"]
# ///
"""Resolução de fonte, cache com checagem de frescor e reserva no Internet Archive, sem rede (`_abrir` simulado)."""

from __future__ import annotations

import io
import json
import sys
import urllib.error
from pathlib import Path
from typing import Any

import pytest

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "scripts"))
sys.path.insert(0, str(AQUI))

import legislacao_dados as dados  # noqa: E402
from legislacao_dados_teste import gravar_todos  # noqa: E402

PORTAL = dados.PADROES["catalogo"][0]
IA = dados.PADROES["catalogo"][1]


class Resposta:
    def __init__(self, corpo: bytes, etag: str = '"v1"') -> None:
        self.corpo = corpo
        self.headers = {"ETag": etag, "Last-Modified": "Mon, 16 Nov 2026 16:00:00 GMT"}

    def read(self) -> bytes:
        return self.corpo

    def __enter__(self) -> Resposta:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class Rede:
    """Servidor falso: `rotas` mapeia URL -> Resposta ou código HTTP; registra os pedidos."""

    def __init__(self, rotas: dict[str, Any]) -> None:
        self.rotas = rotas
        self.pedidos: list[tuple[str, dict[str, str]]] = []

    def __call__(self, pedido: Any, timeout: float) -> Resposta:
        url = pedido.full_url
        cabecalhos = {k.lower(): v for k, v in pedido.header_items()}
        self.pedidos.append((url, cabecalhos))
        destino = self.rotas.get(url, 404)
        if isinstance(destino, int):
            raise urllib.error.HTTPError(url, destino, "erro", {}, io.BytesIO(b""))  # type: ignore[arg-type]
        if cabecalhos.get("if-none-match") == destino.headers["ETag"]:
            raise urllib.error.HTTPError(url, 304, "Not Modified", {}, io.BytesIO(b""))  # type: ignore[arg-type]
        return destino


@pytest.fixture
def parquet(tmp_path: Path) -> bytes:
    return (gravar_todos(tmp_path / "f") / "catalogo.parquet").read_bytes()


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in ("BASE_URL", "CATALOGO"):
        monkeypatch.delenv(f"LEGISLACAO_RO_{nome}", raising=False)


def origens(tmp_path: Path, **kw: Any) -> dados.Origens:
    return dados.Origens(cache_dir=str(tmp_path / "cache"), **kw)


def test_baixa_do_portal_e_reusa_cache_fresco(monkeypatch, tmp_path, parquet) -> None:
    rede = Rede({PORTAL: Resposta(parquet)})
    monkeypatch.setattr(dados, "_abrir", rede)
    primeira = dados.resolver_fonte("catalogo", origens(tmp_path))
    assert primeira.origem == PORTAL
    assert primeira.caminho.read_bytes() == parquet
    dados.resolver_fonte("catalogo", origens(tmp_path))
    assert len(rede.pedidos) == 1  # segundo uso: cache fresco, nenhuma requisição


def test_cache_vencido_revalida_com_etag_e_aceita_304(monkeypatch, tmp_path, parquet) -> None:
    rede = Rede({PORTAL: Resposta(parquet)})
    monkeypatch.setattr(dados, "_abrir", rede)
    dados.resolver_fonte("catalogo", origens(tmp_path))
    meta = tmp_path / "cache" / "catalogo.json"
    antigo = json.loads(meta.read_text())
    antigo["verificado_em"] -= 3 * 24 * 3600
    meta.write_text(json.dumps(antigo))
    fonte = dados.resolver_fonte("catalogo", origens(tmp_path))
    assert len(rede.pedidos) == 2
    assert rede.pedidos[1][1]["if-none-match"] == '"v1"'
    assert fonte.caminho.read_bytes() == parquet
    assert json.loads(meta.read_text())["verificado_em"] > antigo["verificado_em"]  # frescor renovado
    dados.resolver_fonte("catalogo", origens(tmp_path, atualizar=True))
    assert len(rede.pedidos) == 3


def test_reserva_no_internet_archive(monkeypatch, tmp_path, parquet) -> None:
    rede = Rede({IA: Resposta(parquet)})  # portal responde 404
    monkeypatch.setattr(dados, "_abrir", rede)
    fonte = dados.resolver_fonte("catalogo", origens(tmp_path))
    assert fonte.origem == IA
    assert [u for u, _ in rede.pedidos] == [PORTAL, IA]


def test_ausente_nos_dois_espelhos_nomeia_dataset_e_tentativas(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(dados, "_abrir", Rede({}))
    with pytest.raises(dados.DatasetIndisponivel) as erro:
        dados.resolver_fonte("catalogo", origens(tmp_path))
    mensagem = str(erro.value)
    assert "dataset 'catalogo'" in mensagem
    assert PORTAL in mensagem
    assert IA in mensagem
    assert "HTTP 404" in mensagem


def test_sem_rede_usa_copia_antiga_com_aviso(monkeypatch, tmp_path, parquet) -> None:
    monkeypatch.setattr(dados, "_abrir", Rede({PORTAL: Resposta(parquet)}))
    dados.resolver_fonte("catalogo", origens(tmp_path))
    meta = tmp_path / "cache" / "catalogo.json"
    antigo = json.loads(meta.read_text())
    antigo["verificado_em"] -= 10 * 24 * 3600
    meta.write_text(json.dumps(antigo))
    monkeypatch.setattr(dados, "_abrir", Rede({}))
    fonte = dados.resolver_fonte("catalogo", origens(tmp_path))
    assert fonte.caminho.read_bytes() == parquet
    assert "desatualizada" in fonte.avisos[0]


def test_offline_sem_cache_falha_e_com_cache_nao_usa_rede(monkeypatch, tmp_path, parquet) -> None:
    rede = Rede({PORTAL: Resposta(parquet)})
    monkeypatch.setattr(dados, "_abrir", rede)
    with pytest.raises(dados.DatasetIndisponivel, match="offline"):
        dados.resolver_fonte("catalogo", origens(tmp_path, offline=True))
    assert rede.pedidos == []
    dados.resolver_fonte("catalogo", origens(tmp_path))
    dados.resolver_fonte("catalogo", origens(tmp_path, offline=True, atualizar=True))
    assert len(rede.pedidos) == 1


def test_base_url_e_caminho_explicito_tem_precedencia(monkeypatch, tmp_path, parquet) -> None:
    rede = Rede({"https://espelho/x/catalogo.parquet": Resposta(parquet)})
    monkeypatch.setattr(dados, "_abrir", rede)
    fonte = dados.resolver_fonte("catalogo", origens(tmp_path, base_url="https://espelho/x/"))
    assert fonte.origem == "https://espelho/x/catalogo.parquet"
    local = tmp_path / "meu.parquet"
    local.write_bytes(parquet)
    assert dados.resolver_fonte("catalogo", origens(tmp_path, catalogo=str(local))).caminho == local
    monkeypatch.setenv("LEGISLACAO_RO_CATALOGO", str(local))
    assert dados.resolver_fonte("catalogo", origens(tmp_path)).caminho == local
