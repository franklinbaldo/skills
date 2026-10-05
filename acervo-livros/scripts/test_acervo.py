# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "defusedxml>=0.7",
# ]
# ///
"""Testes offline do acervo.py: conversores, divisão em capítulos e travas de licença."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import acervo  # noqa: E402

PARAGRAFO = " ".join(["palavra"] * 320)


def _epub(capitulos: list[tuple[str, str]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr(
            "META-INF/container.xml",
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
            '<rootfile full-path="OEBPS/c.opf"/></rootfiles></container>',
        )
        itens = "".join(f'<item id="c{i}" href="c{i}.xhtml"/>' for i in range(len(capitulos)))
        spine = "".join(f'<itemref idref="c{i}"/>' for i in range(len(capitulos)))
        z.writestr(
            "OEBPS/c.opf",
            '<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
            "<dc:title>Livro de Teste</dc:title></metadata>"
            f"<manifest>{itens}</manifest><spine>{spine}</spine></package>",
        )
        for i, (titulo, texto) in enumerate(capitulos):
            z.writestr(f"OEBPS/c{i}.xhtml", f"<html><body><h2>{titulo}</h2><p>{texto}</p></body></html>")
    return buf.getvalue()


class TestHtmlParaMd(unittest.TestCase):
    def test_titulos_paragrafos_e_enfase(self) -> None:
        md = acervo.html_para_md("<h2>Cap</h2><p>Um <em>dois</em> <b>três</b></p>")
        self.assertEqual(md, "## Cap\n\nUm *dois* **três**")

    def test_descarta_navegacao_do_wikisource(self) -> None:
        md = acervo.html_para_md('<div class="ws-noexport">← anterior</div><p>Texto</p><sup>[1]</sup>')
        self.assertEqual(md, "Texto")


class TestDivisao(unittest.TestCase):
    def test_escolhe_nivel_com_secoes_substanciais(self) -> None:
        md = "\n\n".join(f"## Conto {n}\n\n### I\n\n{PARAGRAFO}\n\n### II\n\n{PARAGRAFO}" for n in range(3))
        caps = acervo._dividir_em_capitulos(md, "x")  # noqa: SLF001
        self.assertEqual([c.titulo for c in caps], ["Conto 0", "Conto 1", "Conto 2"])

    def test_sem_titulos_vira_um_capitulo(self) -> None:
        caps = acervo._dividir_em_capitulos(PARAGRAFO, "Único")  # noqa: SLF001
        self.assertEqual([c.titulo for c in caps], ["Único"])

    def test_tira_moldura_do_gutenberg(self) -> None:
        md = (
            "lixo\n*** START OF THE PROJECT GUTENBERG EBOOK X ***\n"
            "miolo\n*** END OF THE PROJECT GUTENBERG EBOOK X ***\nlicença"
        )
        self.assertEqual(acervo._sem_moldura_gutenberg(md), "miolo")  # noqa: SLF001


class TestConversores(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_epub_por_spine_e_titulo(self) -> None:
        arquivo = self.tmp / "l.epub"
        arquivo.write_bytes(_epub([("Primeiro", PARAGRAFO), ("Segundo", PARAGRAFO), ("Terceiro", PARAGRAFO)]))
        titulo, caps = acervo.converter_arquivo(arquivo)
        self.assertEqual(titulo, "Livro de Teste")
        self.assertEqual([c.titulo for c in caps], ["Primeiro", "Segundo", "Terceiro"])

    def test_docx_estilo_de_titulo(self) -> None:
        w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        corpo = "".join(
            f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Parte {n}</w:t></w:r></w:p>'
            f"<w:p><w:r><w:t>{PARAGRAFO}</w:t></w:r></w:p>"
            for n in range(3)
        )
        arquivo = self.tmp / "d.docx"
        with zipfile.ZipFile(arquivo, "w") as z:
            z.writestr("word/document.xml", f"<w:document {w}><w:body>{corpo}</w:body></w:document>")
        _, caps = acervo.converter_arquivo(arquivo)
        self.assertEqual([c.titulo for c in caps], ["Parte 0", "Parte 1", "Parte 2"])

    def test_txt_desfaz_quebra_dura(self) -> None:
        arquivo = self.tmp / "t.txt"
        arquivo.write_text("CAPÍTULO I\n\nlinha um\nlinha dois\n", encoding="utf-8")
        _, caps = acervo.converter_arquivo(arquivo)
        self.assertIn("linha um linha dois", caps[0].texto)

    def test_formato_desconhecido(self) -> None:
        arquivo = self.tmp / "x.xyz"
        arquivo.write_text("?", encoding="utf-8")
        with self.assertRaises(acervo.ErroAcervoError):
            acervo.converter_arquivo(arquivo)

    def test_gravar_cria_capitulos_livro_e_meta(self) -> None:
        caps = [acervo.Capitulo("Um", "## Um\n\ntexto"), acervo.Capitulo("Dois", "## Dois\n\ntexto")]
        pasta = acervo.gravar("T", caps, self.tmp / "saida", acervo.Meta("T", "local"))
        nomes = sorted(p.name for p in pasta.iterdir())
        self.assertEqual(nomes, ["01-um.md", "02-dois.md", "livro.md", "meta.json"])


class TestTravasDeLicenca(unittest.TestCase):
    def test_gutenberg_recusa_sem_dominio_publico(self) -> None:
        feed = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><rights>Copyrighted.</rights></entry></feed>'
        with mock.patch.object(acervo, "_abrir", return_value=feed), self.assertRaises(acervo.ErroAcervoError):
            acervo.baixar_gutenberg("1", Path(tempfile.mkdtemp()))

    def test_archive_recusa_sem_marca_de_dominio_publico(self) -> None:
        with (
            mock.patch.object(acervo, "_json", return_value={"metadata": {"title": "x"}, "files": []}),
            self.assertRaises(acervo.ErroAcervoError),
        ):
            acervo.baixar_archive("x", Path(tempfile.mkdtemp()))


class TestCli(unittest.TestCase):
    def test_converter_arquivo_inexistente_sai_com_1(self) -> None:
        try:
            codigo = acervo.main(["converter", "/nao/existe.epub"])
        except SystemExit as saida:  # cyclopts recentes encerram com o int devolvido
            codigo = saida.code
        self.assertEqual(codigo, 1)


if __name__ == "__main__":
    unittest.main()
