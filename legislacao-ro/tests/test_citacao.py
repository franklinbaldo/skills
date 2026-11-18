# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest"]
# ///
"""Citações e normalização de busca: stdlib pura."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from legislacao_citacao import (  # noqa: E402
    Citacao,
    normalizar_busca,
    normalizar_tipo,
    parse_artigo,
    parse_citacao,
    termos_busca,
)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("LC 68/1992", Citacao("lc", 68, "", 1992)),
        ("lc 68/92", Citacao("lc", 68, "", 1992)),
        ("LC68/92", Citacao("lc", 68, "", 1992)),
        ("L.C. 68", Citacao("lc", 68)),
        ("Lei Complementar nº 68, de 09-12-1992", Citacao("lc", 68, "", 1992)),
        ("Lei Complementar n° 68, de 9/12/1992", Citacao("lc", 68, "", 1992)),
        ("Lei Complementar n. 68, de 9 de dezembro de 1992", Citacao("lc", 68, "", 1992)),
        ("Lei 1.234", Citacao("lei", 1234)),
        ("Lei 1234", Citacao("lei", 1234)),
        ("lei nº 5.348/2022", Citacao("lei", 5348, "", 2022)),
        ("Lei ordinária 5", Citacao("lei", 5)),
        ("Lei 1234 de 2020", Citacao("lei", 1234, "", 2020)),
        ("Decreto 12345", Citacao("decreto", 12345)),
        ("Decreto 12.345", Citacao("decreto", 12345)),
        ("decreto nº 12.345/22", Citacao("decreto", 12345, "", 2022)),
        ("Dec. 100/2000", Citacao("decreto", 100, "", 2000)),
        ("Decreto-Lei 9-A/1982", Citacao("decreto-lei", 9, "a", 1982)),
        ("Decreto lei nº 9A", Citacao("decreto-lei", 9, "a")),
        ("DL 9", Citacao("decreto-lei", 9)),
    ],
)
def test_formas_de_citacao(texto: str, esperado: Citacao) -> None:
    assert parse_citacao(texto) == esperado


@pytest.mark.parametrize(
    "texto", ["plano de carreira", "lei 80 educação", "68/1992", "Lei 12/995", "constituição 5", "decreto regulamenta"]
)
def test_o_que_nao_e_citacao(texto: str) -> None:
    assert parse_citacao(texto) is None


def test_ano_de_dois_digitos() -> None:
    assert parse_citacao("lc 1/81").ano == 1981
    assert parse_citacao("lc 1/99").ano == 1999
    assert parse_citacao("lc 1/00").ano == 2000
    assert parse_citacao("lc 1/26").ano == 2026


def test_citacao_curta() -> None:
    assert Citacao("decreto-lei", 9, "a", 1982).curta() == "Decreto-Lei 9A/1982"


def test_normalizacao_igual_a_do_catalogo() -> None:
    assert normalizar_busca("Lei nº 1.234 — Crédito Suplementar") == "lei n 1 234 credito suplementar"
    assert termos_busca("Lei 1.234 Educação") == ["lei", "1234", "educacao"]


def test_tipo_e_artigo() -> None:
    assert normalizar_tipo("Lei Complementar") == "lc"
    assert normalizar_tipo("decreto_lei") == "decreto-lei"
    assert normalizar_tipo("portaria") is None
    assert parse_artigo("art. 5º") == (5, "")
    assert parse_artigo("5-A") == (5, "a")
    assert parse_artigo("cinco") is None
