#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
#     "rich>=13.0.0",
# ]
# ///
"""Interface de linha de comando para o Jus.br e o Portal de Serviços da PDPJ/CNJ.

Cada grupo de comandos mora no seu módulo (`cli_auth`, `cli_consultas`,
`cli_processo`, `cli_peticao`); este arquivo só os reúne.
"""

from __future__ import annotations

import sys
from pathlib import Path

_raiz = Path(__file__).resolve().parent
if str(_raiz) not in sys.path:
    sys.path.insert(0, str(_raiz))

from cli_auth import auth_app  # noqa: E402
from cli_consultas import api_app, comunicacoes_app, usuario_app  # noqa: E402
from cli_peticao import peticao_app  # noqa: E402
from cli_processo import processo_app  # noqa: E402
from cyclopts import App  # noqa: E402

app = App(
    name="jusbr",
    help="CLI para o Jus.br e o Portal de Serviços da PDPJ-Br: sessão, autos, comunicações e petições.",
    result_action=lambda x: x,
)
for grupo in (auth_app, usuario_app, comunicacoes_app, processo_app, peticao_app, api_app):
    app.command(grupo)

if __name__ == "__main__":
    app()
