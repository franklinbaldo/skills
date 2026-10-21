"""Armazenamento seguro de tokens e credenciais no Windows Credential Manager / Keyring com suporte a chunking."""

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
CHUNK_SIZE = 512  # Limite de segurança para WinVault (CredWriteW aceita até 512 WCHARs)


class CredentialStore:
    """Gerencia a persistência de tokens no Keyring com chunking transparente e sanitização."""

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
        """Salva a resposta de tokens serializada no keyring, usando chunking se exceder CHUNK_SIZE."""
        self.check_availability()
        try:
            # Limpa credenciais anteriores para evitar estado inconsistente de chunks
            self.delete_tokens()

            payload = tokens.model_dump_json()
            if len(payload) <= CHUNK_SIZE:
                keyring.set_password(self.service_name, self.username, payload)
            else:
                chunks = [payload[i : i + CHUNK_SIZE] for i in range(0, len(payload), CHUNK_SIZE)]
                for idx, chunk in enumerate(chunks):
                    keyring.set_password(self.service_name, f"{self.username}_chunk_{idx}", chunk)
                keyring.set_password(self.service_name, f"{self.username}_chunks", str(len(chunks)))
        except Exception as exc:
            raise KeyringStorageError(f"Falha ao gravar credenciais no keyring: {exc}") from exc

    def load_tokens(self) -> TokenResponse | None:
        """Carrega e remonta os tokens armazenados no keyring."""
        self.check_availability()
        try:
            chunks_count_str = keyring.get_password(self.service_name, f"{self.username}_chunks")
            if chunks_count_str:
                try:
                    total_chunks = int(chunks_count_str)
                except ValueError as exc:
                    raise KeyringStorageError(
                        f"Credenciais armazenadas estão corrompidas (contador inválido): {exc}"
                    ) from exc
                parts = []
                for idx in range(total_chunks):
                    part = keyring.get_password(self.service_name, f"{self.username}_chunk_{idx}")
                    if part is None:
                        raise KeyringStorageError(f"Chunk {idx} ausente no keyring.")
                    parts.append(part)
                raw = "".join(parts)
            else:
                raw = keyring.get_password(self.service_name, self.username)

            if not raw:
                return None
            return TokenResponse.model_validate_json(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise KeyringStorageError(f"Credenciais armazenadas estão corrompidas ou inválidas: {exc}") from exc
        except KeyringStorageError:
            raise
        except Exception as exc:
            raise KeyringStorageError(f"Falha ao ler credenciais do keyring: {exc}") from exc

    def delete_tokens(self) -> None:
        """Remove todas as credenciais e chunks armazenados."""
        self.check_availability()
        try:
            chunks_count_str = keyring.get_password(self.service_name, f"{self.username}_chunks")
            if chunks_count_str:
                try:
                    total_chunks = int(chunks_count_str)
                except ValueError:
                    total_chunks = 0
                for idx in range(total_chunks):
                    try:
                        keyring.delete_password(self.service_name, f"{self.username}_chunk_{idx}")
                    except Exception:
                        pass
                try:
                    keyring.delete_password(self.service_name, f"{self.username}_chunks")
                except Exception:
                    pass

            try:
                keyring.delete_password(self.service_name, self.username)
            except Exception:
                pass
        except Exception:
            pass
