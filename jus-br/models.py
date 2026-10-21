# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
# ]
# ///
"""Modelos de dados e contratos Pydantic para o Jus.br e PDPJ/CNJ."""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    """Representação de tokens emitidos pelo Keycloak da PDPJ/CNJ."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    token_type: str
    expires_in: int = Field(gt=0)
    refresh_token: str | None = None
    refresh_expires_in: int | None = Field(default=None, gt=0)
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


class UsuarioJusBr(BaseModel):
    """Dados cadastrais e permissões do usuário logado na PDPJ/Jus.br."""

    model_config = ConfigDict(extra="ignore")

    sub: str | None = None
    name: str | None = None
    preferred_username: str | None = None
    cpf: str | None = None
    email: str | None = None
    roles: list[str] = Field(default_factory=list)

    def cpf_mascarado(self) -> str:
        """Retorna CPF formatado e mascarado para segurança."""
        doc = self.cpf or self.preferred_username or ""
        clean = "".join(c for c in doc if c.isdigit())
        if len(clean) == 11:
            return f"{clean[:3]}.***.***-{clean[-2:]}"
        return clean or "***"


class DestinatarioComunicacao(BaseModel):
    """Destinatário de uma comunicação processual."""

    model_config = ConfigDict(extra="ignore")

    nome: str | None = None
    polo: str | None = None
    comunicacao_id: int | None = None


class ComunicacaoItem(BaseModel):
    """Item de comunicação/intimação retornado pela ComunicaAPI do PJe/CNJ."""

    model_config = ConfigDict(extra="ignore")

    id: int
    data_disponibilizacao: str | None = None
    siglaTribunal: str | None = None
    tipoComunicacao: str | None = None
    nomeOrgao: str | None = None
    idOrgao: int | None = None
    texto: str | None = None
    numero_processo: str | None = None
    destinatarios: list[DestinatarioComunicacao] = Field(default_factory=list)


class ComunicacaoResponse(BaseModel):
    """Resposta paginada da ComunicaAPI do PJe."""

    model_config = ConfigDict(extra="ignore")

    status: Literal["success"]
    message: str | None = None
    count: int = Field(ge=0)
    items: list[ComunicacaoItem]


class ProcessoConsultaItem(BaseModel):
    """Dados consolidados de processo judicial retornado na consulta."""

    model_config = ConfigDict(extra="ignore")

    numero: str
    tribunal: str | None = None
    orgao_julgador: str | None = None
    classe: str | None = None
    assuntos: list[str] = Field(default_factory=list)
    data_ajuizamento: str | None = None
    partes: list[dict[str, Any]] = Field(default_factory=list)
    movimentacoes: list[dict[str, Any]] = Field(default_factory=list)


class PeticionamentoRequest(BaseModel):
    """Estrutura para protocolo de petição inicial ou intercorrente."""

    model_config = ConfigDict(extra="ignore")

    numero_processo: str
    tipo_peticao: str
    sigla_tribunal: str
    descricao: str | None = None
    arquivo_base64: str
    nome_arquivo: str
    hash_sha256: str | None = None
    documentos_anexos: list[dict[str, Any]] = Field(default_factory=list)


class PeticionamentoResponse(BaseModel):
    """Recibo autêntico de protocolo retornado pelo barramento de peticionamento da PDPJ."""

    model_config = ConfigDict(extra="ignore")

    protocolo: str
    data_recebimento: str
    numero_processo: str
    status: str
    hash_sha256: str | None = None
    mensagem: str | None = None
