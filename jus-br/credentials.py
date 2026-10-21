"""Armazenamento seguro de credenciais e tokens da PDPJ/Jus.br no Keyring / Windows Credential Manager."""

from __future__ import annotations

import json
import logging

import keyring
from errors import KeyringStorageError, KeyringUnavailableError
from models import TokenResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = "jus-br"
DEFAULT_USERNAME = "current_session"
CHUNK_SIZE = 512  # Limite seguro para CredWriteW do WinVault


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
        """Salva a resposta de tokens serializada no keyring de forma transacional.

        Os dados anteriores somente são expurgados após a gravação completa e bem-sucedida dos novos tokens.
        Em caso de falha durante a escrita, a sessão anterior é preservada.
        """
        self.check_availability()
        payload = tokens.model_dump_json()

        # Descobrir estado prévio
        old_chunks_count = 0
        try:
            old_count_str = keyring.get_password(self.service_name, f"{self.username}_chunks")
            if old_count_str:
                old_chunks_count = int(old_count_str)
        except Exception:
            old_chunks_count = 0

        if len(payload) <= CHUNK_SIZE:
            # Modo single: grava o payload completo primeiro
            try:
                keyring.set_password(self.service_name, self.username, payload)
            except Exception as exc:
                raise KeyringStorageError(f"Falha ao gravar credenciais no keyring: {exc}") from exc

            # Limpa chunks antigos excedentes após sucesso
            if old_chunks_count > 0:
                for idx in range(old_chunks_count):
                    try:
                        keyring.delete_password(self.service_name, f"{self.username}_chunk_{idx}")
                    except Exception:
                        pass
                try:
                    keyring.delete_password(self.service_name, f"{self.username}_chunks")
                except Exception:
                    pass
        else:
            # Modo chunking: grava os novos chunks
            chunks = [payload[i : i + CHUNK_SIZE] for i in range(0, len(payload), CHUNK_SIZE)]
            written_chunks = []
            try:
                for idx, chunk in enumerate(chunks):
                    keyring.set_password(self.service_name, f"{self.username}_chunk_{idx}", chunk)
                    written_chunks.append(idx)
                # Atualiza o contador de chunks consolidando a nova transação
                keyring.set_password(self.service_name, f"{self.username}_chunks", str(len(chunks)))
            except Exception as exc:
                # Rollback parcial dos chunks que acabaram de ser escritos nesta tentativa
                for idx in written_chunks:
                    try:
                        keyring.delete_password(self.service_name, f"{self.username}_chunk_{idx}")
                    except Exception:
                        pass
                raise KeyringStorageError(
                    f"Falha ao gravar novos chunks no keyring (sessão anterior preservada): {exc}"
                ) from exc

            # Limpa valor single antigo se existia
            try:
                keyring.delete_password(self.service_name, self.username)
            except Exception:
                pass

            # Limpa chunks antigos que excedem o novo tamanho
            if old_chunks_count > len(chunks):
                for idx in range(len(chunks), old_chunks_count):
                    try:
                        keyring.delete_password(self.service_name, f"{self.username}_chunk_{idx}")
                    except Exception:
                        pass

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
