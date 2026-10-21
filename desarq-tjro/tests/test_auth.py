"""Testes de contrato e integração simulada para o fluxo OAuth/OIDC com PKCE."""

import base64
import hashlib
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import (
    CLIENT_ID,
    AuthService,
    build_authorization_url,
    exchange_code_for_tokens,
    generate_pkce,
    generate_state,
    refresh_access_token,
)
from errors import (
    KeycloakCommunicationError,
    OAuthCallbackError,
    OAuthStateMismatchError,
    PKCEVerificationError,
    RefreshTokenRevokedError,
    SessionExpiredError,
)
from models import TokenResponse


def test_pkce_generation():
    verifier, challenge = generate_pkce()
    # RFC 7636: verifier entre 43 e 128 chars
    assert 43 <= len(verifier) <= 128
    assert re.match(r"^[A-Za-z0-9_-]+$", verifier)

    # Checagem do cálculo S256
    expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(expected_digest).decode("ascii").rstrip("=")
    assert challenge == expected_challenge


def test_state_generation():
    state1 = generate_state()
    state2 = generate_state()
    assert len(state1) >= 16
    assert state1 != state2


def test_build_authorization_url():
    url = build_authorization_url(
        redirect_uri="http://localhost:18274/callback",
        code_challenge="xyz123challenge",
        state="state_abc",
        idp_hint="govbr",
    )
    assert url.startswith("https://rhbk.tjro.jus.br/realms/PJRO/protocol/openid-connect/auth")
    assert f"client_id={CLIENT_ID}" in url
    assert "response_type=code" in url
    assert "code_challenge=xyz123challenge" in url
    assert "code_challenge_method=S256" in url
    assert "state=state_abc" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A18274%2Fcallback" in url
    assert "kc_idp_hint=govbr" in url


def test_build_authorization_url_without_idp():
    url = build_authorization_url(
        redirect_uri="http://localhost:18274/callback",
        code_challenge="xyz123challenge",
        state="state_abc",
        idp_hint=None,
    )
    assert "kc_idp_hint" not in url


def test_exchange_code_success():
    fake_response = {
        "access_token": "valid_access_token_123",
        "token_type": "Bearer",
        "expires_in": 300,
        "refresh_token": "valid_refresh_token_456",
        "refresh_expires_in": 1800,
    }

    mock_client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=fake_response)))

    tokens = exchange_code_for_tokens(
        code="auth_code_xyz",
        code_verifier="pkce_verifier_abc",
        redirect_uri="http://localhost:18274/callback",
        http_client=mock_client,
    )

    assert tokens.access_token == "valid_access_token_123"
    assert tokens.refresh_token == "valid_refresh_token_456"
    assert tokens.expires_in == 300


def test_exchange_code_invalid_grant_pkce_failure():
    fake_error = {
        "error": "invalid_grant",
        "error_description": "PKCE verification failed",
    }
    mock_client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(400, json=fake_error)))

    with pytest.raises(PKCEVerificationError, match="PKCE verification failed"):
        exchange_code_for_tokens(
            code="bad_code",
            code_verifier="wrong_verifier",
            redirect_uri="http://localhost:18274/callback",
            http_client=mock_client,
        )


def test_exchange_code_network_error():
    def raise_connect_error(req):
        raise httpx.ConnectError("Connection refused")

    mock_client = httpx.Client(transport=httpx.MockTransport(raise_connect_error))

    with pytest.raises(KeycloakCommunicationError, match="Falha de conexão com Keycloak"):
        exchange_code_for_tokens(
            code="code",
            code_verifier="verifier",
            redirect_uri="http://localhost:18274/callback",
            http_client=mock_client,
        )


def test_refresh_token_success():
    fake_response = {
        "access_token": "new_access_token_789",
        "token_type": "Bearer",
        "expires_in": 300,
        "refresh_token": "rotated_refresh_token_101",
        "refresh_expires_in": 1800,
    }
    mock_client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=fake_response)))

    tokens = refresh_access_token(
        refresh_token="old_refresh_token",
        http_client=mock_client,
    )
    assert tokens.access_token == "new_access_token_789"
    assert tokens.refresh_token == "rotated_refresh_token_101"


