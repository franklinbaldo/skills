# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest",
#     "cyclopts>=3.0",
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
#     "rich>=13.0.0",
# ]
# ///
"""Testes para a interface CLI de jus-br."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli import app
from models import ComunicacaoItem, ComunicacaoResponse, TokenResponse, UsuarioJusBr


@pytest.fixture
def mock_client_and_auth():
    with (
        patch("cli.AuthService") as mock_auth_cls,
        patch("cli.JusBrClient") as mock_client_cls,
        patch("cli.CredentialStore") as mock_store_cls,
    ):
        mock_auth = MagicMock()
        mock_client = MagicMock()
        mock_store = MagicMock()

        mock_auth_cls.return_value = mock_auth
        mock_client_cls.return_value = mock_client
        mock_store_cls.return_value = mock_store

        yield {
            "auth": mock_auth,
            "client": mock_client,
            "store": mock_store,
        }


def test_cli_auth_status_not_authenticated(mock_client_and_auth, capsys):
    mock_client_and_auth["store"].load_tokens.return_value = None
    app(["auth", "status"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "Não autenticado" in captured.out


def test_cli_auth_status_authenticated(mock_client_and_auth, capsys):
    tokens = TokenResponse(
        access_token="valid_at_123",
        token_type="Bearer",
        refresh_token="valid_rt_456",
        expires_in=300,
        refresh_expires_in=1800,
    )
    mock_client_and_auth["store"].load_tokens.return_value = tokens
    mock_client_and_auth["auth"].ensure_valid_tokens.return_value = tokens
    mock_client_and_auth["client"].obter_perfil.return_value = UsuarioJusBr(
        name="Advogado Teste",
        cpf="11122233344",
        preferred_username="11122233344",
        email="advogado@exemplo.com",
    )

    app(["auth", "status"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "Sessão Ativa" in captured.out
    assert "Advogado Teste" in captured.out
    assert "valid_at_123" not in captured.out


def test_cli_auth_refresh(mock_client_and_auth, capsys):
    tokens = TokenResponse(access_token="at_new", token_type="Bearer", refresh_token="rt_new", expires_in=300)
    mock_client_and_auth["auth"].refresh.return_value = tokens

    app(["auth", "refresh"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "Sessão da PDPJ renovada com sucesso" in captured.out


def test_cli_auth_logout(mock_client_and_auth, capsys):
    app(["auth", "logout"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "Sessão encerrada com sucesso" in captured.out
    mock_client_and_auth["auth"].logout.assert_called_once()


def test_cli_usuario_obter(mock_client_and_auth, capsys):
    mock_client_and_auth["client"].obter_perfil.return_value = UsuarioJusBr(
        name="Procurador JusBr",
        preferred_username="76450694220",
        cpf="76450694220",
        email="procurador@jus.br",
        roles=["advogado", "procurador"],
    )

    app(["usuario", "obter"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "Procurador JusBr" in captured.out
    assert "764.***.***-20" in captured.out


def test_cli_comunicacoes_buscar(mock_client_and_auth, capsys):
    mock_client_and_auth["client"].buscar_comunicacoes.return_value = ComunicacaoResponse(
        status="success",
        count=1,
        items=[
            ComunicacaoItem(
                id=999,
                data_disponibilizacao="2026-10-21",
                siglaTribunal="TJRO",
                tipoComunicacao="Intimação",
                numero_processo="70012345620248220001",
                nomeOrgao="1ª Vara",
            )
        ],
    )

    app(["comunicacoes", "buscar", "--processo", "70012345620248220001"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "70012345620248220001" in captured.out
    assert "TJRO" in captured.out


def test_cli_processo_consultar_never_presents_unconfirmed_endpoint_as_supported(mock_client_and_auth, capsys):
    from errors import ExperimentalServiceUnavailableError

    mock_client_and_auth["client"].consultar_processo.side_effect = ExperimentalServiceUnavailableError(
        "endpoint não confirmado"
    )
    with pytest.raises(SystemExit):
        app(["processo", "consultar", "70012345620248220001"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "endpoint não confirmado" in captured.out
    assert "Vara de Fazenda" not in captured.out


def test_cli_peticionamento_is_disabled_without_reading_or_sending_file(mock_client_and_auth, tmp_path, capsys):
    dummy_pdf = tmp_path / "peticao.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy")
    with patch("pathlib.Path.read_bytes", side_effect=AssertionError("file must not be read")):
        with pytest.raises(SystemExit) as exc:
            app(
                [
                    "peticionamento",
                    "intercorrente",
                    "--processo",
                    "70012345620248220001",
                    "--tribunal",
                    "TJRO",
                    "--arquivo",
                    str(dummy_pdf),
                ],
                exit_on_error=False,
                result_action=None,
            )
    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "nenhum arquivo foi lido ou transmitido" in captured.out
    assert "nenhum protocolo foi gerado" in captured.out
    mock_client_and_auth["client"].peticionar_intercorrente.assert_not_called()


def test_cli_auth_set_token(mock_client_and_auth, capsys):
    tokens = TokenResponse(access_token="sample_jwt_123", token_type="Bearer", expires_in=3600)
    mock_client_and_auth["auth"].import_session.return_value = tokens
    mock_client_and_auth["client"].obter_perfil.return_value = UsuarioJusBr(
        name="Usuario Importado",
        cpf="12345678900",
    )

    app(["auth", "set-token", "--token", "sample_jwt_123"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "Sessão importada e salva com sucesso" in captured.out
    assert "Usuario Importado" in captured.out
    mock_client_and_auth["auth"].import_session.assert_called_once_with("sample_jwt_123")


def test_cli_auth_bookmarklet(mock_client_and_auth, capsys):
    with patch("webbrowser.open") as mock_open:
        app(["auth", "bookmarklet"], exit_on_error=False, result_action=None)
        captured = capsys.readouterr()
        assert "Conector Bookmarklet Jus.br" in captured.out
        mock_open.assert_called_once()
