#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4>=4.12.0",
#     "cyclopts>=3.0",
#     "httpx>=0.27.0",
#     "rich>=13.0.0",
# ]
# ///
"""Testes de regressão para o conversor e utilitários da consulta DARE SEFIN."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Adiciona o diretório do script ao sys.path para importação direta
sys.path.insert(0, str(Path(__file__).parent))

from consultar_dare import (
    calcular_dv_modulo10,
    converter_codigo_barras_para_linha_digitavel,
    converter_linha_digitavel_para_codigo_barras,
)


class ConversaoDareTests(unittest.TestCase):
    def test_modulo10_calculo(self) -> None:
        # Bloco de 11 dígitos da guia de arrecadação
        bloco = "85660000012"
        # O cálculo deve resultar no DV 4
        self.assertEqual(calcular_dv_modulo10(bloco), 4)

    def test_conversao_44_para_48_e_vice_versa(self) -> None:
        c44_puro = "85660000012046500227243053001389645215072572"
        c48_esperado = "856600000124046500227247305300138966452150725722"

        # Converte 44 -> 48
        c48_obtido = converter_codigo_barras_para_linha_digitavel(c44_puro)
        self.assertEqual(c48_obtido, c48_esperado)

        # Converte 48 -> 44
        c44_obtido = converter_linha_digitavel_para_codigo_barras(c48_esperado)
        self.assertEqual(c44_obtido, c44_puro)

    def test_tolerancia_a_espacos_e_pontuacao(self) -> None:
        c48_formatado = "85660000012-4 04650022724-7 30530013896-6 45215072572-2"
        c48_limpo = "856600000124046500227247305300138966452150725722"

        self.assertEqual(
            converter_codigo_barras_para_linha_digitavel(c48_formatado),
            c48_limpo,
        )

    def test_codigo_invalido_dispara_erro(self) -> None:
        with self.assertRaises(ValueError):
            converter_codigo_barras_para_linha_digitavel("12345")


if __name__ == "__main__":
    unittest.main()
