"""Exceções especializadas para a integração com o portal Jus.br e PDPJ/CNJ."""


class JusBrError(Exception):
    """Exceção base para operações no Jus.br / PDPJ."""


class JusBrAuthError(JusBrError):
    """Exceção base para erros de autenticação no Keycloak do CNJ."""


class KeyringUnavailableError(JusBrAuthError):
    """Keyring do sistema operacional não está disponível ou acessível."""


class KeyringStorageError(JusBrAuthError):
    """Falha ao persistir ou recuperar credencial no keyring."""


class OAuthStateMismatchError(JusBrAuthError):
    """O parâmetro state retornado não coincide com o esperado."""


class PKCEVerificationError(JusBrAuthError):
    """Falha na verificação de PKCE durante a troca do código."""


class TokenExpiredError(JusBrAuthError):
    """O access token expirou e não pôde ser utilizado."""


class RefreshTokenRevokedError(JusBrAuthError):
    """O refresh token foi revogado ou a sessão SSO no CNJ foi encerrada."""


class SessionExpiredError(JusBrAuthError):
    """A sessão está expirada e requer novo login interativo."""


class JusBrApiError(JusBrError):
    """Exceção base para erros nas APIs REST do ecossistema Jus.br / PDPJ."""


class JusBrUnauthorizedError(JusBrApiError):
    """Acesso não autorizado às APIs da PDPJ (HTTP 401)."""
