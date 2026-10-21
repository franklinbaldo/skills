"""Modelos de dados e contratos Pydantic para o DESARQ/TJRO."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    """Representação de tokens emitidos pelo Keycloak do TJRO."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(default=300)
    refresh_token: str | None = None
    refresh_expires_in: int | None = None
    scope: str | None = None
    id_token: str | None = None
    created_at: float = Field(default_factory=time.time)

    def is_access_token_expired(self, leeway: int = 30) -> bool:
        """Indica se o access token expirou ou expira dentro do intervalo de tolerância."""
        now = time.time()
        return (now + leeway) >= (self.created_at + self.expires_in)

    def is_refresh_token_expired(self, leeway: int = 30) -> bool:
        """Indica se o refresh token expirou ou expira dentro do intervalo de tolerância."""
        if not self.refresh_token:
            return True
        if self.refresh_expires_in is None:
            # Se Keycloak não informou refresh_expires_in, assume vida útil típica (ex.: 1800s / 30m)
            return False
        now = time.time()
        return (now + leeway) >= (self.created_at + self.refresh_expires_in)

    def __repr__(self) -> str:
        at_preview = f"{self.access_token[:4]}...{self.access_token[-4:]}" if len(self.access_token) > 8 else "***"
        rt_preview = (
            f"{self.refresh_token[:4]}...{self.refresh_token[-4:]}"
            if self.refresh_token and len(self.refresh_token) > 8
            else "***"
        )
        return (
            f"TokenResponse(access_token='{at_preview}', token_type='{self.token_type}', "
            f"expires_in={self.expires_in}, refresh_token='{rt_preview}', "
            f"created_at={self.created_at})"
        )

    def __str__(self) -> str:
        return self.__repr__()


class UsuarioMe(BaseModel):
    """Dados cadastrais e permissões do usuário logado no DESARQ."""

    model_config = ConfigDict(extra="ignore")

    login: str
    nome: str
    cpfCNPJ: str
    email: str | None = None
    loginComNome: str | None = None
    origemAutenticacao: str | None = None
    pessoaJuridica: bool = False
    admin: bool = False
    permissoes: list[str] = Field(default_factory=list)

    def cpf_mascarado(self) -> str:
        """Retorna o CPF mascarado para exibição segura."""
        clean = "".join(c for c in self.cpfCNPJ if c.isdigit())
        if len(clean) == 11:
            return f"{clean[:3]}.***.***-{clean[-2:]}"
        elif len(clean) == 14:
            return f"{clean[:2]}.***.***/****-{clean[-2:]}"
        return "***"


class SolicitacaoBuscaItem(BaseModel):
    """Item retornado na busca de solicitações do DESARQ."""

    model_config = ConfigDict(extra="ignore")

    id: int
    idProcesso: int
    numeroProcesso: str
    estado: str | None = None
    tipoDesarquivamento: str | None = None
    tipoEmissao: str | None = None
    numeroGuia: str | None = None
    dataCriacao: str | None = None
    dataUltimoEstado: str | None = None
    caixa: str | None = None
    obsProcesso: str | None = None
    observacao: str | None = None
    eventos: list[dict[str, Any]] = Field(default_factory=list)


class SolicitacaoBuscaResponse(BaseModel):
    """Resposta paginada da busca de solicitações."""

    model_config = ConfigDict(extra="ignore")

    content: list[SolicitacaoBuscaItem] = Field(default_factory=list)
    page: dict[str, Any] = Field(default_factory=dict)
