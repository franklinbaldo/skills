"""Testes unitários para o fluxo de autenticação OAuth 2.0 / PKCE em jus-br."""

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
    parse_callback_input,
    refresh_access_token,
)
from errors import (
    JusBrAuthError,
    OAuthStateMismatchError,
    RefreshTokenRevokedError,
    SessionExpiredError,
)
from models import TokenResponse


def test_pkce_generation():
    verifier, challenge = generate_pkce()
    assert 43 <= len(verifier) <= 128
    assert re.match(r"^[A-Za-z0-9_-]+$", verifier)

    expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(expected_digest).decode("ascii").rstrip("=")
    assert challenge == expected_challenge


def test_build_authorization_url():
    url = build_authorization_url(code_challenge="xyz123", state="state456")
    assert "https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth" in url
    assert f"client_id={CLIENT_ID}" in url
    assert "code_challenge=xyz123" in url
    assert "code_challenge_method=S256" in url
    assert "state=state456" in url


def test_parse_callback_input_from_full_url():
    url = "https://www.jus.br/?code=code_abc_123&state=state_xyz_789"
    code = parse_callback_input(url, expected_state="state_xyz_789")
    assert code == "code_abc_123"


def test_parse_callback_input_state_mismatch():
    url = "https://www.jus.br/?code=code_abc_123&state=attacker_state"
    with pytest.raises(OAuthStateMismatchError, match="State retornado"):
        parse_callback_input(url, expected_state="expected_state")


def test_parse_callback_input_missing_state():
    url = "https://www.jus.br/callback?code=code_abc_123"
    with pytest.raises(OAuthStateMismatchError, match="Parâmetro 'state' ausente"):
        parse_callback_input(url, expected_state="state_xyz_789")


def test_parse_callback_input_isolated_code_rejected():
    with pytest.raises(JusBrAuthError, match="código isolado sem contexto"):
        parse_callback_input("just_a_random_code_without_url", expected_state="state_xyz_789")


def test_parse_callback_input_unauthorized_host():
    url = "https://attacker.evil.com/callback?code=code_abc_123&state=s1"
    with pytest.raises(JusBrAuthError, match="Origem de callback não autorizada"):
        parse_callback_input(url, expected_state="s1")


def test_parse_callback_input_with_error():
    url = "https://www.jus.br/?error=access_denied&error_description=Cancelado&state=s1"
    with pytest.raises(JusBrAuthError, match="Erro retornado na autorização do CNJ"):
        parse_callback_input(url, expected_state="s1")


def test_exchange_code_success():
    fake_response = {
        "access_token": "valid_pdpj_at",
        "token_type": "Bearer",
        "expires_in": 300,
        "refresh_token": "valid_pdpj_rt",
        "refresh_expires_in": 1800,
    }
    mock_client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=fake_response)))

    tokens = exchange_code_for_tokens(
        code="code123",
        code_verifier="verifier456",
        http_client=mock_client,
    )
    assert tokens.access_token == "valid_pdpj_at"
    assert tokens.refresh_token == "valid_pdpj_rt"


def test_refresh_token_revoked():
    fake_error = {"error": "invalid_grant", "error_description": "Session expired"}
    mock_client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(400, json=fake_error)))

    with pytest.raises(RefreshTokenRevokedError, match="Sessão não está mais ativa"):
        refresh_access_token("bad_rt", http_client=mock_client)


def test_auth_service_ensure_valid_token_cached():
    mock_store = MagicMock()
    valid_tokens = TokenResponse(
        access_token="at_cached",
        refresh_token="rt_cached",
        expires_in=300,
    )
    mock_store.load_tokens.return_value = valid_tokens

    service = AuthService(credential_store=mock_store)
    tokens = service.ensure_valid_tokens()
    assert tokens.access_token == "at_cached"
    mock_store.save_tokens.assert_not_called()


def test_auth_service_ensure_valid_token_refreshes_when_expired():
    mock_store = MagicMock()
    expired_tokens = TokenResponse(
        access_token="expired_at",
        refresh_token="valid_rt",
        expires_in=-10,
    )
    mock_store.load_tokens.return_value = expired_tokens

    new_tokens = TokenResponse(
        access_token="refreshed_at",
        refresh_token="new_rt",
        expires_in=300,
    )

    with patch("auth.refresh_access_token", return_value=new_tokens) as mock_refresh:
        service = AuthService(credential_store=mock_store)
        res = service.ensure_valid_tokens()
        assert res.access_token == "refreshed_at"
        mock_refresh.assert_called_once_with("valid_rt", http_client=None)
        mock_store.save_tokens.assert_called_once_with(new_tokens)


def test_auth_service_raises_when_no_session():
    mock_store = MagicMock()
    mock_store.load_tokens.return_value = None

    service = AuthService(credential_store=mock_store)
    with pytest.raises(SessionExpiredError):
        service.ensure_valid_tokens()


def test_logout_remote_success_and_failure():
    from auth import logout

    # Sucesso 204
    mock_ok = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(204)))
    assert logout("some_rt", http_client=mock_ok) is True

    # Falha 500
    mock_fail = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(500, text="Internal error")))
    assert logout("some_rt", http_client=mock_fail) is False

    # Sem refresh token
    assert logout(None) is False
