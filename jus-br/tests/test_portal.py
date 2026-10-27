# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest",
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
"""Testes offline do cliente do Portal de Serviços: cabeçalhos, renovação, erros e envio ao S3."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from errors import JusBrApiError, JusBrUnauthorizedError
from models import TokenResponse
from portal import PORTAL_API, PortalClient, desembrulhar, sha1_hex


@pytest.fixture
def auth():
    service = MagicMock()
    service.ensure_valid_tokens.return_value = TokenResponse(access_token="jwt", token_type="Bearer", expires_in=300)
    service.refresh.return_value = TokenResponse(access_token="novo", token_type="Bearer", expires_in=300)
    return service


def cliente(auth, handler):
    return PortalClient(auth_service=auth, http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_get_sends_browser_headers_and_bearer(auth):
    def handler(req):
        assert str(req.url) == f"{PORTAL_API}/v1/usuario"
        assert req.headers["authorization"] == "Bearer jwt"
        assert "Mozilla" in req.headers["user-agent"]
        assert req.headers["sec-fetch-site"] == "same-origin"
        return httpx.Response(200, json={"dadosResposta": {"nome": "Fulano"}})

    assert cliente(auth, handler).get("/v1/usuario") == {"nome": "Fulano"}


def test_401_renews_once_and_repeats(auth):
    tentativas = []

    def handler(req):
        tentativas.append(req.headers["authorization"])
        return httpx.Response(401) if len(tentativas) == 1 else httpx.Response(200, json=[{"id": 1}])

    assert cliente(auth, handler).peticoes() == [{"id": 1}]
    assert tentativas == ["Bearer jwt", "Bearer novo"]


def test_second_401_raises_unauthorized(auth):
    with pytest.raises(JusBrUnauthorizedError):
        cliente(auth, lambda req: httpx.Response(401)).peticoes()


def test_web_server_403_is_named_as_such(auth):
    resp = httpx.Response(403, text="<html>403 Forbidden</html>")
    with pytest.raises(JusBrApiError, match="servidor web"):
        cliente(auth, lambda req: resp).get("v1/usuario")


def test_api_error_message_is_reported(auth):
    corpo = {"status": 400, "message": "Data está no formato inválido"}
    with pytest.raises(JusBrApiError, match="formato inválido"):
        cliente(auth, lambda req: httpx.Response(400, json=corpo)).domicilio("x", "y")


def test_unwraps_paged_content():
    assert desembrulhar({"content": [1], "pageable": {}}) == [1]
    assert desembrulhar({"dadosResposta": {"content": [2], "pageable": {}}}) == [2]
    assert desembrulhar([3]) == [3]


def test_processo_returns_first_item_and_rejects_empty(auth):
    def handler(req):
        if "6009021" in str(req.url):
            return httpx.Response(200, json=[{"numeroProcesso": "6009021-21.2026.4.06.3802"}])
        return httpx.Response(200, json=[])

    portal = cliente(auth, handler)
    assert portal.processo("6009021-21.2026.4.06.3802")["numeroProcesso"].startswith("6009021")
    with pytest.raises(JusBrApiError, match="não encontrado"):
        portal.processo("0000000-00.2026.8.22.0001")


def test_tribunal_absent_from_registry_is_none(auth):
    corpo = {"status": 404, "message": "Tribunal não localizado para o código JTR informado."}
    assert cliente(auth, lambda req: httpx.Response(404, json=corpo)).tribunal("406") is None


def test_comunicacoes_sends_digits_only_and_skips_empty_filters(auth):
    def handler(req):
        assert req.url.params["numeroProcesso"] == "60090212120264063802"
        assert "nomeParte" not in req.url.params
        return httpx.Response(200, json={"count": 0, "items": []})

    cliente(auth, handler).comunicacoes("6009021-21.2026.4.06.3802", "2026-08-01", "2026-10-26")


def test_anexar_uploads_to_presigned_url_without_pdpj_bearer(auth):
    vistos = []

    def handler(req):
        vistos.append(req)
        if req.url.host == "portaldeservicos.pdpj.jus.br":
            assert json.loads(req.content)["idPeticao"] == 7
            return httpx.Response(200, json={"url": "https://s3.example/obj?sig=1", "documentoSalvo": {"id": 9}})
        assert "authorization" not in req.headers
        assert req.content == b"%PDF-1.7"
        return httpx.Response(200)

    salvo = cliente(auth, handler).anexar({"idPeticao": 7}, b"%PDF-1.7")
    assert salvo == {"id": 9}
    assert [r.method for r in vistos] == ["POST", "PUT"]


def test_anexar_without_url_fails_loudly(auth):
    with pytest.raises(JusBrApiError, match="URL de envio"):
        cliente(auth, lambda req: httpx.Response(200, json={"documentoSalvo": {}})).anexar({}, b"x")


def test_sha1_matches_portal_hash_format():
    assert sha1_hex(b"abc") == "a9993e364706816aba3e25717850c26c9cd0d89d"
