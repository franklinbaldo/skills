"""Exceções especializadas para o módulo de autenticação e cliente DESARQ/TJRO."""


class DesarqError(Exception):
    """Exceção base para operações no DESARQ."""


class DesarqAuthError(DesarqError):
    """Exceção base para erros de autenticação e credenciais."""


class KeyringUnavailableError(DesarqAuthError):
    """Keyring do sistema operacional não está disponível ou acessível."""


class KeyringStorageError(DesarqAuthError):
    """Falha ao persistir ou recuperar credencial no keyring."""


class OAuthStateMismatchError(DesarqAuthError):
    """O parâmetro state retornado pelo provedor não coincide com o esperado."""


class OAuthCallbackError(DesarqAuthError):
    """O provedor retornou um erro durante a autorização."""

    def __init__(self, error: str, description: str | None = None) -> None:
        super().__init__(f"Erro de autorização OAuth: {error}" + (f" ({description})" if description else ""))
        self.error = error
        self.description = description


class PKCEVerificationError(DesarqAuthError):
    """Falha na verificação de PKCE durante a troca do código."""


class TokenExpiredError(DesarqAuthError):
    """O access token expirou e não pôde ser utilizado."""


class RefreshTokenRevokedError(DesarqAuthError):
    """O refresh token foi revogado ou a sessão SSO no Keycloak foi encerrada."""


class SessionExpiredError(DesarqAuthError):
    """A sessão está completamente expirada e requer novo login interativo."""


class MFAPendingError(DesarqAuthError):
    """O login requer confirmação de MFA que não foi concluída."""


class KeycloakCommunicationError(DesarqAuthError):
    """Falha de comunicação ou timeout com o Keycloak."""


class DesarqApiError(DesarqError):
    """Exceção base para chamadas à API REST do DESARQ."""


class DesarqUnauthorizedError(DesarqApiError):
    """A API do DESARQ retornou HTTP 401 Unauthorized mesmo após tentativa de refresh."""
