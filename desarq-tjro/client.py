"""Cliente HTTP autenticado para a API REST do DESARQ/TJRO."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from auth import AuthService
from errors import DesarqApiError, DesarqUnauthorizedError
from models import SolicitacaoBuscaResponse, UsuarioMe

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = "https://desarquivamento-back.tjro.jus.br/back"


class DesarqClient:
    """Cliente HTTP com injeção transparente de Bearer token e auto-refresh em 401."""

    def __init__(
        self,
        auth_service: AuthService | None = None,
        http_client: httpx.Client | None = None,
        base_url: str = DEFAULT_API_BASE,
    ) -> None:
        self.auth = auth_service or AuthService()
        self.base_url = base_url.rstrip("/")
        self.http = http_client or httpx.Client(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Executa a requisição HTTP com token Bearer e uma tentativa de retry após 401."""
        tokens = self.auth.ensure_valid_tokens()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {tokens.access_token}"

        clean_path = path.lstrip("/")
        resp = self.http.request(method, clean_path, headers=headers, **kwargs)

        if resp.status_code == 401:
            logger.info("Recebido HTTP 401 da API DESARQ. Tentando renovação de token...")
            try:
                new_tokens = self.auth.refresh()
            except Exception as exc:
                raise DesarqUnauthorizedError(f"Acesso não autorizado (401) e falha ao renovar token: {exc}") from exc

            headers["Authorization"] = f"Bearer {new_tokens.access_token}"
            resp = self.http.request(method, clean_path, headers=headers, **kwargs)

            if resp.status_code == 401:
                raise DesarqUnauthorizedError(f"Acesso não autorizado ao DESARQ (HTTP 401): {resp.text}")

        if resp.status_code >= 400:
            raise DesarqApiError(f"Erro na API DESARQ ({resp.status_code}) em {path}: {resp.text}")

        return resp

    def get_me(self) -> UsuarioMe:
        """Consulta dados cadastrais e permissões do usuário logado (GET api/usuarios/me)."""
        resp = self._request("GET", "api/usuarios/me")
        return UsuarioMe.model_validate(resp.json())

    def buscar_solicitacoes(
        self,
        page: int = 0,
        size: int = 10,
        processo: str = "",
        modo: str = "",
        andamento: str = "",
        situacao: str = "",
        data: str = "",
    ) -> SolicitacaoBuscaResponse:
        """Busca solicitações de desarquivamento cadastradas."""
        params: dict[str, Any] = {"page": page, "size": size}
        if processo:
            params["processo"] = processo
        if modo:
            params["modo"] = modo
        if andamento:
            params["andamento"] = andamento
        if situacao:
            params["situacao"] = situacao
        if data:
            params["data"] = data

        resp = self._request("GET", "desarquivamento/busca", params=params)
        return SolicitacaoBuscaResponse.model_validate(resp.json())

    def existe_solicitacao(self, numero: str) -> bool:
        """Verifica se já existe solicitação em andamento para o processo."""
        clean_num = "".join(c for c in numero if c.isdigit())
        resp = self._request("GET", f"guia/existeSolicitacao/{clean_num}")
        return resp.json() is True

    def buscar_processo(self, numero: str) -> list[dict[str, Any]]:
        """Consulta processo(s) físico(s) no acervo do arquivo."""
        clean_num = "".join(c for c in numero if c.isdigit())
        resp = self._request("GET", f"processo/numero/{clean_num}")
        data = resp.json()
        if isinstance(data, list):
            return data
        return []
