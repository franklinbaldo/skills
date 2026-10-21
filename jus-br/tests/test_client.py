"""Testes para o cliente HTTP de Jus.br e PDPJ."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import JusBrClient
from models import PeticionamentoRequest, TokenResponse


@pytest.fixture
def mock_auth_service():
    service = MagicMock()
    service.ensure_valid_tokens.return_value = TokenResponse(
        access_token="valid_pdpj_token",
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
        refresh_token="refreshed_rt",
        expires_in=300,
    )

    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)
    with patch.object(mock_auth_service, "refresh", return_value=refreshed_tokens):
        mock_auth_service.ensure_valid_tokens.side_effect = [
            TokenResponse(access_token="initial", expires_in=300),
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


def test_client_peticionar_intercorrente(mock_auth_service):
    mock_http = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json={
                    "protocolo": "PROT-20261021-999",
                    "data_recebimento": "2026-10-21T10:00:00Z",
                    "numero_processo": "70012345620248220001",
                    "status": "RECEBIDO",
                },
            )
        )
    )
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)

    req = PeticionamentoRequest(
        numero_processo="70012345620248220001",
        tipo_peticao="Manifestação",
        sigla_tribunal="TJRO",
        arquivo_base64="ZHVtbXk=",
        nome_arquivo="manifestacao.pdf",
        hash_sha256="abc123sha256",
    )
    resp = client.peticionar_intercorrente(req)
    assert resp.protocolo == "PROT-20261021-999"
    assert resp.status == "RECEBIDO"


def test_client_consultar_processo_sucesso(mock_auth_service):
    mock_http = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json={
                    "numero": "70012345620248220001",
                    "classe": "Ação Civil Pública",
                    "tribunal": "TJRO",
                    "orgao_julgador": "2ª Vara Cível",
                },
            )
        )
    )
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)
    proc = client.consultar_processo("70012345620248220001")
    assert proc.numero == "70012345620248220001"
    assert proc.classe == "Ação Civil Pública"


def test_client_consultar_processo_falha_nao_simula_dados(mock_auth_service):
    from errors import JusBrApiError

    mock_http = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(404, text="Processo não localizado no barramento"))
    )
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)

    with pytest.raises(JusBrApiError, match="Erro na API da PDPJ"):
        client.consultar_processo("70012345620248220001")


def test_client_peticionar_intercorrente_falha_nao_fabrica_recibo(mock_auth_service):
    from errors import JusBrApiError

    mock_http = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(500, text="Falha de conexão com o tribunal destino"))
    )
    client = JusBrClient(auth_service=mock_auth_service, http_client=mock_http)

    req = PeticionamentoRequest(
        numero_processo="70012345620248220001",
        tipo_peticao="Manifestação",
        sigla_tribunal="TJRO",
        arquivo_base64="ZHVtbXk=",
        nome_arquivo="manifestacao.pdf",
    )
    # Garante categoricamente que JAMAIS fabrica PROT-<timestamp> em caso de erro!
    with pytest.raises(JusBrApiError, match="Erro na API da PDPJ"):
        client.peticionar_intercorrente(req)
