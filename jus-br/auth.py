"""Módulo de autenticação OAuth 2.0 / OIDC com PKCE para o Jus.br e PDPJ/CNJ."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import urllib.parse

import httpx
from credentials import CredentialStore
from errors import (
    JusBrAuthError,
    OAuthStateMismatchError,
    PKCEVerificationError,
    RefreshTokenRevokedError,
    SessionExpiredError,
)
from models import TokenResponse, UsuarioJusBr

logger = logging.getLogger(__name__)

KEYCLOAK_BASE = "https://sso.cloud.pje.jus.br/auth/realms/pje"
AUTH_ENDPOINT = f"{KEYCLOAK_BASE}/protocol/openid-connect/auth"
TOKEN_ENDPOINT = f"{KEYCLOAK_BASE}/protocol/openid-connect/token"
LOGOUT_ENDPOINT = f"{KEYCLOAK_BASE}/protocol/openid-connect/logout"
USERINFO_ENDPOINT = f"{KEYCLOAK_BASE}/protocol/openid-connect/userinfo"
CLIENT_ID = "jusbr"
DEFAULT_REDIRECT_URI = "https://www.jus.br/callback"


def generate_pkce() -> tuple[str, str]:
    """Gera code_verifier e code_challenge (S256) compatíveis com RFC 7636."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def generate_state() -> str:
    """Gera state criptograficamente seguro contra CSRF."""
    return secrets.token_urlsafe(32)


def build_authorization_url(
    code_challenge: str,
    state: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    client_id: str = CLIENT_ID,
) -> str:
    """Constrói a URL de autorização no Keycloak da PDPJ."""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def parse_callback_input(callback_input: str, expected_state: str) -> str:
    """Extrai o authorization code de uma URL colada ou string com validação de state."""
    raw = callback_input.strip()
    if "?" in raw or "&" in raw or raw.startswith("http"):
        parsed = urllib.parse.urlparse(raw)
        qs = urllib.parse.parse_qs(parsed.query or parsed.fragment)
        error = qs.get("error", [None])[0]
        if error:
            desc = qs.get("error_description", [""])[0]
            raise JusBrAuthError(f"Erro retornado na autorização do CNJ: {error} ({desc})")

        state = qs.get("state", [None])[0]
        if state and state != expected_state:
            raise OAuthStateMismatchError(f"State retornado ({state}) não confere com o esperado ({expected_state}).")

        code = qs.get("code", [None])[0]
        if not code:
            raise JusBrAuthError("Nenhum parâmetro 'code' encontrado na URL informada.")
        return code

    # Caso o usuário tenha colado diretamente o código
    return raw


def exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    client_id: str = CLIENT_ID,
    http_client: httpx.Client | None = None,
) -> TokenResponse:
    """Troca o authorization code por tokens no Keycloak da PDPJ usando PKCE."""
    client = http_client or httpx.Client(timeout=30.0)
    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    try:
        resp = client.post(TOKEN_ENDPOINT, data=data)
    except httpx.RequestError as exc:
        raise JusBrAuthError(f"Falha de conexão com Keycloak da PDPJ: {exc}") from exc

    if resp.status_code == 200:
        return TokenResponse.model_validate(resp.json())

    error_payload = {}
    try:
        error_payload = resp.json()
    except Exception:
        pass

    err_code = error_payload.get("error", "")
    err_desc = error_payload.get("error_description", resp.text)

    if err_code == "invalid_grant":
        if "pkce" in err_desc.lower():
            raise PKCEVerificationError(f"Falha na validação de PKCE: {err_desc}")
        raise JusBrAuthError(f"Código de autorização inválido ou expirado: {err_desc}")

    raise JusBrAuthError(f"Falha na emissão de tokens da PDPJ ({resp.status_code}): {err_desc}")