def test_refresh_token_revoked():
    fake_error = {
        "error": "invalid_grant",
        "error_description": "Session not active",
    }
    mock_client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(400, json=fake_error)))

    with pytest.raises(RefreshTokenRevokedError, match="Sessão não está mais ativa"):
        refresh_access_token(
            refresh_token="revoked_token",
            http_client=mock_client,
        )


def test_auth_service_ensure_valid_token_uses_cached():
    mock_store = MagicMock()
    # Token válido criado há 5 segundos
    valid_tokens = TokenResponse(
        access_token="cached_at",
        refresh_token="cached_rt",
        expires_in=300,
        refresh_expires_in=1800,
    )
    mock_store.load_tokens.return_value = valid_tokens

    service = AuthService(credential_store=mock_store)
    tokens = service.ensure_valid_tokens()
    assert tokens.access_token == "cached_at"
    # Não deve ter chamado save nem feito refresh
    mock_store.save_tokens.assert_not_called()


def test_auth_service_ensure_valid_token_refreshes_when_expired():
    mock_store = MagicMock()
    # Token expirado (expires_in=-10)
    expired_tokens = TokenResponse(
        access_token="expired_at",
        refresh_token="valid_rt",
        expires_in=-10,
        refresh_expires_in=1800,
    )
    mock_store.load_tokens.return_value = expired_tokens

    new_tokens = TokenResponse(
        access_token="new_refreshed_at",
        refresh_token="new_rotated_rt",
        expires_in=300,
        refresh_expires_in=1800,
    )

    with patch("auth.refresh_access_token", return_value=new_tokens) as mock_refresh:
        service = AuthService(credential_store=mock_store)
        result = service.ensure_valid_tokens()

        assert result.access_token == "new_refreshed_at"
        mock_refresh.assert_called_once_with("valid_rt", http_client=None)
        mock_store.save_tokens.assert_called_once_with(new_tokens)


def test_auth_service_ensure_valid_token_raises_when_no_session():
    mock_store = MagicMock()
    mock_store.load_tokens.return_value = None

    service = AuthService(credential_store=mock_store)
    with pytest.raises(SessionExpiredError, match="Nenhuma sessão ativa encontrada"):
        service.ensure_valid_tokens()


def test_logout():
    mock_store = MagicMock()
    tokens = TokenResponse(
        access_token="at",
        refresh_token="rt",
        expires_in=300,
    )
    mock_store.load_tokens.return_value = tokens

    mock_client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(204)))

    service = AuthService(credential_store=mock_store, http_client=mock_client)
    service.logout()

    mock_store.delete_tokens.assert_called_once()


def test_callback_server_success():
    import threading

    from auth import run_callback_server_and_wait

    state = "test_expected_state_123"
    port = 19876

    def client_call():
        import time

        time.sleep(0.1)
        httpx.get(f"http://127.0.0.1:{port}/callback?code=mock_code_abc&state={state}")

    t = threading.Thread(target=client_call)
    t.start()

    code = run_callback_server_and_wait(port=port, expected_state=state, timeout=2.0)
    t.join()

    assert code == "mock_code_abc"


def test_callback_server_state_mismatch():
    import threading

    from auth import run_callback_server_and_wait

    state = "expected_state_real"
    port = 19877

    def client_call():
        import time

        time.sleep(0.1)
        httpx.get(f"http://127.0.0.1:{port}/callback?code=mock_code&state=wrong_attacker_state")

    t = threading.Thread(target=client_call)
    t.start()

    with pytest.raises(OAuthStateMismatchError):
        run_callback_server_and_wait(port=port, expected_state=state, timeout=2.0)
    t.join()


def test_callback_server_provider_error():
    import threading

    from auth import run_callback_server_and_wait

    state = "expected_state_abc"
    port = 19878

    def client_call():
        import time

        time.sleep(0.1)
        httpx.get(
            f"http://127.0.0.1:{port}/callback?error=access_denied&error_description=Usuario+cancelou+ou+mfa+pendente&state={state}"
        )

    t = threading.Thread(target=client_call)
    t.start()

    with pytest.raises(OAuthCallbackError, match="access_denied"):
        run_callback_server_and_wait(port=port, expected_state=state, timeout=2.0)
    t.join()


def test_callback_server_timeout():
    from auth import run_callback_server_and_wait

    with pytest.raises(TimeoutError, match="Tempo limite esgotado"):
        run_callback_server_and_wait(port=19879, expected_state="any", timeout=0.2)
