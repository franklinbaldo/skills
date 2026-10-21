# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
"""Módulo de autenticação OAuth 2.0 / OIDC com PKCE para o Jus.br e PDPJ/CNJ."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import secrets
import time
import urllib.parse
from typing import Any

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
CLIENT_ID = "portalexterno-frontend"
DEFAULT_REDIRECT_URI = "https://portaldeservicos.pdpj.jus.br/consulta"


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


ALLOWED_CALLBACK_HOSTS = ("portaldeservicos.pdpj.jus.br", "www.jus.br")
EXPECTED_CALLBACK_PATHS = ("/consulta", "/callback")


def parse_callback_input(callback_input: str, expected_state: str) -> str:
    """Extrai e valida estritamente o authorization code de uma URL de callback.

    Exige:
    1. URL HTTPS completa iniciando com 'https://'.
    2. Host pertencente à lista autorizada de domínios oficiais ('portaldeservicos.pdpj.jus.br' ou 'www.jus.br').
    3. Path autorizado de redirecionamento ('/consulta' ou '/callback').
    4. Parâmetro 'state' obrigatoriamente presente e estritamente idêntico ao expected_state (anti-CSRF).
    5. Parâmetro 'code' obrigatoriamente presente.
    Fragmentos parciais, URLs HTTP inseguras ou códigos isolados são sumariamente rejeitados.
    """
    raw = callback_input.strip()
    if not raw:
        raise JusBrAuthError("Entrada vazia. Forneça a URL de redirecionamento contendo code e state.")

    if not raw.startswith("https://"):
        raise JusBrAuthError(
            "Entrada inválida: é obrigatório fornecer a URL HTTPS completa gerada no redirecionamento "
            "(exemplo: https://portaldeservicos.pdpj.jus.br/consulta?code=...&state=...). Entradas parciais ou inseguras não são permitidas."
        )

    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise JusBrAuthError("Protocolo inválido: a URL de callback deve utilizar HTTPS obrigatoriamente.")

    if parsed.netloc not in ALLOWED_CALLBACK_HOSTS:
        raise JusBrAuthError(
            f"Origem de callback não autorizada: '{parsed.netloc}'. "
            f"Esperado domínio oficial: {', '.join(ALLOWED_CALLBACK_HOSTS)}"
        )

    if parsed.path not in EXPECTED_CALLBACK_PATHS:
        raise JusBrAuthError(
            f"Caminho de callback inválido: '{parsed.path}'. Esperado um dos: {', '.join(EXPECTED_CALLBACK_PATHS)}"
        )
    if parsed.fragment:
        raise JusBrAuthError("Fragmentos não são aceitos na URL de callback.")

    qs = urllib.parse.parse_qs(parsed.query)
    for parameter in ("state", "code", "error"):
        if len(qs.get(parameter, [])) > 1:
            raise JusBrAuthError(f"Parâmetro '{parameter}' repetido na URL de callback.")
    error = qs.get("error", [None])[0]
    if error:
        desc = qs.get("error_description", [""])[0]
        raise JusBrAuthError(f"Erro retornado na autorização do CNJ: {error} ({desc})")

    state = qs.get("state", [None])[0]
    if not state:
        raise OAuthStateMismatchError("Parâmetro 'state' ausente na URL de callback. Possível tentativa de CSRF.")

    if state != expected_state:
        raise OAuthStateMismatchError("O state retornado não confere com o esperado.")

    code = qs.get("code", [None])[0]
    if not code:
        raise JusBrAuthError("Nenhum parâmetro 'code' encontrado na URL informada.")

    return code


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decodifica de forma segura o payload de um token JWT sem validar assinatura."""
    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    parts = clean_token.split(".")
    if len(parts) != 3:
        raise JusBrAuthError("Formato de token inválido: esperado um JWT com 3 partes separadas por ponto.")

    payload_b64 = parts[1]
    padding = "=" * ((4 - len(payload_b64) % 4) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise JusBrAuthError(f"Falha ao decodificar payload do token JWT: {exc}") from exc


def parse_session_input(raw_input: str) -> TokenResponse:
    """Extrai um TokenResponse de um token JWT direto, Bearer ou payload exportado do bookmarklet."""
    raw = raw_input.strip()
    if not raw:
        raise JusBrAuthError("Entrada vazia. Forneça o token ou payload da sessão.")

    candidate_jwt: str | None = None
    if raw.startswith("{") and raw.endswith("}"):
        try:
            data = json.loads(raw)
            all_values = []
            if isinstance(data.get("storage"), dict):
                all_values.extend(data["storage"].values())
            all_values.extend(data.values())

            for val in all_values:
                if isinstance(val, str) and "eyJ" in val:
                    m = re.search(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", val)
                    if m:
                        candidate_jwt = m.group(0)
                        break
        except Exception:
            pass

    if not candidate_jwt:
        m = re.search(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", raw)
        if m:
            candidate_jwt = m.group(0)

    if not candidate_jwt:
        raise JusBrAuthError("Nenhum token JWT válido (iniciado com 'eyJ...') foi encontrado na entrada informada.")

    payload = decode_jwt_payload(candidate_jwt)
    exp = payload.get("exp")
    now = time.time()
    if exp and isinstance(exp, (int, float)):
        expires_in = max(60, int(exp - now))
    else:
        expires_in = 3600

    return TokenResponse(
        access_token=candidate_jwt,
        token_type="Bearer",
        expires_in=expires_in,
        scope=payload.get("scope"),
        created_at=now,
    )


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


def _extract_oab(data: dict[str, Any]) -> str | None:
    """Extrai número de inscrição da OAB se presente no perfil ou vínculo corporativo."""
    if data.get("oab"):
        return str(data["oab"])
    corp = data.get("corporativo")
    if isinstance(corp, list):
        for item in corp:
            if isinstance(item, dict) and item.get("oab"):
                return str(item["oab"])
    return None


def get_userinfo(access_token: str, http_client: httpx.Client | None = None) -> UsuarioJusBr:
    """Consulta dados do perfil do usuário autenticado no UserInfo endpoint, com fallback para claims do JWT."""
    client = http_client or httpx.Client(timeout=15.0)
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = client.get(USERINFO_ENDPOINT, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            try:
                claims = decode_jwt_payload(access_token)
            except Exception:
                claims = {}
            return UsuarioJusBr(
                sub=data.get("sub"),
                name=data.get("name"),
                preferred_username=data.get("preferred_username"),
                cpf=data.get("cpf") or data.get("preferred_username"),
                email=data.get("email"),
                oab=_extract_oab(data) or _extract_oab(claims),
                roles=data.get("roles", []) or (claims.get("roles") if isinstance(claims.get("roles"), list) else []),
            )
    except Exception:
        pass

    # Fallback resiliente: extrai dados de perfil diretamente das claims do JWT se o endpoint falhar
    try:
        claims = decode_jwt_payload(access_token)
        if claims.get("name") or claims.get("preferred_username") or claims.get("sub"):
            roles = claims.get("roles") or []
            if not roles and isinstance(claims.get("realm_access"), dict):
                roles = claims.get("realm_access", {}).get("roles", [])
            return UsuarioJusBr(
                sub=claims.get("sub"),
                name=claims.get("name"),
                preferred_username=claims.get("preferred_username"),
                cpf=claims.get("cpf") or claims.get("preferred_username"),
                email=claims.get("email"),
                oab=_extract_oab(claims),
                roles=roles if isinstance(roles, list) else [],
            )
    except Exception:
        pass

    raise JusBrAuthError(
        f"Erro ao consultar UserInfo ({resp.status_code if 'resp' in locals() else 'conexão'}): falha na API e sem claims no token."
    )


def logout(refresh_token: str | None = None, http_client: httpx.Client | None = None) -> bool:
    """Encerra a sessão no Keycloak do CNJ.

    Retorna True se a revogação remota foi aceita pelo Keycloak, ou False se houve falha ou ausência de token.
    """
    if not refresh_token:
        return False
    client = http_client or httpx.Client(timeout=10.0)
    data = {"client_id": CLIENT_ID, "refresh_token": refresh_token}
    try:
        resp = client.post(LOGOUT_ENDPOINT, data=data)
        if resp.status_code in (200, 204):
            return True
        logger.warning("Keycloak retornou HTTP %s ao revogar sessão: %s", resp.status_code, resp.text)
        return False
    except Exception as exc:
        logger.warning("Falha de rede ao contatar endpoint de logout do Keycloak: %s", exc)
        return False


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
        new_tokens = new_tokens.model_copy(
            update={
                "refresh_token": new_tokens.refresh_token or tokens.refresh_token,
                "refresh_expires_in": new_tokens.refresh_expires_in or tokens.refresh_expires_in,
            }
        )
        self.store.save_tokens(new_tokens)
        return new_tokens

    def refresh(self) -> TokenResponse:
        """Força a renovação dos tokens utilizando o refresh_token."""
        tokens = self.store.load_tokens()
        if not tokens or not tokens.refresh_token:
            raise SessionExpiredError("Nenhum refresh token disponível no keyring.")
        new_tokens = refresh_access_token(tokens.refresh_token, http_client=self.http_client)
        new_tokens = new_tokens.model_copy(
            update={
                "refresh_token": new_tokens.refresh_token or tokens.refresh_token,
                "refresh_expires_in": new_tokens.refresh_expires_in or tokens.refresh_expires_in,
            }
        )
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

    def import_session(self, raw_input: str) -> TokenResponse:
        """Importa e persiste uma sessão diretamente a partir de um JWT ou payload do bookmarklet."""
        tokens = parse_session_input(raw_input)
        self.store.save_tokens(tokens)
        return tokens

    def logout(self) -> bool:
        """Revoga tokens no Keycloak do CNJ e remove do keyring local.

        Retorna True se a revogação remota foi confirmada pelo Keycloak, False caso contrário.
        Os dados locais no keyring são sempre expurgados.
        """
        revogado_remoto = False
        tokens = self.store.load_tokens()
        if tokens and tokens.refresh_token:
            revogado_remoto = logout(tokens.refresh_token, http_client=self.http_client)
        self.store.delete_tokens()
        return revogado_remoto
