"""Testes unitários para armazenamento de credenciais no keyring em jus-br."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from credentials import CredentialStore
from errors import KeyringStorageError, KeyringUnavailableError
from models import TokenResponse


@pytest.fixture
def mock_keyring():
    store = {}

    def get_password(service, username):
        return store.get((service, username))

    def set_password(service, username, password):
        store[(service, username)] = password

    def delete_password(service, username):
        if (service, username) in store:
            del store[(service, username)]
        else:
            raise Exception("Password not found")

    with (
        patch("credentials.keyring.get_password", side_effect=get_password),
        patch("credentials.keyring.set_password", side_effect=set_password),
        patch("credentials.keyring.delete_password", side_effect=delete_password),
    ):
        yield store


def test_save_and_load_tokens(mock_keyring):
    store = CredentialStore(service_name="test-jusbr")
    tokens = TokenResponse(
        access_token="secret_at_12345678",
        refresh_token="secret_rt_87654321",
        expires_in=300,
        refresh_expires_in=1800,
    )

    store.save_tokens(tokens)
    loaded = store.load_tokens()

    assert loaded is not None
    assert loaded.access_token == "secret_at_12345678"
    assert loaded.refresh_token == "secret_rt_87654321"
    assert loaded.expires_in == 300


def test_chunking_large_tokens(mock_keyring):
    store = CredentialStore(service_name="test-jusbr")
    long_access_token = "ey" + "x" * 2500
    tokens = TokenResponse(
        access_token=long_access_token,
        refresh_token="rt_" + "y" * 1200,
        expires_in=300,
    )

    store.save_tokens(tokens)

    for (service, username), value in mock_keyring.items():
        assert len(value) <= 512, f"Chave {username} excedeu 512 chars ({len(value)} bytes)"

    loaded = store.load_tokens()
    assert loaded is not None
    assert loaded.access_token == long_access_token

    store.delete_tokens()
    assert len(mock_keyring) == 0


def test_delete_tokens(mock_keyring):
    store = CredentialStore(service_name="test-jusbr")
    tokens = TokenResponse(access_token="at", refresh_token="rt", expires_in=300)
    store.save_tokens(tokens)
    assert store.load_tokens() is not None

    store.delete_tokens()
    assert store.load_tokens() is None


def test_keyring_storage_error_on_save():
    store = CredentialStore(service_name="test-jusbr")
    tokens = TokenResponse(access_token="at", expires_in=300)

    with patch("credentials.keyring.set_password", side_effect=Exception("Disk full")):
        with pytest.raises(KeyringStorageError, match="Falha ao persistir nova geração"):
            store.save_tokens(tokens)


def test_keyring_unavailable_error():
    store = CredentialStore(service_name="test-jusbr")
    with patch("credentials.keyring.get_keyring", side_effect=Exception("No backend")):
        with pytest.raises(KeyringUnavailableError):
            store.check_availability()


def test_transactional_save_preserves_old_tokens_on_failure(mock_keyring):
    store = CredentialStore(service_name="test-jusbr")
    old_tokens = TokenResponse(access_token="old_access_token", refresh_token="old_rt", expires_in=300)
    store.save_tokens(old_tokens)
    assert store.load_tokens().access_token == "old_access_token"

    # Tentativa de salvar novos tokens com falha no meio
    new_tokens = TokenResponse(
        access_token="new_" + "z" * 1500,
        refresh_token="new_rt",
        expires_in=300,
    )

    calls = 0

    def failing_set_password(service, username, password):
        nonlocal calls
        calls += 1
        if "chunk_1" in username:
            raise Exception("Quota exceeded in WinVault")
        mock_keyring[(service, username)] = password

    with patch("credentials.keyring.set_password", side_effect=failing_set_password):
        with pytest.raises(KeyringStorageError, match="geração anterior intacta"):
            store.save_tokens(new_tokens)

    # Verifica que a sessão antiga não foi perdida
    assert store.load_tokens() is not None
    assert store.load_tokens().access_token == "old_access_token"


def test_roundtrip_verification_failure_aborts_commit(mock_keyring):
    """Testa que se a releitura/validação após a escrita falhar, o ponteiro não comuta."""
    store = CredentialStore(service_name="test-jusbr")
    initial_tokens = TokenResponse(access_token="initial_at", refresh_token="initial_rt", expires_in=300)
    store.save_tokens(initial_tokens)
    assert store.load_tokens().access_token == "initial_at"

    new_tokens = TokenResponse(access_token="corrupt_at", refresh_token="corrupt_rt", expires_in=300)

    def failing_get_password(service, username):
        # Simula corrupção de leitura na verificação de roundtrip da nova geração
        if "gen_" in username and "active_gen" not in username:
            return None
        return mock_keyring.get((service, username))

    with patch("credentials.keyring.get_password", side_effect=failing_get_password):
        with pytest.raises(KeyringStorageError, match="Verificação de gravação falhou"):
            store.save_tokens(new_tokens)

    # Garante que a sessão original permaneceu intacta
    assert store.load_tokens().access_token == "initial_at"
