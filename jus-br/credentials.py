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

    Arquitetura de Consistência e Atomicidade:
    1. Gerações Imutáveis: Cada gravação cria um conjunto de chaves sob uma geração única com timestamp e entropia
       criptográfica (ex: current_session_gen_1729530000_abcd_chunk_0). Dois processos concorrentes nunca colidem chunks.
    2. Validação Estrita Pré-Comutação (Roundtrip Verification): Antes de alternar a geração ativa, a implementação relê
       todos os chunks gravados no backend e desserializa o TokenResponse completo. Se houver falha de leitura, o ponteiro
       não é alterado e a geração defeituosa é descartada.
    3. Comutação de Ponteiro: A comutação é efetuada gravando a chave única '{username}_active_gen'. Nos backends oficiais
       (Windows Credential Manager via CredWriteW, macOS Keychain via SecItemAdd/Update e Linux SecretService via DBus), a
       escrita de uma chave individual é atômica no nível do subsistema de segurança do SO.
    4. Purga Tardia: Chunks de gerações anteriores só são removidos após a confirmação integral da nova geração ativa.
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

        old_gen = None
        try:
            old_gen = keyring.get_password(self.service_name, self._active_pointer_key)
        except Exception:
            old_gen = None

        new_gen = f"gen_{int(time.time())}_{secrets.token_hex(4)}"
        written_keys: list[str] = []

        try:
            if len(payload) <= CHUNK_SIZE:
                key = f"{self.username}_{new_gen}"
                keyring.set_password(self.service_name, key, payload)
                written_keys.append(key)
            else:
                chunks = [payload[i : i + CHUNK_SIZE] for i in range(0, len(payload), CHUNK_SIZE)]
                for idx, chunk in enumerate(chunks):
                    chunk_key = f"{self.username}_{new_gen}_chunk_{idx}"
                    keyring.set_password(self.service_name, chunk_key, chunk)
                    written_keys.append(chunk_key)

                chunks_key = f"{self.username}_{new_gen}_chunks"
                keyring.set_password(self.service_name, chunks_key, str(len(chunks)))
                written_keys.append(chunks_key)

            # Confirmação de gravação (roundtrip validation): relê e valida antes de atualizar o ponteiro
            if len(payload) <= CHUNK_SIZE:
                readback_raw = keyring.get_password(self.service_name, f"{self.username}_{new_gen}")
            else:
                readback_count = keyring.get_password(self.service_name, f"{self.username}_{new_gen}_chunks")
                if not readback_count or int(readback_count) != len(chunks):
                    raise KeyringStorageError("Verificação de gravação falhou: contador de chunks inconsistente.")
                parts = []
                for idx in range(len(chunks)):
                    p = keyring.get_password(self.service_name, f"{self.username}_{new_gen}_chunk_{idx}")
                    if p is None:
                        raise KeyringStorageError(f"Verificação de gravação falhou: chunk {idx} ausente na leitura.")
                    parts.append(p)
                readback_raw = "".join(parts)

            if not readback_raw:
                raise KeyringStorageError("Verificação de gravação falhou: dados ausentes no keyring.")

            # Desserializa e valida que o conteúdo persistido está perfeitamente íntegro
            TokenResponse.model_validate_json(readback_raw)

            # Transição atômica: comuta o ponteiro para a nova geração validada
            keyring.set_password(self.service_name, self._active_pointer_key, new_gen)

        except Exception as exc:
            # Rollback: purga as chaves da nova geração com falha, mantendo a geração anterior 100% intacta
            for k in written_keys:
                try:
                    keyring.delete_password(self.service_name, k)
                except Exception:
                    pass
            raise KeyringStorageError(
                f"Falha ao persistir nova geração de credenciais no keyring (geração anterior intacta): {exc}"
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
                self._purge_generation(active_gen)
                try:
                    keyring.delete_password(self.service_name, self._active_pointer_key)
                except Exception:
                    pass
            self._purge_legacy()
        except Exception:
            pass
