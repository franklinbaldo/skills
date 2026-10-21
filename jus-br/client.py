"""Cliente HTTP autenticado para as APIs do ecossistema Jus.br e PDPJ/CNJ."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from auth import AuthService, get_userinfo
from errors import JusBrApiError, JusBrUnauthorizedError
from models import (
    ComunicacaoResponse,
    PeticionamentoRequest,
    PeticionamentoResponse,
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
        """Consulta metadados e linha processual de um processo na PDPJ.

        Propaga JusBrApiError ou JusBrUnauthorizedError caso o serviço retorne erro.
        Nenhum dado é forjado ou simulado em caso de falha.
        """
        clean_num = "".join(c for c in numero if c.isdigit())
        if not clean_num:
            raise JusBrApiError(f"Número de processo inválido: {numero}")
        url = f"https://api.pdpj.jus.br/processos/{clean_num}"
        resp = self._authenticated_request("GET", url)
        return ProcessoConsultaItem.model_validate(resp.json())

    def peticionar_intercorrente(self, request: PeticionamentoRequest) -> PeticionamentoResponse:
        """Submete uma petição intercorrente ao barramento da PDPJ.

        Somente retorna sucesso quando um recibo autêntico for emitido e validado pelo barramento da PDPJ.
        Em caso de erro de rede, recusa de protocolo ou rejeição, propaga exceção explicita.
        """
        url = "https://api.pdpj.jus.br/peticionamento/intercorrente"
        resp = self._authenticated_request("POST", url, json=request.model_dump())
        return PeticionamentoResponse.model_validate(resp.json())
