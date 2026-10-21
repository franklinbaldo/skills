# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
"""Cliente HTTP autenticado para as APIs do ecossistema Jus.br e PDPJ/CNJ."""

from __future__ import annotations

import logging
from typing import Any, NoReturn

import httpx
from auth import AuthService, get_userinfo
from errors import ExperimentalServiceUnavailableError, JusBrApiError, JusBrUnauthorizedError
from models import (
    ComunicacaoResponse,
    PeticionamentoRequest,
    ProcessoConsultaItem,
    UsuarioJusBr,
)

logger = logging.getLogger(__name__)

COMUNICA_API_BASE = "https://comunicaapi.pje.jus.br/api/v1"


class JusBrClient:
    """Cliente HTTP com auto-refresh para as APIs do ecossistema Jus.br / PDPJ."""

    def __init__(
        self,
        auth_service: AuthService | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.auth = auth_service or AuthService()
        self.http = http_client or httpx.Client(timeout=30.0)

    def _authenticated_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Executa chamada HTTP com Bearer token e uma tentativa de refresh após 401."""
        tokens = self.auth.ensure_valid_tokens()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {tokens.access_token}"

        resp = self.http.request(method, url, headers=headers, **kwargs)

        if resp.status_code == 401:
            logger.info("Recebido HTTP 401 da API da PDPJ. Tentando renovação com refresh_token...")
            try:
                new_tokens = self.auth.refresh()
            except Exception as exc:
                raise JusBrUnauthorizedError(f"Acesso não autorizado (401) e falha ao renovar: {exc}") from exc

            headers["Authorization"] = f"Bearer {new_tokens.access_token}"
            resp = self.http.request(method, url, headers=headers, **kwargs)

            if resp.status_code == 401:
                raise JusBrUnauthorizedError(f"Acesso não autorizado na PDPJ (HTTP 401): {resp.text}")

        if resp.status_code >= 400:
            raise JusBrApiError(f"Erro na API da PDPJ ({resp.status_code}) em {url}: {resp.text}")

        return resp

    def obter_perfil(self) -> UsuarioJusBr:
        """Consulta dados cadastrais do usuário via UserInfo da PDPJ."""
        tokens = self.auth.ensure_valid_tokens()
        return get_userinfo(tokens.access_token, http_client=self.http)

    def buscar_comunicacoes(
        self,
        numero_processo: str = "",
        sigla_tribunal: str = "",
        data_disponibilizacao: str = "",
        pagina: int = 1,
        itens_por_pagina: int = 10,
    ) -> ComunicacaoResponse:
        """Busca publicações, intimações e editais oficiais em tempo real na ComunicaAPI do PJe."""
        params: dict[str, Any] = {
            "pagina": pagina,
            "itensPorPagina": itens_por_pagina,
        }
        if numero_processo:
            clean_num = "".join(c for c in numero_processo if c.isdigit())
            params["numeroProcesso"] = clean_num
        if sigla_tribunal:
            params["siglaTribunal"] = sigla_tribunal.upper()
        if data_disponibilizacao:
            params["dataDisponibilizacao"] = data_disponibilizacao

        url = f"{COMUNICA_API_BASE}/comunicacao"
        # ComunicaAPI aceita consulta pública ou autenticada
        try:
            tokens = self.auth.store.load_tokens()
            headers = {"Authorization": f"Bearer {tokens.access_token}"} if tokens else {}
        except Exception:
            headers = {}

        resp = self.http.get(url, params=params, headers=headers)
        if resp.status_code >= 400:
            raise JusBrApiError(f"Erro na ComunicaAPI ({resp.status_code}): {resp.text}")

        return ComunicacaoResponse.model_validate(resp.json())

    def consultar_processo(self, numero: str) -> ProcessoConsultaItem:
        """Consulta experimental desabilitada até confirmação do contrato oficial.

        O endpoint anteriormente presumido não consta da documentação oficial verificada.
        Não envie credenciais nem dados processuais para um contrato não confirmado.
        """
        raise ExperimentalServiceUnavailableError(
            "Consulta processual direta indisponível: o endpoint implementado anteriormente não foi confirmado "
            "por contrato oficial. Use a consulta do Portal Jus.br ou uma API autorizada do CNJ."
        )

    def peticionar_intercorrente(self, request: PeticionamentoRequest) -> NoReturn:
        """Peticionamento experimental desabilitado até contrato e ambiente serem confirmados.

        A documentação do CNJ descreve o Portal de Serviços, Swagger de homologação e
        callbacks assíncronos; ela não confirma o endpoint anteriormente presumido.
        Esta operação não transmite a petição.
        """
        raise ExperimentalServiceUnavailableError(
            "Peticionamento por API indisponível: o endpoint anteriormente implementado não foi confirmado "
            "por contrato oficial, e nenhum protocolo foi transmitido ou gerado. Use o Portal de Serviços oficial."
        )
