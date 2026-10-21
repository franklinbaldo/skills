"""Testes para a interface CLI de jus-br."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli import app
from models import (
    ComunicacaoItem,
    ComunicacaoResponse,
    PeticionamentoResponse,
    ProcessoConsultaItem,
    TokenResponse,
    UsuarioJusBr,
)


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
    tokens = TokenResponse(access_token="at_new", refresh_token="rt_new", expires_in=300)
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


def test_cli_processo_consultar(mock_client_and_auth, capsys):
    mock_client_and_auth["client"].consultar_processo.return_value = ProcessoConsultaItem(
        numero="70012345620248220001",
        tribunal="TJRO",
        orgao_julgador="Vara de Fazenda",
        classe="Execução Fiscal",
    )

    app(["processo", "consultar", "70012345620248220001"], exit_on_error=False, result_action=None)
    captured = capsys.readouterr()
    assert "70012345620248220001" in captured.out
    assert "Vara de Fazenda" in captured.out


def test_cli_peticionamento_intercorrente(mock_client_and_auth, tmp_path, capsys):
    dummy_pdf = tmp_path / "peticao.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy")

    mock_client_and_auth["client"].peticionar_intercorrente.return_value = PeticionamentoResponse(
        protocolo="PROT-TEST-1234",
        data_recebimento="2026-10-21T12:00:00Z",
        numero_processo="70012345620248220001",
        status="RECEBIDO",
    )

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
    assert "PROT-TEST-1234" in captured.out
    assert "Recibo autêntico de protocolo recebido da PDPJ" in captured.out
    assert "SHA-256" in captured.out
