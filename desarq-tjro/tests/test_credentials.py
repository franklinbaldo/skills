"""Testes de contrato para armazenamento seguro de credenciais no keyring."""

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
    store = CredentialStore(service_name="test-desarq")
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


def test_load_empty_store(mock_keyring):
    store = CredentialStore(service_name="test-desarq")
    assert store.load_tokens() is None


def test_delete_tokens(mock_keyring):
    store = CredentialStore(service_name="test-desarq")
    tokens = TokenResponse(
        access_token="secret_at",
        refresh_token="secret_rt",
        expires_in=300,
    )
    store.save_tokens(tokens)
    assert store.load_tokens() is not None

    store.delete_tokens()
    assert store.load_tokens() is None


def test_delete_nonexistent_does_not_fail(mock_keyring):
    store = CredentialStore(service_name="test-desarq")
    # Deletar quando vazio não deve quebrar
    store.delete_tokens()
    assert store.load_tokens() is None


def test_keyring_storage_error_on_save():
    store = CredentialStore(service_name="test-desarq")
    tokens = TokenResponse(access_token="at", expires_in=300)

    with patch("credentials.keyring.set_password", side_effect=Exception("Disk full / permission denied")):
        with pytest.raises(KeyringStorageError, match="Falha ao gravar credenciais"):
            store.save_tokens(tokens)


def test_keyring_storage_error_on_corrupt_data():
    store = CredentialStore(service_name="test-desarq")
    with patch("credentials.keyring.get_password", return_value="invalid-json-data"):
        with pytest.raises(KeyringStorageError, match="corrompidas"):
            store.load_tokens()


def test_keyring_unavailable_error():
    store = CredentialStore(service_name="test-desarq")
    with patch("credentials.keyring.get_keyring", side_effect=Exception("No backend available")):
        with pytest.raises(KeyringUnavailableError):
            store.check_availability()


def test_tokens_never_leaked_in_repr():
    tokens = TokenResponse(
        access_token="secret_super_confidential_token_xyz",
        refresh_token="secret_refresh_token_very_long_abc",
        expires_in=300,
    )
    rep = repr(tokens)
    assert "secret_super_confidential_token_xyz" not in rep
    assert "secret_refresh_token_very_long_abc" not in rep
    assert "..." in rep


def test_save_and_load_large_tokens_chunking(mock_keyring):
    store = CredentialStore(service_name="test-desarq")
    # Simula access_token longo típico de JWT assinado do Keycloak (3000 chars)
    long_access_token = "ey" + "a" * 3000
    tokens = TokenResponse(
        access_token=long_access_token,
        refresh_token="rt_" + "b" * 1500,
        expires_in=300,
    )

    store.save_tokens(tokens)

    # Verifica que nenhum chunk individual excedeu 512 caracteres
    for (service, username), value in mock_keyring.items():
        assert len(value) <= 512, f"Chave {username} excedeu 512 caracteres ({len(value)} bytes)"

    loaded = store.load_tokens()
    assert loaded is not None
    assert loaded.access_token == long_access_token
    assert loaded.refresh_token == tokens.refresh_token

    # Ao deletar, limpa todos os chunks
    store.delete_tokens()
    assert len(mock_keyring) == 0
    assert store.load_tokens() is None
