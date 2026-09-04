# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest", "fastmcp>=2.0", "cyclopts>=3.0", "rich>=13.0", "requests"]
# ///
"""Regressões da projeção humana do CLI DataJud."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud_mcp as mod  # noqa: E402


def _resultado() -> dict:
    return {
        "processo": "7027457-61.2021.8.22.0001",
        "tribunal": "TJRO",
        "encontrado": True,
        "resumo": "7027457-61.2021.8.22.0001 — TJRO — último marco: Definitivo.",
        "documentos": [
            {
                "grau": "Juizado Especial",
                "classe": "Cumprimento de sentença (156)",
                "assuntos": "Acidente de Trânsito",
                "orgao": "5º Juizado Especial Cível",
                "ajuizamento": "01/06/2021 13:50",
                "ultima_atualizacao": "03/08/2026 02:08",
                "marcos": [
                    {"data": f"0{i}/06/2026 08:34", "codigo": i, "nome": f"Marco {i}"}
                    for i in range(1, 15)
                ],
                "total_movimentos": 20,
                "movimentos_omitidos": 6,
            }
        ],
        "next_actions": [
            {
                "tool": "datajud_processo",
                "args": {
                    "cnj": "7027457-61.2021.8.22.0001",
                    "tribunal": "tjro",
                    "incluir_movimentos": True,
                },
                "reason": "Ver movimentos omitidos.",
            }
        ],
    }


def test_render_human_e_compacto_e_nao_despeja_json(capsys):
    mod._render_human(_resultado(), incluir_movimentos=False)
    out = capsys.readouterr().out

    assert "7027457-61.2021.8.22.0001" in out
    assert "Juizado Especial" in out
    assert "Marcos recentes (12/14)" in out
    assert "Marco 1" not in out
    assert "Marco 14" in out
    assert '"documentos"' not in out
    assert "Próximos passos" in out


def test_cli_json_preserva_payload_cru(monkeypatch, capsys):
    payload = _resultado()
    monkeypatch.setattr(mod, "datajud_processo", lambda *args, **kwargs: payload)

    status = mod.processo("7027457-61.2021.8.22.0001", json=True)
    out = capsys.readouterr().out

    assert status == 0
    assert json.loads(out) == payload
    assert "╭" not in out


def test_cli_humana_nao_muda_contrato_mcp(monkeypatch, capsys):
    payload = _resultado()
    monkeypatch.setattr(mod, "datajud_processo", lambda *args, **kwargs: payload)

    status = mod.processo("7027457-61.2021.8.22.0001")
    out = capsys.readouterr().out

    assert status == 0
    assert "Cumprimento de sentença" in out
    assert payload["documentos"][0]["marcos"][0]["nome"] == "Marco 1"
    assert len(payload["documentos"][0]["marcos"]) == 14
