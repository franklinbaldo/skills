# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest", "fastmcp>=2.0", "requests"]
# ///
"""Testes das duas propriedades que a superfície do DataJud precisa manter.

Nenhum toca a rede: `datajud_processo` recebe a resposta do Elasticsearch por
monkeypatch em `dj.search`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud_mcp as mod  # noqa: E402

import datajud as dj  # noqa: E402


def _hit(grau: str, movimentos: list[dict]) -> dict:
    return {
        "_source": {
            "numeroProcesso": "70006676720268220000",
            "grau": grau,
            "classe": {"codigo": 120, "nome": "Mandado de Segurança Cível"},
            "assuntos": [],
            "orgaoJulgador": {"nome": "2ª Vara"},
            "dataAjuizamento": "20260130000000",
            "dataHoraUltimaAtualizacao": "2026-07-14T08:36:00Z",
            "movimentos": movimentos,
        }
    }


def _responder(monkeypatch, hits: list[dict]) -> None:
    monkeypatch.setattr(dj, "search", lambda *a, **k: {"hits": {"hits": hits}})


def test_ultimo_marco_desempata_por_segundo_entre_graus(monkeypatch):
    """Dois graus no mesmo minuto: o de segundo maior tem de vencer.

    `fmt_data_iso` corta a data em ``HH:MM``. Comparar a data formatada para
    achar o último marco faz 09:45:01 e 09:45:59 empatarem, e o desempate cai
    na ordem de iteração dos documentos — que é por grau, não por tempo.

    Mutação que este teste tem de matar: trocar a chave do `max()` de `_ord`
    (timestamp cru) por `data` (formatada). Com ela, o G1 vence por vir antes.
    """
    _responder(
        monkeypatch,
        [
            _hit("G1", [{"codigo": 246, "nome": "Definitivo", "dataHora": "2026-07-14T09:45:01Z"}]),
            _hit("G2", [{"codigo": 848, "nome": "Trânsito em julgado", "dataHora": "2026-07-14T09:45:59Z"}]),
        ],
    )
    saida = mod.datajud_processo("7000667-67.2026.8.22.0000")

    assert "Trânsito em julgado" in saida["resumo"], (
        "o último marco deve ser o do G2, que ocorreu 58 segundos depois; "
        f"veio: {saida['resumo']}"
    )
    assert "Definitivo" not in saida["resumo"]


def test_marco_interno_nao_vaza_para_a_saida(monkeypatch):
    """A chave de ordenação sobrevive ao max() global e some da resposta."""
    _responder(
        monkeypatch,
        [_hit("G1", [{"codigo": 848, "nome": "Trânsito em julgado", "dataHora": "2026-06-22T19:38:00Z"}])],
    )
    saida = mod.datajud_processo("7000667-67.2026.8.22.0000")

    marcos = [m for d in saida["documentos"] for m in d["marcos"]]
    assert marcos, "deveria haver ao menos um marco"
    assert all("_ord" not in m for m in marcos)


@pytest.mark.parametrize("codigo", sorted(mod.RUIDO))
def test_todo_codigo_de_ruido_conhecido_desaparece(monkeypatch, codigo):
    """Cada código da lista de ruído tem de sumir dos marcos."""
    _responder(
        monkeypatch,
        [
            _hit(
                "G1",
                [
                    {"codigo": codigo, "nome": "ruído", "dataHora": "2026-01-01T10:00:00Z"},
                    {"codigo": 848, "nome": "Trânsito em julgado", "dataHora": "2026-01-02T10:00:00Z"},
                ],
            )
        ],
    )
    saida = mod.datajud_processo("7000667-67.2026.8.22.0000")
    codigos = [m["codigo"] for d in saida["documentos"] for m in d["marcos"]]

    assert codigo not in codigos
    assert 848 in codigos, "o marco legítimo não pode ser filtrado junto"


def test_codigo_desconhecido_permanece_como_marco(monkeypatch):
    """A heurística é por exclusão: o que não é ruído conhecido fica.

    É a propriedade que justifica filtrar o ruído em vez de enumerar os marcos.
    As Tabelas Processuais Unificadas do CNJ ganham códigos novos; um código de
    decisão que ninguém previu tem de aparecer, e não desaparecer em silêncio.
    """
    inedito = 999999
    assert inedito not in mod.RUIDO
    _responder(
        monkeypatch,
        [_hit("G1", [{"codigo": inedito, "nome": "Providência inédita", "dataHora": "2026-05-05T12:00:00Z"}])],
    )
    saida = mod.datajud_processo("7000667-67.2026.8.22.0000")
    codigos = [m["codigo"] for d in saida["documentos"] for m in d["marcos"]]

    assert inedito in codigos
    assert "Providência inédita" in saida["resumo"]


def test_processo_inexistente_devolve_proximo_passo(monkeypatch):
    """Resposta vazia carrega a própria continuação, como manda a mcp-coding."""
    _responder(monkeypatch, [])
    saida = mod.datajud_processo("7000667-67.2026.8.22.0000")

    assert saida["encontrado"] is False
    assert saida["next_actions"], "resposta vazia deve sugerir o próximo passo"
