# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "cyclopts>=3.0", "duckdb>=1.1"]
# ///
"""Consultas ponta a ponta sobre Parquet minúsculos, sempre offline (`--base-url` aponta para um diretório)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "scripts"))
sys.path.insert(0, str(AQUI))

import legislacao_ro as cli  # noqa: E402
from legislacao_dados_teste import gravar_todos, nid  # noqa: E402


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for nome in ("BASE_URL", "CATALOGO", "RELACOES", "TEXTOS", "VERSOES", "TTL_HORAS"):
        monkeypatch.delenv(f"LEGISLACAO_RO_{nome}", raising=False)
    monkeypatch.setenv("LEGISLACAO_RO_CACHE", str(tmp_path / "cache"))


@pytest.fixture
def dados(tmp_path: Path) -> Path:
    return gravar_todos(tmp_path / "dados")


def rodar(capsys: pytest.CaptureFixture[str], dados: Path, *args: str) -> tuple[int, Any, str]:
    codigo = cli.main([*args, "--base-url", str(dados)])
    saida = capsys.readouterr()
    try:
        corpo = json.loads(saida.out)
    except ValueError:
        corpo = saida.out
    return codigo, corpo, saida.err


def ids(resultado: dict[str, Any]) -> list[str]:
    return [r["citacao_curta"] for r in resultado["resultados"]]


def test_busca_ignora_acento_e_exige_todos_os_termos(capsys, dados) -> None:
    for consulta in ("educacao", "EDUCAÇÃO", "plano carreira educacao", "Plano de Carreira"):
        _, r, _ = rodar(capsys, dados, "buscar", consulta, "--tipo", "lei")
        assert ids(r) == ["Lei 1234/2005"], consulta
    _, r, _ = rodar(capsys, dados, "buscar", "plano parque")
    assert r["total"] == 0


def test_busca_numero_exato_primeiro_depois_mais_recentes(capsys, dados) -> None:
    _, r, _ = rodar(capsys, dados, "buscar", "complementar 68")
    # LC 68 (exata) antes de LC 101 e LC 100, que só citam "68" e são mais recentes.
    assert ids(r) == ["LC 68/1992", "LC 101/2003", "LC 100/2001"]
    _, r, _ = rodar(capsys, dados, "buscar", "lei 80")
    assert ids(r)[0] == "Lei 80/1990"


def test_filtros_tipo_ano_intervalo_situacao_limite(capsys, dados) -> None:
    _, r, _ = rodar(capsys, dados, "buscar", "--tipo", "Lei Complementar")
    assert ids(r) == ["LC 101/2003", "LC 100/2001", "LC 68/1992", "LC 1/1984"]
    _, r, _ = rodar(capsys, dados, "buscar", "--tipo", "lc", "--ano", "2001")
    assert ids(r) == ["LC 100/2001"]
    _, r, _ = rodar(capsys, dados, "buscar", "--tipo", "lc", "--de", "1990", "--ate", "2002")
    assert ids(r) == ["LC 100/2001", "LC 68/1992"]
    _, r, _ = rodar(capsys, dados, "buscar", "--situacao", "revogada")
    assert sorted(ids(r)) == ["Decreto 12345/2010", "LC 1/1984"]
    _, r, _ = rodar(capsys, dados, "buscar", "--tipo", "lc", "--limite", "1")
    assert r["total"] == 4
    assert r["retornados"] == 1


def test_busca_por_citacao(capsys, dados) -> None:
    _, r, _ = rodar(capsys, dados, "buscar", "LC 68/1992")
    assert r["modo"] == "citacao"
    assert ids(r) == ["LC 68/1992"]
    _, r, _ = rodar(capsys, dados, "buscar", "Lei 1.234")
    assert ids(r) == ["Lei 1234/2005"]
    _, r, _ = rodar(capsys, dados, "buscar", "Decreto 12345")
    assert ids(r) == ["Decreto 12345/2010"]
    _, r, _ = rodar(capsys, dados, "buscar", "LC 68/1999")
    assert r["total"] == 0
    assert "dica" in r


def test_busca_sem_criterio_e_tipo_invalido(capsys, dados) -> None:
    codigo, _, erro = rodar(capsys, dados, "buscar")
    assert codigo == 2
    assert "informe" in erro
    codigo, _, erro = rodar(capsys, dados, "buscar", "x", "--tipo", "portaria")
    assert codigo == 2


def test_norma_relacoes_nos_dois_sentidos_e_nao_resolvida(capsys, dados) -> None:
    codigo, r, _ = rodar(capsys, dados, "norma", "LC 68/1992")
    assert codigo == 0
    assert r["norma"]["norma_id"] == nid("lc", 68)
    assert r["situacao_no_indice"]["valor"] == "tem-compilada"
    assert "não é marca de revogação nem de vigência" in r["situacao_no_indice"]["leitura"]
    assert r["situacao_no_indice"]["evidencias"] == ["rendicao-compilada"]
    assert "não é parecer de vigência" in r["situacao_no_indice"]["aviso"]
    assert r["links"]["internet_archive"] == "https://ia/lc68.pdf"
    assert "NÃO é a publicação original" in r["links"]["aviso"]
    assert r["cobertura"]["estagio"] == "estruturada"
    saida = r["relacoes"]["saida"]
    assert [i["outra_norma"]["citacao_curta"] for i in saida["revoga"]] == ["LC 1/1984"]
    entrada = r["relacoes"]["entrada"]
    assert [i["outra_norma"]["citacao_curta"] for i in entrada["altera"]] == ["LC 100/2001"]
    assert "automaticamente" in r["relacoes"]["aviso"]
    _, r100, _ = rodar(capsys, dados, "norma", "LC 100/2001")
    nao_resolvida = [i for i in r100["relacoes"]["saida"]["altera"] if not i["resolvida"]]
    assert [i["como_escrito"] for i in nao_resolvida] == ["Resolução 5"]
    assert nao_resolvida[0]["outra_norma"] is None


def test_relacoes_comando_filtra_direcao_e_verbo(capsys, dados) -> None:
    _, r, _ = rodar(capsys, dados, "relacoes", "LC 68/1992", "--direcao", "entrada")
    assert r["contagem"] == {"saida": 0, "entrada": 1}
    assert r["relacoes"]["entrada"]["altera"][0]["trecho"].startswith("altera")
    _, r, _ = rodar(capsys, dados, "relacoes", "LC 68/1992", "--direcao", "saida")
    assert r["contagem"] == {"saida": 1, "entrada": 0}
    assert r["relacoes"]["saida"]["revoga"][0]["fonte_relacao"] == "anotacao-do-indice"
    _, r, _ = rodar(capsys, dados, "relacoes", "Lei 1234", "--verbo", "regulamenta")
    assert r["relacoes"]["entrada"]["regulamenta"][0]["parcial"] is True


def test_citacao_inexistente_ano_divergente_e_ambigua(capsys, dados) -> None:
    codigo, _, erro = rodar(capsys, dados, "norma", "Lei 9999/2020")
    assert codigo == 1
    assert "não consta" in erro
    codigo, _, erro = rodar(capsys, dados, "norma", "LC 68/1999")
    assert codigo == 1
    assert "data diferente" in erro
    codigo, _, erro = rodar(capsys, dados, "norma", "bobagem")
    assert codigo == 2
    codigo, r, _ = rodar(capsys, dados, "norma", "Decreto-Lei 9")
    assert codigo == 0
    assert r["norma"]["sufixo"] == ""
    codigo, r, _ = rodar(capsys, dados, "norma", "Decreto-Lei 9A")
    assert r["norma"]["sufixo"] == "a"


def test_texto_estruturado_e_artigo(capsys, dados) -> None:
    _, r, _ = rodar(capsys, dados, "texto", "LC 68/1992")
    assert r["fonte"] == "versoes"
    assert [d["path"] for d in r["dispositivos"]] == [
        "ementa", "art-1", "art-5", "art-5-inc-1", "art-5-inc-2", "art-5-par-1", "art-5-par-1-inc-1", "art-6",
    ]  # fmt: skip
    assert any("confira" in a for a in r["avisos"])
    codigo, r, _ = rodar(capsys, dados, "texto", "LC 68/1992", "--artigo", "5")
    assert codigo == 0
    assert r["recorte"] == "art-5"
    assert [d["path"] for d in r["dispositivos"]][:3] == ["art-5", "art-5-inc-1", "art-5-inc-2"]
    assert "art-6" not in [d["path"] for d in r["dispositivos"]]
    # só a versão mais recente do § 1º
    assert [d["texto"] for d in r["dispositivos"] if d["path"] == "art-5-par-1"] == ["Parágrafo primeiro."]
    codigo, _, erro = rodar(capsys, dados, "texto", "LC 68/1992", "--artigo", "99")
    assert codigo == 1
    assert "art-99" in erro


def test_texto_so_ocr_com_ancoras_que_fecham(capsys, dados) -> None:
    _, r, _ = rodar(capsys, dados, "texto", "Lei 1234")
    assert r["fonte"] == "textos"
    assert "OCR" in r["descricao_da_fonte"]
    assert r["texto"].startswith("DECRETA:")
    assert any("PDF original prevalece" in a for a in r["avisos"])
    _, r, _ = rodar(capsys, dados, "texto", "Lei 1234", "--artigo", "2")
    assert r["texto"] == "Art. 2º Segundo artigo."
    _, r, _ = rodar(capsys, dados, "texto", "Lei 1234", "--artigo", "3")
    assert r["texto"].startswith("Art. 3º Terceiro.")
    assert any("último artigo" in a for a in r["avisos"])
    _, r, _ = rodar(capsys, dados, "texto", "Lei 1234", "--max", "5")
    assert r["texto"] == "DECRE"
    codigo, _, erro = rodar(capsys, dados, "texto", "Lei 1234", "--artigo", "9")
    assert codigo == 1


def test_texto_so_ocr_sem_ancoras_recusa_artigo(capsys, dados) -> None:
    codigo, r, _ = rodar(capsys, dados, "texto", "Decreto 12345", "--artigo", "1")
    assert codigo == 1
    assert r["texto"] is None
    assert any("não é confiável" in a for a in r["avisos"])
    assert r["links"]["melhor"]
    codigo, r, _ = rodar(capsys, dados, "texto", "Decreto 12345")
    assert codigo == 0
    assert r["texto"] == "Texto ilegível Art. 1º e depois Art. 4º solto."


def test_texto_com_sufixo_avisa_ambiguidade_e_norma_sem_texto(capsys, dados) -> None:
    _, r, _ = rodar(capsys, dados, "texto", "Decreto-Lei 9A")
    assert any("outra delas" in a for a in r["avisos"])
    codigo, r, erro = rodar(capsys, dados, "texto", "Lei 80")
    assert codigo == 1
    assert r["norma"]["citacao_curta"] == "Lei 80/1990"
    assert "não tem texto" in erro


def test_texto_versus_dispositivo_e_fonte_textos(capsys, dados) -> None:
    _, r, _ = rodar(capsys, dados, "texto", "LC 68/1992", "--dispositivo", "art-5-par-1")
    assert [d["path"] for d in r["dispositivos"]] == ["art-5-par-1", "art-5-par-1-inc-1"]
    codigo, _, erro = rodar(capsys, dados, "texto", "LC 68/1992", "--artigo", "1", "--dispositivo", "art-1")
    assert codigo == 2
    codigo, _, erro = rodar(capsys, dados, "texto", "LC 68/1992", "--fonte", "textos")
    assert codigo == 1  # LC 68 só existe estruturada


def test_formato_texto_legivel(capsys, dados) -> None:
    codigo = cli.main(["norma", "LC 68/1992", "--formato", "texto", "--base-url", str(dados)])
    saida = capsys.readouterr().out
    assert codigo == 0
    assert "Situação no índice oficial: tem-compilada" in saida
    assert "alterada por" in saida
    assert "AVISO: relações extraídas automaticamente" in saida
    codigo = cli.main(["texto", "Lei 1234", "--formato", "texto", "--base-url", str(dados)])
    saida = capsys.readouterr().out
    assert "FONTE DO TEXTO: textos" in saida


def test_dataset_exigido_ausente_nomeia_o_dataset(capsys, tmp_path: Path) -> None:
    dados = gravar_todos(tmp_path / "sem-relacoes", sem=("relacoes",))
    codigo, _, erro = rodar(capsys, dados, "relacoes", "LC 68/1992")
    assert codigo == 3
    assert "dataset 'relacoes' indisponível" in erro
    assert "Traceback" not in erro
    codigo, r, _ = rodar(capsys, dados, "norma", "LC 68/1992")
    assert codigo == 0
    assert r["relacoes"] is None
    assert any("'relacoes'" in a for a in r["avisos"])
    sem_catalogo = gravar_todos(tmp_path / "sem-catalogo", sem=("catalogo",))
    codigo, _, erro = rodar(capsys, sem_catalogo, "buscar", "plano")
    assert codigo == 3
    assert "dataset 'catalogo'" in erro


def test_texto_sem_nenhuma_fonte_de_texto(capsys, tmp_path: Path) -> None:
    dados = gravar_todos(tmp_path / "x", sem=("textos", "versoes"))
    codigo, _, erro = rodar(capsys, dados, "texto", "Lei 1234")
    assert codigo == 3
    assert "versoes" in erro
    assert "textos" in erro


def test_caminho_explicito_inexistente(capsys, tmp_path: Path) -> None:
    codigo = cli.main(["buscar", "x", "--catalogo", str(tmp_path / "nao-existe.parquet")])
    erro = capsys.readouterr().err
    assert codigo == 3
    assert "dataset 'catalogo'" in erro
    assert "nao-existe.parquet" in erro


def test_catalogo_formato_antigo_funciona_com_aviso(capsys, tmp_path: Path) -> None:
    dados = gravar_todos(tmp_path / "v01", catalogo_v01=True)
    _, r, _ = rodar(capsys, dados, "buscar", "educacao")
    assert ids(r) == ["Lei 1234/2005", "LC 101/2003"]
    assert any("formato 0.1" in a for a in r["avisos"])
    assert r["resultados"][0]["situacao_no_indice"] is None
    assert r["resultados"][0]["link"] == "https://oficial/lei1234.pdf"
    codigo, _, erro = rodar(capsys, dados, "buscar", "x", "--situacao", "revogada")
    assert codigo == 2
    _, n, _ = rodar(capsys, dados, "norma", "Lei 1234")
    assert n["situacao_no_indice"]["valor"] is None
    assert n["links"]["rendicoes_listadas"] == "original"
