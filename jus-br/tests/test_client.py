# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest",
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
"""Testes para o cliente HTTP de Jus.br e PDPJ."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import JusBrClient
from errors import ExperimentalServiceUnavailableError
from models import PeticionamentoRequest, TokenResponse


@pytest.fixture
def mock_auth_service():
    service = MagicMock()
    service.ensure_valid_tokens.return_value = TokenResponse(
        access_token="valid_pdpj_token",
        token_type="Bearer",
        refresh_token="valid_pdpj_refresh",
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
                "sub": "user_123",
                "name": "Nome Usuario",
                "preferred_username": "12345678900",
                "cpf": "12345678900",
                "roles": ["advogado"],
            },
        )

    mock_http = httpx.Client(transport=httpx.MockTransport(handle_request))
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)
    perfil = client.obter_perfil()

    assert captured_headers.get("authorization") == "Bearer valid_pdpj_token"
    assert perfil.name == "Nome Usuario"


def test_client_handles_401_with_refresh_and_retry(mock_auth_service):
    attempts = 0

    def handle_request(req):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(401, json={"error": "token_expired"})
        return httpx.Response(200, json={"numero": "00012345620248220001"})

    mock_http = httpx.Client(transport=httpx.MockTransport(handle_request))
    refreshed_tokens = TokenResponse(
        access_token="refreshed_at",
        token_type="Bearer",
        refresh_token="refreshed_rt",
        expires_in=300,
    )

    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)
    with patch.object(mock_auth_service, "refresh", return_value=refreshed_tokens):
        mock_auth_service.ensure_valid_tokens.side_effect = [
            TokenResponse(access_token="initial", token_type="Bearer", expires_in=300),
            refreshed_tokens,
        ]
        resp = client._authenticated_request("GET", "https://api.pdpj.jus.br/processos/1")

    assert attempts == 2
    assert resp.status_code == 200


def test_client_buscar_comunicacoes(mock_auth_service):
    fake_response = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": 101,
                "data_disponibilizacao": "2026-10-21",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "1ª Vara de Fazenda",
                "numero_processo": "70012345620248220001",
            }
        ],
    }
    mock_http = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=fake_response)))
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)

    res = client.buscar_comunicacoes(numero_processo="70012345620248220001", sigla_tribunal="TJRO")
    assert res.count == 1
    assert len(res.items) == 1
    assert res.items[0].siglaTribunal == "TJRO"


@pytest.mark.parametrize("payload", [{}, {"status": "success"}, {"status": "error", "count": 0, "items": []}])
def test_client_rejects_incomplete_or_unsuccessful_communication_contract(mock_auth_service, payload):
    mock_http = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload)))
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)
    with pytest.raises(ValidationError):
        client.buscar_comunicacoes()


def test_unconfirmed_petition_endpoint_is_disabled_without_auth_or_network(mock_auth_service):
    sent = []
    mock_http = httpx.Client(transport=httpx.MockTransport(lambda req: sent.append(req)))
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)

    req = PeticionamentoRequest(
        numero_processo="70012345620248220001",
        tipo_peticao="Manifestação",
        sigla_tribunal="TJRO",
        arquivo_base64="ZHVtbXk=",
        nome_arquivo="manifestacao.pdf",
        hash_sha256="abc123sha256",
    )
    with pytest.raises(ExperimentalServiceUnavailableError, match="nenhum protocolo foi transmitido"):
        client.peticionar_intercorrente(req)
    assert sent == []
    mock_auth_service.ensure_valid_tokens.assert_not_called()


def test_unconfirmed_process_endpoint_is_disabled_without_auth_or_network(mock_auth_service):
    sent = []
    mock_http = httpx.Client(transport=httpx.MockTransport(lambda req: sent.append(req)))
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)
    with pytest.raises(ExperimentalServiceUnavailableError, match="não foi confirmado"):
        client.consultar_processo("70012345620248220001")
    assert sent == []
    mock_auth_service.ensure_valid_tokens.assert_not_called()


def test_client_consultar_processo_is_disabled_without_network(mock_auth_service):
    sent = []
    mock_http = httpx.Client(transport=httpx.MockTransport(lambda req: sent.append(req)))
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)

    with pytest.raises(ExperimentalServiceUnavailableError):
        client.consultar_processo("70012345620248220001")
    assert sent == []


def test_authenticated_request_timeout_propagates_without_success(mock_auth_service):
    mock_http = httpx.Client(
        transport=httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("slow response")))
    )
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)
    with pytest.raises(httpx.ReadTimeout):
        client._authenticated_request("GET", "https://example.invalid")


@pytest.mark.parametrize("status", [403, 404, 429, 500, 503])
def test_authenticated_request_http_failures_raise(status, mock_auth_service):
    from errors import JusBrApiError

    mock_http = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(status, text="service error")))
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)
    with pytest.raises(JusBrApiError, match=f"{status}"):
        client._authenticated_request("GET", "https://example.invalid")
