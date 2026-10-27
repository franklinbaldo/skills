# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
#     "rich>=13.0.0",
# ]
# ///
"""Console e serviços compartilhados pelos comandos da CLI.

Os comandos chamam `comum.AuthService()`, `comum.PortalClient()` etc. por este
módulo, e não por import direto, para que os testes troquem as classes num lugar só.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from auth import AuthService  # noqa: E402
from client import JusBrClient  # noqa: E402
from credentials import CredentialStore  # noqa: E402
from portal import PortalClient  # noqa: E402
from rich.console import Console  # noqa: E402

console = Console()

__all__ = ["RAIZ", "AuthService", "CredentialStore", "JusBrClient", "PortalClient", "console"]
