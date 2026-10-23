# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
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
        token_type="Bearer",
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
        token_type="Bearer",
        refresh_token="rt_" + "y" * 1200,
        expires_in=300,
    )

    store.save_tokens(tokens)

    for (service, username), value in mock_keyring.items():
        assert len(value.encode("utf-8")) <= 512, f"Chave {username} excedeu 512 bytes"

    loaded = store.load_tokens()
    assert loaded is not None
    assert loaded.access_token == long_access_token

    store.delete_tokens()
    assert len(mock_keyring) == 0


def test_chunking_respects_utf8_byte_limit(mock_keyring):
    store = CredentialStore(service_name="test-jusbr")
    tokens = TokenResponse(access_token="ação-" * 300, token_type="Bearer", expires_in=300)
    store.save_tokens(tokens)
    for (_, username), value in mock_keyring.items():
        if "_chunk_" in username:
            assert len(value.encode("utf-8")) <= 512
    assert store.load_tokens().access_token == tokens.access_token


def test_delete_tokens(mock_keyring):
    store = CredentialStore(service_name="test-jusbr")
    tokens = TokenResponse(access_token="at", token_type="Bearer", refresh_token="rt", expires_in=300)
    store.save_tokens(tokens)
    assert store.load_tokens() is not None

    store.delete_tokens()
    assert store.load_tokens() is None


def test_delete_tokens_reports_partial_keyring_failure(mock_keyring):
    store = CredentialStore(service_name="test-jusbr")
    store.save_tokens(TokenResponse(access_token="a" * 1800, token_type="Bearer", expires_in=300))

    def fail_chunk_delete(service, username):
        if username.endswith("_chunk_0"):
            raise OSError("credential manager unavailable")
        key = (service, username)
        if key not in mock_keyring:
            raise KeyError(username)
        del mock_keyring[key]

    with patch("credentials.keyring.delete_password", side_effect=fail_chunk_delete):
        with pytest.raises(KeyringStorageError, match="permaneceram no keyring"):
            store.delete_tokens()


def test_keyring_storage_error_on_save():
    store = CredentialStore(service_name="test-jusbr")
    tokens = TokenResponse(access_token="at", token_type="Bearer", expires_in=300)

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
    old_tokens = TokenResponse(
        access_token="old_access_token_" + "o" * 1800,
        token_type="Bearer",
        refresh_token="old_rt_" + "r" * 900,
        expires_in=300,
    )
    store.save_tokens(old_tokens)
    old_pointer = mock_keyring[("test-jusbr", "current_session_active_gen")]
    assert store.load_tokens().access_token == old_tokens.access_token

    # Tentativa de salvar novos tokens com falha no meio
    new_tokens = TokenResponse(
        access_token="new_" + "z" * 1500,
        token_type="Bearer",
        refresh_token="new_rt",
        expires_in=300,
    )

    calls = 0

    def failing_set_password(service, username, password):
        nonlocal calls
        calls += 1
        if username.endswith("_chunk_1") and "gen_" in username:
            raise Exception("Quota exceeded in WinVault")
        mock_keyring[(service, username)] = password

    with patch("credentials.keyring.set_password", side_effect=failing_set_password):
        with pytest.raises(KeyringStorageError, match="geração anterior restaurada"):
            store.save_tokens(new_tokens)

    # Verifica que a sessão antiga não foi perdida
    assert store.load_tokens() is not None
    assert store.load_tokens().access_token == old_tokens.access_token
    assert mock_keyring[("test-jusbr", "current_session_active_gen")] == old_pointer


def test_pointer_write_that_persists_then_raises_restores_old_generation(mock_keyring):
    store = CredentialStore(service_name="test-jusbr")
    old_tokens = TokenResponse(
        access_token="old_access_token", token_type="Bearer", refresh_token="old_rt", expires_in=300
    )
    store.save_tokens(old_tokens)
    old_pointer = mock_keyring[("test-jusbr", "current_session_active_gen")]

    def real_set(service, username, password):
        mock_keyring[(service, username)] = password

    def fail_after_pointer_write(service, username, password):
        real_set(service, username, password)
        if username == "current_session_active_gen" and password != old_pointer:
            raise OSError("backend failed after write")

    with patch("credentials.keyring.set_password", side_effect=fail_after_pointer_write):
        with pytest.raises(KeyringStorageError):
            store.save_tokens(TokenResponse(access_token="new_access_token", token_type="Bearer", expires_in=300))

    assert mock_keyring[("test-jusbr", "current_session_active_gen")] == old_pointer
    assert store.load_tokens().access_token == "old_access_token"
