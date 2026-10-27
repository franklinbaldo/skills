# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
"""Armazenamento seguro de credenciais e tokens da PDPJ/Jus.br no Keyring / Windows Credential Manager."""

from __future__ import annotations

import json
import logging
import secrets
import time

import keyring
from errors import KeyringStorageError, KeyringUnavailableError
from models import TokenResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = "jus-br"
DEFAULT_USERNAME = "current_session"
CHUNK_SIZE = 512  # Limite seguro para CredWriteW do WinVault


class CredentialStore:
    """Gerencia a persistência de tokens no Keyring usando gerações imutáveis e ponteiro atômico.

    Cada gravação cria uma nova geração isolada (ex: current_session_gen_1729530000_abcd).
    Todos os chunks da nova geração são gravados e validados antes do ponteiro ativo ser atualizado.
    Em caso de falha a meio caminho, os chunks da nova geração são descartados e a geração ativa
    anterior permanece intocada. Somente após a troca bem-sucedida do ponteiro ativo a geração antiga é purgada.
    """

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME, username: str = DEFAULT_USERNAME) -> None:
        self.service_name = service_name
        self.username = username

    @property
    def _active_pointer_key(self) -> str:
        return f"{self.username}_active_gen"

    def check_availability(self) -> None:
        """Verifica se o backend de keyring está disponível."""
        try:
            backend = keyring.get_keyring()
            if backend is None:
                raise KeyringUnavailableError("Nenhum backend de keyring configurado no sistema.")
        except Exception as exc:
            raise KeyringUnavailableError(f"Erro ao verificar disponibilidade do keyring: {exc}") from exc

    def _purge_generation(self, gen_id: str) -> None:
        """Exclui com segurança todas as chaves associadas a uma geração específica."""
        chunks_key = f"{self.username}_{gen_id}_chunks"
        chunks_count_str = None
        try:
            chunks_count_str = keyring.get_password(self.service_name, chunks_key)
        except Exception:
            pass

        if chunks_count_str:
            try:
                total_chunks = int(chunks_count_str)
            except ValueError:
                total_chunks = 0
            for idx in range(total_chunks):
                try:
                    keyring.delete_password(self.service_name, f"{self.username}_{gen_id}_chunk_{idx}")
                except Exception:
                    pass
            try:
                keyring.delete_password(self.service_name, chunks_key)
            except Exception:
                pass
        else:
            try:
                keyring.delete_password(self.service_name, f"{self.username}_{gen_id}")
            except Exception:
                pass

    @staticmethod
    def _split_chunks(payload: str) -> list[str]:
        """Divide texto em blocos de no máximo 512 bytes sem cortar UTF-8."""
        chunks: list[str] = []
        current: list[str] = []
        current_size = 0
        for char in payload:
            char_size = len(char.encode("utf-8"))
            if current and current_size + char_size > CHUNK_SIZE:
                chunks.append("".join(current))
                current = []
                current_size = 0
            current.append(char)
            current_size += char_size
        if current:
            chunks.append("".join(current))
        return chunks

    def _purge_legacy(self) -> None:
        """Limpa identificadores legados que não utilizavam controle de geração."""
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

    def save_tokens(self, tokens: TokenResponse) -> None:
        """Salva a resposta de tokens criando uma geração imutável e comutando o ponteiro de forma atômica."""
        self.check_availability()
        payload = tokens.model_dump_json()
        payload_bytes = payload.encode("utf-8")

        old_gen = None
        try:
            old_gen = keyring.get_password(self.service_name, self._active_pointer_key)
        except Exception:
            old_gen = None

        new_gen = f"gen_{int(time.time())}_{secrets.token_hex(4)}"
        written_keys: list[str] = []

        try:
            if len(payload_bytes) <= CHUNK_SIZE:
                key = f"{self.username}_{new_gen}"
                keyring.set_password(self.service_name, key, payload)
                written_keys.append(key)
            else:
                chunks = self._split_chunks(payload)
                for idx, chunk in enumerate(chunks):
                    chunk_key = f"{self.username}_{new_gen}_chunk_{idx}"
                    keyring.set_password(self.service_name, chunk_key, chunk)
                    written_keys.append(chunk_key)

                chunks_key = f"{self.username}_{new_gen}_chunks"
                keyring.set_password(self.service_name, chunks_key, str(len(chunks)))
                written_keys.append(chunks_key)

            # Valida a geração completa antes de publicar o ponteiro. Isso detecta
            # gravações truncadas ou omitidas pelo backend de keyring.
            if len(payload_bytes) <= CHUNK_SIZE:
                persisted = keyring.get_password(self.service_name, f"{self.username}_{new_gen}")
            else:
                persisted_count = keyring.get_password(self.service_name, f"{self.username}_{new_gen}_chunks")
                if persisted_count != str(len(chunks)):
                    raise ValueError("Contador de chunks não confere após gravação.")
                persisted_parts = [
                    keyring.get_password(self.service_name, f"{self.username}_{new_gen}_chunk_{idx}")
                    for idx in range(len(chunks))
                ]
                if any(part is None for part in persisted_parts):
                    raise ValueError("Chunk ausente após gravação.")
                persisted = "".join(persisted_parts)
            if persisted != payload:
                raise ValueError("Conteúdo persistido não confere com os tokens gravados.")
            TokenResponse.model_validate_json(persisted)

            # Transição atômica: atualiza o ponteiro para a nova geração
            keyring.set_password(self.service_name, self._active_pointer_key, new_gen)
            if keyring.get_password(self.service_name, self._active_pointer_key) != new_gen:
                raise ValueError("Ponteiro ativo não confirmou a nova geração.")

        except Exception as exc:
            # A gravação do ponteiro pode persistir e ainda assim lançar erro. Restaura
            # o valor anterior antes de remover a geração candidata.
            pointer_restored = False
            try:
                if old_gen:
                    keyring.set_password(self.service_name, self._active_pointer_key, old_gen)
                else:
                    keyring.delete_password(self.service_name, self._active_pointer_key)
                restored = keyring.get_password(self.service_name, self._active_pointer_key)
                pointer_restored = restored == old_gen
            except Exception:
                logger.exception("Não foi possível restaurar o ponteiro anterior do keyring")
            # Se o estado do ponteiro for incerto, preserve a geração candidata:
            # ela pode ter se tornado a ativa apesar da exceção do backend.
            if pointer_restored:
                for k in written_keys:
                    try:
                        keyring.delete_password(self.service_name, k)
                    except Exception:
                        pass
            raise KeyringStorageError(
                f"Falha ao persistir nova geração de credenciais no keyring "
                f"({'geração anterior restaurada' if pointer_restored else 'estado do ponteiro incerto; dados preservados'}): {exc}"
            ) from exc

        # Após o commit bem-sucedido do novo ponteiro, purga a geração antiga e dados legados
        if old_gen and old_gen != new_gen:
            self._purge_generation(old_gen)
        self._purge_legacy()

    def load_tokens(self) -> TokenResponse | None:
        """Carrega e remonta os tokens da geração ativa apontada no keyring."""
        self.check_availability()
        try:
            active_gen = keyring.get_password(self.service_name, self._active_pointer_key)
            raw = None

            if active_gen:
                chunks_key = f"{self.username}_{active_gen}_chunks"
                chunks_count_str = keyring.get_password(self.service_name, chunks_key)
                if chunks_count_str:
                    try:
                        total_chunks = int(chunks_count_str)
                    except ValueError as exc:
                        raise KeyringStorageError(f"Contador de chunks corrompido na geração ativa: {exc}") from exc
                    parts = []
                    for idx in range(total_chunks):
                        part = keyring.get_password(self.service_name, f"{self.username}_{active_gen}_chunk_{idx}")
                        if part is None:
                            raise KeyringStorageError(f"Chunk {idx} ausente na geração ativa.")
                        parts.append(part)
                    raw = "".join(parts)
                else:
                    raw = keyring.get_password(self.service_name, f"{self.username}_{active_gen}")
            else:
                chunks_count_str = keyring.get_password(self.service_name, f"{self.username}_chunks")
                if chunks_count_str:
                    try:
                        total_chunks = int(chunks_count_str)
                    except ValueError as exc:
                        raise KeyringStorageError(f"Contador legado corrompido: {exc}") from exc
                    parts = []
                    for idx in range(total_chunks):
                        part = keyring.get_password(self.service_name, f"{self.username}_chunk_{idx}")
                        if part is None:
                            raise KeyringStorageError(f"Chunk legado {idx} ausente.")
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
        """Remove todas as credenciais ativas, gerações e registros legados."""
        self.check_availability()
        try:
            active_gen = keyring.get_password(self.service_name, self._active_pointer_key)
            if active_gen:
                generation_count_key = f"{self.username}_{active_gen}_chunks"
                generation_count = keyring.get_password(self.service_name, generation_count_key)
                generation_keys = [f"{self.username}_{active_gen}", generation_count_key]
                if generation_count:
                    generation_keys.extend(
                        f"{self.username}_{active_gen}_chunk_{idx}" for idx in range(int(generation_count))
                    )
                self._purge_generation(active_gen)
                if any(keyring.get_password(self.service_name, key) is not None for key in generation_keys):
                    raise KeyringStorageError("Uma ou mais credenciais da geração ativa permaneceram no keyring.")
                try:
                    keyring.delete_password(self.service_name, self._active_pointer_key)
                except Exception:
                    pass
                if keyring.get_password(self.service_name, self._active_pointer_key) is not None:
                    raise KeyringStorageError("O ponteiro da sessão permaneceu no keyring.")
            self._purge_legacy()
            legacy_count = keyring.get_password(self.service_name, f"{self.username}_chunks")
            legacy_keys = [self.username, f"{self.username}_chunks"]
            if legacy_count:
                legacy_keys.extend(f"{self.username}_chunk_{idx}" for idx in range(int(legacy_count)))
            if any(keyring.get_password(self.service_name, key) is not None for key in legacy_keys):
                raise KeyringStorageError("Uma ou mais credenciais legadas permaneceram no keyring.")
            if (
                keyring.get_password(self.service_name, self._active_pointer_key) is not None
                or self.load_tokens() is not None
            ):
                raise KeyringStorageError("O keyring ainda contém uma sessão após a tentativa de remoção local.")
        except KeyringStorageError:
            raise
        except Exception as exc:
            raise KeyringStorageError(f"Falha ao remover a sessão local do keyring: {exc}") from exc
