#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
# ]
# ///
"""Regressão da conversão de número antigo do TJRO, sem rede.

Os pares antigo → CNJ abaixo foram conferidos no DataJud em 03/11/2026.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numero_antigo as na  # noqa: E402


class ConversaoTests(unittest.TestCase):
    def test_pares_conferidos_no_datajud(self) -> None:
        for antigo, esperado in (
            ("001.1993.006868-9", "0068689-57.1993.8.22.0001"),
            ("00119950175057", "0175057-22.1995.8.22.0001"),
            ("001.1997.003786-5", "0037865-76.1997.8.22.0001"),
        ):
            with self.subTest(antigo=antigo):
                (c,) = na.converter(antigo)["candidatos"]
                self.assertEqual(c["cnj"], esperado)

    def test_ano_com_dois_digitos(self) -> None:
        (c,) = na.converter("006.01.000138-2")["candidatos"]
        self.assertEqual(c["appg"], "00620010001382")
        self.assertEqual(c["cnj"], "0001382-90.2001.8.22.0006")
        (c,) = na.converter("001.97.003786-5")["candidatos"]
        self.assertEqual(c["antigo"], "001.1997.003786-5")

    def test_sequencial_sem_zeros(self) -> None:
        (c,) = na.converter("006.2005.1624-0")["candidatos"]
        self.assertEqual(c["appg"], "00620050016240")

    def test_sem_digito_gera_dez_candidatos(self) -> None:
        linha = na.converter("006.2001.000138")
        self.assertFalse(linha["digito_informado"])
        self.assertEqual(len(linha["candidatos"]), 10)
        self.assertIn("00620010001382", [c["appg"] for c in linha["candidatos"]])

    def test_comarca_pelo_foro(self) -> None:
        self.assertEqual(na.converter("006.2001.000138-2")["comarca"], "Presidente Médici")

    def test_rejeita_texto_que_nao_e_numero(self) -> None:
        with self.assertRaises(ValueError):
            na.converter("0001382-90.2001.8.22.0006")


if __name__ == "__main__":
    unittest.main()
