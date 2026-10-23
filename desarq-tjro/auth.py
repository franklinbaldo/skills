"""Módulo de autenticação OAuth 2.0 / OIDC com PKCE para o DESARQ/TJRO."""

from __future__ import annotations

import base64
import hashlib
import http.server
import logging
import secrets
import time
import urllib.parse
import webbrowser
from typing import Any

import httpx
from credentials import CredentialStore
from errors import (
    DesarqAuthError,
    KeycloakCommunicationError,
    OAuthCallbackError,
    OAuthStateMismatchError,
    PKCEVerificationError,
    RefreshTokenRevokedError,
    SessionExpiredError,
)
from models import TokenResponse

logger = logging.getLogger(__name__)

KEYCLOAK_BASE = "https://rhbk.tjro.jus.br/realms/PJRO"
AUTH_ENDPOINT = f"{KEYCLOAK_BASE}/protocol/openid-connect/auth"
TOKEN_ENDPOINT = f"{KEYCLOAK_BASE}/protocol/openid-connect/token"
LOGOUT_ENDPOINT = f"{KEYCLOAK_BASE}/protocol/openid-connect/logout"
CLIENT_ID = "desarq-app"
DEFAULT_PORT = 18274


def generate_pkce() -> tuple[str, str]:
    """Gera code_verifier e code_challenge (S256) compatíveis com RFC 7636."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def generate_state() -> str:
    """Gera um state seguro e imprevisível contra ataques CSRF."""
    return secrets.token_urlsafe(32)


def build_authorization_url(
    redirect_uri: str,
    code_challenge: str,
    state: str,
    idp_hint: str | None = "govbr",
) -> str:
    """Constrói a URL de autorização no Keycloak com PKCE e seleção opcional de IdP."""
    params: dict[str, str] = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    if idp_hint:
        params["kc_idp_hint"] = idp_hint

    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def run_callback_server_and_wait(
    port: int = DEFAULT_PORT,
    expected_state: str = "",
    timeout: float = 120.0,
) -> str:
    """Sobe um servidor HTTP de loopback e aguarda o callback de autorização."""
    result: dict[str, Any] = {"code": None, "error": None}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            # Silencia os logs normais de HTTP para evitar ruído e vazamentos
            pass

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)

            state = query.get("state", [None])[0]
            error = query.get("error", [None])[0]
            error_desc = query.get("error_description", [None])[0]
            code = query.get("code", [None])[0]

            if error:
                result["error"] = OAuthCallbackError(error, error_desc)
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    f"<html><body><h2>Erro na autenticação: {error}</h2><p>{error_desc or ''}</p>"
                    "<p>Você pode fechar esta aba e tentar novamente no terminal.</p></body></html>".encode("utf-8")
                )
                return

            if state != expected_state:
                result["error"] = OAuthStateMismatchError(
                    f"State retornado ({state}) não coincide com o esperado ({expected_state})."
                )
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    "<html><body><h2>Falha de segurança OAuth</h2>"
                    "<p>Parâmetro state inválido. Feche esta aba.</p></body></html>".encode("utf-8")
                )
                return

            if not code:
                result["error"] = DesarqAuthError("Nenhum authorization code retornado no callback.")
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    "<html><body><h2>Código ausente</h2><p>Feche esta aba.</p></body></html>".encode("utf-8")
                )
                return

            result["code"] = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DESARQ - Autenticado</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f8fafc; color: #1e293b; }
        .card { background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); text-align: center; max-width: 420px; }
        .icon { font-size: 3rem; margin-bottom: 1rem; color: #16a34a; }
        h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #0f172a; }
        p { color: #64748b; font-size: 0.95rem; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✓</div>
        <h1>Autenticação concluída!</h1>
        <p>A identidade foi confirmada com sucesso. Você já pode fechar esta aba e retornar ao terminal.</p>
    </div>
</body>
</html>""".encode("utf-8")
            )

    server = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.timeout = 0.5

    start_time = time.time()
    try:
        while time.time() - start_time < timeout:
            server.handle_request()
            if result["code"] or result["error"]:
                break
    finally:
        server.server_close()

    if result["error"]:
        raise result["error"]

    if not result["code"]:
        raise TimeoutError(f"Tempo limite esgotado ({timeout}s) aguardando login no navegador.")

    return result["code"]


def exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    redirect_uri: str,
    http_client: httpx.Client | None = None,
) -> TokenResponse:
    """Troca o authorization code por tokens no Keycloak usando PKCE."""
    client = http_client or httpx.Client(timeout=30.0)
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    try:
        resp = client.post(TOKEN_ENDPOINT, data=data)
    except httpx.RequestError as exc:
        raise KeycloakCommunicationError(f"Falha de conexão com Keycloak ao trocar código: {exc}") from exc

    if resp.status_code == 200:
        return TokenResponse.model_validate(resp.json())

    # Trata erros
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
        raise DesarqAuthError(f"Código de autorização inválido ou expirado: {err_desc}")

    raise DesarqAuthError(f"Falha na emissão de tokens ({resp.status_code}): {err_desc}")


def refresh_access_token(
    refresh_token: str,
    http_client: httpx.Client | None = None,
) -> TokenResponse:
    """Renova o access_token usando o refresh_token no Keycloak."""
    client = http_client or httpx.Client(timeout=30.0)
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    try:
        resp = client.post(TOKEN_ENDPOINT, data=data)
    except httpx.RequestError as exc:
        raise KeycloakCommunicationError(f"Falha de conexão com Keycloak ao renovar token: {exc}") from exc

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
        raise RefreshTokenRevokedError(f"Sessão não está mais ativa no Keycloak: {err_desc}")

    raise DesarqAuthError(f"Erro ao renovar token ({resp.status_code}): {err_desc}")


def logout(
    refresh_token: str | None = None,
    http_client: httpx.Client | None = None,
) -> None:
    """Envia requisição de logout ao Keycloak para encerrar a sessão SSO."""
    if not refresh_token:
        return
    client = http_client or httpx.Client(timeout=10.0)
    data = {
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    }
    try:
        client.post(LOGOUT_ENDPOINT, data=data)
    except Exception:
        # Logout remoto é de melhor esforço
        pass


class AuthService:
    """Serviço de autenticação que orquestra login interativo, renovação e keyring."""

    def __init__(
        self,
        credential_store: CredentialStore | None = None,
        http_client: httpx.Client | None = None,
        port: int = DEFAULT_PORT,
    ) -> None:
        self.store = credential_store or CredentialStore()
        self.http_client = http_client
        self.port = port

    def ensure_valid_tokens(self) -> TokenResponse:
        """Retorna tokens válidos do cache/keyring, renovando se necessário."""
        tokens = self.store.load_tokens()
        if not tokens:
            raise SessionExpiredError("Nenhuma sessão ativa encontrada. Execute 'desarq auth login'.")

        if not tokens.is_access_token_expired():
            return tokens

        # Access token expirou, tenta renovar via refresh_token
        if not tokens.refresh_token or tokens.is_refresh_token_expired():
            raise SessionExpiredError("Sessão expirada. Execute 'desarq auth login'.")

        new_tokens = refresh_access_token(tokens.refresh_token, http_client=self.http_client)
        self.store.save_tokens(new_tokens)
        return new_tokens

    def refresh(self) -> TokenResponse:
        """Força a renovação dos tokens usando o refresh_token atual."""
        tokens = self.store.load_tokens()
        if not tokens or not tokens.refresh_token:
            raise SessionExpiredError("Nenhum refresh token disponível para renovar. Faça login.")
        new_tokens = refresh_access_token(tokens.refresh_token, http_client=self.http_client)
        self.store.save_tokens(new_tokens)
        return new_tokens

    def login(
        self,
        open_browser: bool = True,
        timeout: float = 180.0,
        force: bool = False,
        idp_hint: str | None = "govbr",
    ) -> TokenResponse:
        """Executa o fluxo completo de login via navegador com PKCE e servidor local."""
        if not force:
            try:
                return self.ensure_valid_tokens()
            except (SessionExpiredError, RefreshTokenRevokedError):
                pass

        verifier, challenge = generate_pkce()
        state = generate_state()
        redirect_uri = f"http://localhost:{self.port}/callback"

        auth_url = build_authorization_url(
            redirect_uri=redirect_uri,
            code_challenge=challenge,
            state=state,
            idp_hint=idp_hint,
        )

        if open_browser:
            webbrowser.open(auth_url)

        code = run_callback_server_and_wait(
            port=self.port,
            expected_state=state,
            timeout=timeout,
        )

        tokens = exchange_code_for_tokens(
            code=code,
            code_verifier=verifier,
            redirect_uri=redirect_uri,
            http_client=self.http_client,
        )

        self.store.save_tokens(tokens)
        return tokens

    def logout(self) -> None:
        """Revoga tokens no Keycloak e limpa o keyring local."""
        tokens = self.store.load_tokens()
        if tokens and tokens.refresh_token:
            logout(tokens.refresh_token, http_client=self.http_client)
        self.store.delete_tokens()
