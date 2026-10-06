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
"""Regressões offline: somente dados sintéticos e transporte HTTP simulado."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import consultar_dare as dare


def codigo_sintetico(modulo: str = "6") -> str:
    # Construído do zero; nunca copiado de guia ou enviado a serviço externo.
    sem_dv = "80" + modulo + "0" * 40
    calc = dare.calcular_dv_modulo10 if modulo in "67" else dare.calcular_dv_modulo11
    return sem_dv[:3] + str(calc(sem_dv)) + sem_dv[3:]


def comprovante(data: str = "01/01/2026", valor: str = "1,00", receita: str = "0001") -> str:
    return (
        '<div class="legacy-title">COMPROVANTE DE PAGAMENTO DE DARE</div>'
        f"Data Pagamento:</b><span>{data}</span>"
        f"Cod. Receita:</b><span>{receita}</span>"
        f"Valor Total</b><span>{valor}</span>"
    )


class ConversaoDareTests(unittest.TestCase):
    def test_modulo10_calculo(self) -> None:
        self.assertEqual(dare.calcular_dv_modulo10("0" * 11), 0)
        self.assertEqual(dare.calcular_dv_modulo10("0" * 10 + "1"), 8)

    def test_modulo11_calculo(self) -> None:
        for ultimo, esperado in (("0", 0), ("1", 9), ("5", 1), ("6", 0)):
            self.assertEqual(dare.calcular_dv_modulo11("0" * 10 + ultimo), esperado)

    def test_conversao_44_para_48_e_vice_versa(self) -> None:
        for modulo in "6789":
            codigo = codigo_sintetico(modulo)
            linha = dare.converter_codigo_barras_para_linha_digitavel(codigo)
            self.assertEqual(len(linha), 48)
            self.assertIsNone(dare.codigo_invalido(codigo))
            self.assertIsNone(dare.codigo_invalido(linha))
            self.assertEqual(dare.converter_linha_digitavel_para_codigo_barras(linha), codigo)

    def test_tolerancia_a_espacos_e_pontuacao(self) -> None:
        linha = dare.converter_codigo_barras_para_linha_digitavel(codigo_sintetico())
        formatado = " .- ".join(linha[i : i + 12] for i in range(0, 48, 12))
        self.assertIsNone(dare.codigo_invalido(formatado))
        self.assertEqual(dare.converter_codigo_barras_para_linha_digitavel(formatado), linha)

    def test_codigo_invalido_dispara_erro(self) -> None:
        with self.assertRaises(ValueError):
            dare.converter_codigo_barras_para_linha_digitavel("12345")

    def test_verificadores_invalidos(self) -> None:
        codigo = codigo_sintetico()
        self.assertIsNotNone(dare.codigo_invalido(codigo[:3] + str((int(codigo[3]) + 1) % 10) + codigo[4:]))
        linha = dare.converter_codigo_barras_para_linha_digitavel(codigo)
        for bloco in range(4):
            pos = bloco * 12 + 11
            self.assertIsNotNone(dare.codigo_invalido(linha[:pos] + str((int(linha[pos]) + 1) % 10) + linha[pos + 1 :]))
        self.assertIsNotNone(dare.codigo_invalido("x" + codigo))


class ConsultaDareTests(unittest.TestCase):
    def test_normaliza_request_e_arquivo_sem_rede(self) -> None:
        codigo = codigo_sintetico()
        linha = dare.converter_codigo_barras_para_linha_digitavel(codigo)
        for entrada in (codigo, "-".join(linha[i : i + 12] for i in range(0, 48, 12))):

            def handler(request: httpx.Request) -> httpx.Response:
                self.assertEqual(request.url.params["numero_guia_cbarras"], linha)
                return httpx.Response(200, text=comprovante())

            with httpx.Client(transport=httpx.MockTransport(handler)) as client, tempfile.TemporaryDirectory() as tmp:
                res = dare.consultar_guia(client, entrada, pasta_destino=Path(tmp))
                self.assertEqual(res.codigo, linha)
                self.assertEqual(res.situacao, "pago")
                self.assertEqual(len(list(Path(tmp).glob("*.html"))), 1)

    def test_invalido_nao_consulta(self) -> None:
        with httpx.Client(transport=httpx.MockTransport(lambda _: self.fail("HTTP inesperado"))) as client:
            with self.assertRaises(ValueError):
                dare.consultar_guia(client, "12345")

    def test_classificacao(self) -> None:
        for html, esperado in (
            (comprovante(), "pago"),
            (comprovante("Não informado", "0,00", "0000"), "nao_encontrado"),
            ("<html>Manutenção</html>", "erro"),
            (comprovante("", "1,00"), "erro"),
            (comprovante("01/01/2026", "0,00"), "erro"),
        ):
            self.assertEqual(dare.extrair_dados_comprovante(html, "sintetico").situacao, esperado)

    def test_lote_com_erro_parcial_e_exportacoes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arquivo = root / "guias.json"
            arquivo.write_text(json.dumps([{"codigo": codigo_sintetico()}, {"codigo": ""}]))
            sucesso = dare.extrair_dados_comprovante(comprovante(), "sintetico")
            with (
                patch.object(dare, "consultar_guia", return_value=sucesso),
                patch.object(dare.time, "sleep"),
                patch.object(dare.httpx, "Client"),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = dare.main(arquivo=arquivo, json_out=root / "out/dados.json", csv_out=root / "out/dados.csv")
            self.assertEqual(code, 1)
            resultados = json.loads((root / "out/dados.json").read_text())
            self.assertEqual([r["situacao"] for r in resultados], ["pago", "erro"])
            self.assertTrue((root / "out/dados.csv").exists())

    def test_timeout_falha_total(self) -> None:
        with patch.object(dare, "consultar_guia", side_effect=httpx.ReadTimeout("simulado")):
            with (
                patch.object(dare.time, "sleep"),
                patch.object(dare.httpx, "Client"),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(dare.main(codigo=codigo_sintetico()), 1)

    def test_sucesso_e_negativo_verificado(self) -> None:
        for html in (comprovante(), comprovante("Não informado", "0,00", "0000")):
            resultado = dare.extrair_dados_comprovante(html, "sintetico")
            with patch.object(dare, "consultar_guia", return_value=resultado):
                with (
                    patch.object(dare.time, "sleep"),
                    patch.object(dare.httpx, "Client"),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(dare.main(codigo=codigo_sintetico()), 0)

    def test_cli_exit_status(self) -> None:
        script = str(Path(dare.__file__).resolve())
        for args, code in (([], 1), (["--codigo", "12345"], 1), (["--help"], 0)):
            proc = subprocess.run(
                [sys.executable, script, *args],
                capture_output=True,
                text=True,
                check=False,
                env={k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")},
            )
            self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
