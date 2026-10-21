"""Testes para a interface de linha de comando (CLI) do DESARQ/TJRO."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli import app
from models import SolicitacaoBuscaItem, SolicitacaoBuscaResponse, TokenResponse, UsuarioMe


@pytest.fixture
def mock_client_and_auth():
    with (
        patch("cli.AuthService") as mock_auth_cls,
        patch("cli.DesarqClient") as mock_client_cls,
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

    # Executa: desarq auth status
    app(["auth", "status"], exit_on_error=False, result_action=None)

    captured = capsys.readouterr()
    assert "Não autenticado" in captured.out


def test_cli_auth_status_authenticated(mock_client_and_auth, capsys):
    tokens = TokenResponse(
        access_token="valid_at_12345",
        refresh_token="valid_rt_67890",
        expires_in=300,
        refresh_expires_in=1800,
    )
    mock_client_and_auth["store"].load_tokens.return_value = tokens
    mock_client_and_auth["auth"].ensure_valid_tokens.return_value = tokens
    mock_client_and_auth["client"].get_me.return_value = UsuarioMe(
        login="11122233344",
        nome="Procurador Teste",
        cpfCNPJ="11122233344",
        email="teste@pge.ro.gov.br",
        admin=False,
    )

    app(["auth", "status"], exit_on_error=False, result_action=None)

    captured = capsys.readouterr()
    assert "Sessão Ativa" in captured.out
    assert "Procurador Teste" in captured.out
    # Garante que nenhum token foi impresso no terminal
    assert "valid_at_12345" not in captured.out
    assert "valid_rt_67890" not in captured.out


def test_cli_auth_login_already_valid(mock_client_and_auth, capsys):
    tokens = TokenResponse(
        access_token="valid_at",
        refresh_token="valid_rt",
        expires_in=300,
    )
    mock_client_and_auth["auth"].ensure_valid_tokens.return_value = tokens
    mock_client_and_auth["client"].get_me.return_value = UsuarioMe(
        login="11122233344",
        nome="Procurador Teste",
        cpfCNPJ="11122233344",
    )

    app(["auth", "login"], exit_on_error=False, result_action=None)

    captured = capsys.readouterr()
    assert "Sessão ativa e válida" in captured.out
    mock_client_and_auth["auth"].login.assert_not_called()


def test_cli_auth_login_force(mock_client_and_auth, capsys):
    new_tokens = TokenResponse(
        access_token="new_at",
        refresh_token="new_rt",
        expires_in=300,
    )
    mock_client_and_auth["auth"].login.return_value = new_tokens
    mock_client_and_auth["client"].get_me.return_value = UsuarioMe(
        login="11122233344",
        nome="Procurador Teste",
        cpfCNPJ="11122233344",
    )

    app(["auth", "login", "--force"], exit_on_error=False, result_action=None)

    captured = capsys.readouterr()
    assert "Autenticação concluída com sucesso" in captured.out
    mock_client_and_auth["auth"].login.assert_called_once()


def test_cli_auth_refresh(mock_client_and_auth, capsys):
    new_tokens = TokenResponse(
        access_token="refreshed_at",
        refresh_token="refreshed_rt",
        expires_in=300,
    )
    mock_client_and_auth["auth"].refresh.return_value = new_tokens

    app(["auth", "refresh"], exit_on_error=False, result_action=None)

    captured = capsys.readouterr()
    assert "Sessão renovada com sucesso" in captured.out
    mock_client_and_auth["auth"].refresh.assert_called_once()


def test_cli_auth_logout(mock_client_and_auth, capsys):
    app(["auth", "logout"], exit_on_error=False, result_action=None)

    captured = capsys.readouterr()
    assert "Sessão encerrada com sucesso" in captured.out
    mock_client_and_auth["auth"].logout.assert_called_once()


def test_cli_usuario_obter(mock_client_and_auth, capsys):
    mock_client_and_auth["client"].get_me.return_value = UsuarioMe(
        login="11122233344",
        nome="Fulano de Tal",
        cpfCNPJ="11122233344",
        email="fulano@pge.ro.gov.br",
        origemAutenticacao="GOV_BR",
        admin=False,
        permissoes=["DESARQUIVAMENTO_SOLICITAR"],
    )

    app(["usuario", "obter"], exit_on_error=False, result_action=None)

    captured = capsys.readouterr()
    assert "Fulano de Tal" in captured.out
    assert "111.***.***-44" in captured.out  # Mascarado


def test_cli_solicitacoes_listar(mock_client_and_auth, capsys):
    mock_client_and_auth["client"].buscar_solicitacoes.return_value = SolicitacaoBuscaResponse(
        content=[
            SolicitacaoBuscaItem(
                id=5001,
                idProcesso=1002,
                numeroProcesso="70012345620248220001",
                estado="SOLICITADO",
                tipoDesarquivamento="Digitalizado",
                dataCriacao="2026-10-21T10:00:00",
                caixa="CX-12",
            )
        ],
        page={"size": 10, "number": 0, "totalElements": 1, "totalPages": 1},
    )

    app(["solicitacoes", "listar"], exit_on_error=False, result_action=None)

    captured = capsys.readouterr()
    assert "70012345620248220001" in captured.out
    assert "SOLICITADO" in captured.out
    assert "5001" in captured.out