def refresh_access_token(
    refresh_token: str,
    client_id: str = CLIENT_ID,
    http_client: httpx.Client | None = None,
) -> TokenResponse:
    """Renova o access token usando o refresh token no Keycloak da PDPJ."""
    client = http_client or httpx.Client(timeout=30.0)
    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    try:
        resp = client.post(TOKEN_ENDPOINT, data=data)
    except httpx.RequestError as exc:
        raise JusBrAuthError(f"Falha de conexão com Keycloak ao renovar token: {exc}") from exc

    if resp.status_code == 200:
        return TokenResponse.model_validate(resp.json())

    error_payload = {}
    try:
        error_payload = resp.json()
    except Exception:
        pass

    err_code = error_payload.get("error", "")
    err_desc = error_payload.get("error_description", resp.text)

    if err_code == "invalid_grant":
        raise RefreshTokenRevokedError(f"Sessão não está mais ativa no Keycloak da PDPJ: {err_desc}")

    raise JusBrAuthError(f"Erro ao renovar token da PDPJ ({resp.status_code}): {err_desc}")


def get_userinfo(access_token: str, http_client: httpx.Client | None = None) -> UsuarioJusBr:
    """Consulta dados do perfil do usuário autenticado no UserInfo endpoint."""
    client = http_client or httpx.Client(timeout=15.0)
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = client.get(USERINFO_ENDPOINT, headers=headers)
    except httpx.RequestError as exc:
        raise JusBrAuthError(f"Falha ao conectar ao UserInfo da PDPJ: {exc}") from exc

    if resp.status_code == 200:
        data = resp.json()
        return UsuarioJusBr(
            sub=data.get("sub"),
            name=data.get("name"),
            preferred_username=data.get("preferred_username"),
            cpf=data.get("cpf") or data.get("preferred_username"),
            email=data.get("email"),
            roles=data.get("roles", []),
        )

    raise JusBrAuthError(f"Erro ao consultar UserInfo ({resp.status_code}): {resp.text}")


def logout(refresh_token: str | None = None, http_client: httpx.Client | None = None) -> None:
    """Encerra a sessão no Keycloak do CNJ."""
    if not refresh_token:
        return
    client = http_client or httpx.Client(timeout=10.0)
    data = {"client_id": CLIENT_ID, "refresh_token": refresh_token}
    try:
        client.post(LOGOUT_ENDPOINT, data=data)
    except Exception:
        pass


class AuthService:
    """Orquestra o ciclo de vida da autenticação com o Keycloak da PDPJ/Jus.br."""

    def __init__(
        self,
        credential_store: CredentialStore | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.store = credential_store or CredentialStore()
        self.http_client = http_client

    def ensure_valid_tokens(self) -> TokenResponse:
        """Retorna tokens válidos do keyring, renovando via refresh token se necessário."""
        tokens = self.store.load_tokens()
        if not tokens:
            raise SessionExpiredError("Nenhuma sessão ativa encontrada. Execute 'jusbr auth login'.")

        if not tokens.is_access_token_expired():
            return tokens

        if not tokens.refresh_token or tokens.is_refresh_token_expired():
            raise SessionExpiredError("Sessão da PDPJ expirada. Execute 'jusbr auth login'.")

        new_tokens = refresh_access_token(tokens.refresh_token, http_client=self.http_client)
        self.store.save_tokens(new_tokens)
        return new_tokens

    def refresh(self) -> TokenResponse:
        """Força a renovação dos tokens utilizando o refresh_token."""
        tokens = self.store.load_tokens()
        if not tokens or not tokens.refresh_token:
            raise SessionExpiredError("Nenhum refresh token disponível no keyring.")
        new_tokens = refresh_access_token(tokens.refresh_token, http_client=self.http_client)
        self.store.save_tokens(new_tokens)
        return new_tokens

    def start_login(self) -> tuple[str, str, str]:
        """Inicia fluxo PKCE e retorna (auth_url, code_verifier, state)."""
        verifier, challenge = generate_pkce()
        state = generate_state()
        url = build_authorization_url(code_challenge=challenge, state=state)
        return url, verifier, state

    def complete_login(self, callback_input: str, code_verifier: str, state: str) -> TokenResponse:
        """Conclui a troca de código e persiste os tokens no keyring."""
        code = parse_callback_input(callback_input, expected_state=state)
        tokens = exchange_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            http_client=self.http_client,
        )
        self.store.save_tokens(tokens)
        return tokens

    def logout(self) -> None:
        """Revoga tokens no Keycloak do CNJ e remove do keyring."""
        tokens = self.store.load_tokens()
        if tokens and tokens.refresh_token:
            logout(tokens.refresh_token, http_client=self.http_client)
        self.store.delete_tokens()
