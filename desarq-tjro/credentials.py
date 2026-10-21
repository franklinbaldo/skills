"""Armazenamento seguro de tokens e credenciais no Windows Credential Manager / Keyring."""

from __future__ import annotations

import json
import logging

import keyring
from errors import KeyringStorageError, KeyringUnavailableError
from models import TokenResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = "desarq-tjro"
DEFAULT_USERNAME = "current_session"


class CredentialStore:
    """Gerencia a persistência de tokens no Keyring com sanitização e tratamento de erros."""

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME, username: str = DEFAULT_USERNAME) -> None:
        self.service_name = service_name
        self.username = username

    def check_availability(self) -> None:
        """Verifica se o backend de keyring está disponível."""
        try:
            backend = keyring.get_keyring()
            if backend is None:
                raise KeyringUnavailableError("Nenhum backend de keyring configurado no sistema.")
        except Exception as exc:
            raise KeyringUnavailableError(f"Erro ao verificar disponibilidade do keyring: {exc}") from exc

    def save_tokens(self, tokens: TokenResponse) -> None:
        """Salva a resposta de tokens serializada no keyring."""
        self.check_availability()
        try:
            payload = tokens.model_dump_json()
            keyring.set_password(self.service_name, self.username, payload)
        except Exception as exc:
            raise KeyringStorageError(f"Falha ao gravar credenciais no keyring: {exc}") from exc

    def load_tokens(self) -> TokenResponse | None:
        """Carrega e valida os tokens armazenados no keyring."""
        self.check_availability()
        try:
            raw = keyring.get_password(self.service_name, self.username)
            if not raw:
                return None
            return TokenResponse.model_validate_json(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise KeyringStorageError(f"Credenciais armazenadas estão corrompidas ou inválidas: {exc}") from exc
        except Exception as exc:
            raise KeyringStorageError(f"Falha ao ler credenciais do keyring: {exc}") from exc

    def delete_tokens(self) -> None:
        """Remove as credenciais armazenadas."""
        self.check_availability()
        try:
            keyring.delete_password(self.service_name, self.username)
        except Exception:
            # Silencioso se a credencial não existir
            pass
