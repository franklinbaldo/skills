"""Testes para o cliente HTTP autenticado do DESARQ/TJRO."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import DesarqClient
from errors import DesarqUnauthorizedError
from models import SolicitacaoBuscaResponse, TokenResponse


@pytest.fixture
def mock_auth_service():
    service = MagicMock()
    service.ensure_valid_tokens.return_value = TokenResponse(
        access_token="valid_test_access_token",
        refresh_token="valid_test_refresh_token",
        expires_in=300,
    )
    return service


def test_client_injects_bearer_token(mock_auth_service):
    captured_headers = {}

    def handle_request(req):
        captured_headers.update(dict(req.headers))
        return httpx.Response(
            200,
            json={
                "login": "12345678900",
                "nome": "Fulano de Tal",
                "cpfCNPJ": "12345678900",
                "email": "fulano@tjro.jus.br",
                "admin": False,
                "permissoes": [],
            },
        )

    mock_http = httpx.Client(
        base_url="https://desarquivamento-back.tjro.jus.br/back",
        transport=httpx.MockTransport(handle_request),
    )

    client = DesarqClient(auth_service=mock_auth_service, http_client=mock_http)
    me = client.get_me()

    assert captured_headers.get("authorization") == "Bearer valid_test_access_token"
    assert me.login == "12345678900"
    assert me.nome == "Fulano de Tal"


def test_client_handles_401_with_refresh_and_retry(mock_auth_service):
    attempts = 0

    def handle_request(req):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(401, json={"mensagem": "Token expired"})
        return httpx.Response(
            200,
            json={
                "login": "12345678900",
                "nome": "Fulano de Tal",
                "cpfCNPJ": "12345678900",
                "admin": False,
                "permissoes": [],
            },
        )

    mock_http = httpx.Client(
        base_url="https://desarquivamento-back.tjro.jus.br/back",
        transport=httpx.MockTransport(handle_request),
    )

    refreshed_tokens = TokenResponse(
        access_token="refreshed_access_token",
        refresh_token="refreshed_refresh_token",
        expires_in=300,
    )

    client = DesarqClient(auth_service=mock_auth_service, http_client=mock_http)

    with patch.object(mock_auth_service, "refresh", return_value=refreshed_tokens):
        # Na segunda tentativa, ensure_valid_tokens retorna os tokens renovados
        mock_auth_service.ensure_valid_tokens.side_effect = [
            TokenResponse(access_token="initial_token", expires_in=300),
            refreshed_tokens,
        ]
        me = client.get_me()

    assert attempts == 2
    assert me.nome == "Fulano de Tal"


def test_client_raises_unauthorized_if_401_persists(mock_auth_service):
    def handle_request(req):
        return httpx.Response(401, json={"mensagem": "Unauthorized"})

    mock_http = httpx.Client(
        base_url="https://desarquivamento-back.tjro.jus.br/back",
        transport=httpx.MockTransport(handle_request),
    )

    client = DesarqClient(auth_service=mock_auth_service, http_client=mock_http)

    with pytest.raises(DesarqUnauthorizedError, match="Acesso não autorizado"):
        client.get_me()


def test_client_buscar_solicitacoes(mock_auth_service):
    fake_response = {
        "content": [
            {
                "id": 101,
                "idProcesso": 202,
                "numeroProcesso": "00012345620248220001",
                "estado": "SOLICITADO",
            }
        ],
        "page": {
            "size": 10,
            "number": 0,
            "totalElements": 1,
            "totalPages": 1,
        },
    }

    mock_http = httpx.Client(
        base_url="https://desarquivamento-back.tjro.jus.br/back",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=fake_response)),
    )

    client = DesarqClient(auth_service=mock_auth_service, http_client=mock_http)
    busca = client.buscar_solicitacoes(page=0, size=10)

    assert isinstance(busca, SolicitacaoBuscaResponse)
    assert len(busca.content) == 1
    assert busca.content[0].id == 101
    assert busca.content[0].numeroProcesso == "00012345620248220001"
