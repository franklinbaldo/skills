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
"""Testes offline da montagem da petição e dos comandos `processo` e `peticao` (dados fictícios)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli import app
from peticao_montagem import MontagemError, conferir_arquivo, conferir_tribunal, escolher_tipo, montar_rascunho

PROCESSO = {
    "numeroProcesso": "1000001-00.2026.4.01.4100",
    "siglaTribunal": "TRF1",
    "tramitacaoAtual": {
        "tribunal": {"sigla": "TRF1", "segmento": "JUSTICA_FEDERAL", "jtr": "401"},
        "grau": {"sigla": "G1", "numero": 1},
        "valorAcao": 1000.0,
        "classe": [{"codigo": 7, "descricao": "Procedimento Comum Cível"}],
        "assunto": [{"codigo": 5922, "descricao": "Retido na fonte"}],
        "distribuicao": [{"dataHora": "2026-08-14T16:33:14", "orgaoJulgador": [{"id": 123, "nome": "1ª Vara"}]}],
        "partes": [
            {
                "polo": "ATIVO",
                "nome": "PARTE AUTORA",
                "documentosPrincipais": [{"numero": "00000000000", "tipo": "CPF"}],
                "representantes": [{"tipoRepresentacao": "ADVOGADO", "nome": "ADVOGADA FICTICIA"}],
            },
            {"polo": "PASSIVO", "nome": "AUTARQUIA RE", "documentosPrincipais": [{"numero": "1", "tipo": "CNPJ"}]},
        ],
        "movimentos": [{"dataHora": "2026-09-01T10:00:00", "descricao": "Citação"}],
    },
    "documentos": [
        {
            "sequencia": 1,
            "nome": "inicial.pdf",
            "tipo": {"nome": "PETIÇÃO"},
            "hrefBinario": "/processos/1000001-00.2026.4.01.4100/documentos/abc-uuid/binario",
        }
    ],
}
CADASTRO = {
    "codigoJTR": "401",
    "ativo": True,
    "funcionalidadesHabilitadas": ["PETICAO_INTERCORRENTE"],
    "tiposArquivosAceitos": [{"extensao": "pdf", "tamanhoMaximoMB": 1}],
}
TIPOS = [
    {"id": 533, "descricao": "Contestação"},
    {"id": 591, "descricao": "Contestação (Outros)"},
    {"id": 9, "descricao": "Anexo"},
]


def test_rascunho_takes_every_field_from_the_records():
    dto = montar_rascunho(PROCESSO, 533)
    assert dto["tipo"] == "A" and dto["idTipoDocumento"] == 533
    assert dto["codOrgaoJulgadorCorporativo"] == 123
    assert dto["distribuidoEm"] == "2026-08-14 16:33:14"
    assert dto["siglaSegmentoJustica"] == "JCF" and dto["jtrTribunal"] == "401"
    assert dto["numeroGrau"] == "1" and dto["siglaGrau"] == "G1"
    assert [p["modalidadePolo"] for p in dto["peticaoPartes"]] == ["AT", "PA"]
    assert dto["peticaoPartes"][0]["advogados"][0]["pessoa"]["nome"] == "ADVOGADA FICTICIA"
    assert dto["peticaoAssuntos"] == [{"codigo": 5922, "nome": "Retido na fonte"}]


def test_rascunho_refuses_records_without_court_or_distribution():
    incompleto = {**PROCESSO, "tramitacaoAtual": {**PROCESSO["tramitacaoAtual"], "distribuicao": []}}
    with pytest.raises(MontagemError, match="órgão julgador"):
        montar_rascunho(incompleto, 533)


def test_court_outside_registry_stops_before_any_write():
    with pytest.raises(MontagemError, match="peticione no sistema do tribunal"):
        conferir_tribunal(None, "TRF6")
    with pytest.raises(MontagemError, match="não habilita"):
        conferir_tribunal({**CADASTRO, "funcionalidadesHabilitadas": ["OFICIOS"]}, "TRF2")


def test_file_extension_and_size_follow_the_court(tmp_path):
    pdf = tmp_path / "peca.pdf"
    pdf.write_bytes(b"%PDF" + b"0" * 10)
    assert conferir_arquivo(CADASTRO, pdf).startswith(b"%PDF")
    grande = tmp_path / "grande.pdf"
    grande.write_bytes(b"0" * (1024 * 1024 + 1))
    with pytest.raises(MontagemError, match="limite"):
        conferir_arquivo(CADASTRO, grande)
    docx = tmp_path / "peca.docx"
    docx.write_bytes(b"x")
    with pytest.raises(MontagemError, match="não aceita"):
        conferir_arquivo(CADASTRO, docx)


def test_document_type_is_never_guessed():
    assert escolher_tipo(TIPOS, "Contestação")["id"] == 533
    assert escolher_tipo(TIPOS, "591")["id"] == 591
    with pytest.raises(MontagemError, match="não identifica um só tipo"):
        escolher_tipo(TIPOS, "Contest")
    with pytest.raises(MontagemError):
        escolher_tipo(TIPOS, "")


@pytest.fixture
def portal():
    with patch("cli_comum.PortalClient") as cls:
        mock = MagicMock()
        mock.processo.return_value = PROCESSO
        mock.tribunal.return_value = CADASTRO
        mock.tipos_documento.return_value = TIPOS
        cls.return_value = mock
        yield mock


def _rodar(args):
    app(args, exit_on_error=False, result_action=None)


def test_processo_consultar_shows_document_id_for_download(portal, capsys):
    _rodar(["processo", "consultar", PROCESSO["numeroProcesso"]])
    saida = capsys.readouterr().out
    assert "abc-uuid" in saida and "1ª Vara" in saida and "Citação" in saida


def test_rascunho_without_confirm_only_shows_plan(portal, tmp_path, capsys):
    pdf = tmp_path / "contestacao.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    _rodar(["peticao", "rascunho", PROCESSO["numeroProcesso"], str(pdf), "--tipo", "Contestação"])
    assert "Nada foi criado" in capsys.readouterr().out
    portal.criar_rascunho.assert_not_called()
    portal.anexar.assert_not_called()


def test_rascunho_with_confirm_creates_and_attaches_in_order(portal, tmp_path, capsys):
    principal, anexo = tmp_path / "contestacao.pdf", tmp_path / "ficha.pdf"
    principal.write_bytes(b"%PDF-principal")
    anexo.write_bytes(b"%PDF-anexo")
    portal.criar_rascunho.return_value = {"id": 77}
    _rodar(
        ["peticao", "rascunho", PROCESSO["numeroProcesso"], str(principal), "--tipo", "533"]
        + ["--anexo", str(anexo), "--tipo-anexo", "Anexo", "--confirmar"]
    )
    docs = [c.args[0] for c in portal.anexar.call_args_list]
    assert [(d["nome"], d["principal"], d["ordem"], d["idTipoDocumento"]) for d in docs] == [
        ("contestacao.pdf", True, 0, 533),
        ("ficha.pdf", False, 1, 9),
    ]
    assert "Rascunho 77 criado" in capsys.readouterr().out
    portal.protocolar.assert_not_called()


def test_rascunho_stops_when_court_does_not_accept_petitions(portal, tmp_path, capsys):
    portal.tribunal.return_value = None
    pdf = tmp_path / "contestacao.pdf"
    pdf.write_bytes(b"%PDF")
    with pytest.raises(SystemExit):
        _rodar(["peticao", "rascunho", PROCESSO["numeroProcesso"], str(pdf), "--tipo", "533", "--confirmar"])
    assert "peticione no sistema do tribunal" in capsys.readouterr().out
    portal.criar_rascunho.assert_not_called()


def test_protocolar_requires_confirm(portal, capsys):
    portal.peticao.return_value = {
        "siglaTribunal": "TRF1",
        "numeroProcesso": PROCESSO["numeroProcesso"],
        "peticaoDocumentos": [
            {"documento": {"ordem": 0, "nome": "contestacao.pdf", "nomeTipoDocumento": "Contestação"}}
        ],
    }
    _rodar(["peticao", "protocolar", "77"])
    assert "Nada foi protocolado" in capsys.readouterr().out
    portal.protocolar.assert_not_called()
    portal.protocolar.return_value = {"numeroReciboCnj": "20264000000000001", "status": "AJ"}
    _rodar(["peticao", "protocolar", "77", "--confirmar"])
    portal.protocolar.assert_called_once_with(77)
    assert "20264000000000001" in capsys.readouterr().out


def test_protocolar_refuses_empty_draft(portal):
    portal.peticao.return_value = {"peticaoDocumentos": []}
    with pytest.raises(SystemExit):
        _rodar(["peticao", "protocolar", "77", "--confirmar"])
    portal.protocolar.assert_not_called()


def test_excluir_requires_confirm(portal, capsys):
    _rodar(["peticao", "excluir", "77"])
    portal.excluir.assert_not_called()
    _rodar(["peticao", "excluir", "77", "--confirmar"])
    portal.excluir.assert_called_once_with(77)
