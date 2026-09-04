#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "markitdown[pdf]",
#     "pymupdf",
# ]
# ///
"""Regression tests for convert_pdf.py's extraction and splitting contract."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import convert_pdf  # noqa: E402  — script vizinho, resolvido pelo sys.path acima


class SplitOnMarkersTests(unittest.TestCase):
    def test_unpaginated_text_splits_at_each_document_marker(self) -> None:
        text = "capa do processo\n\nSENTENÇA\ncorpo um\n\nDESPACHO\ncorpo dois\n"
        chunks = convert_pdf.split_on_markers(text)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(chunks[1].startswith("SENTENÇA"))
        self.assertTrue(chunks[2].startswith("DESPACHO"))

    def test_text_without_markers_stays_one_chunk(self) -> None:
        self.assertEqual(convert_pdf.split_on_markers("nada aqui"), ["nada aqui"])


class IntoDocumentsTests(unittest.TestCase):
    def test_marker_at_the_start_of_a_page_opens_a_document(self) -> None:
        extraction = convert_pdf.Extraction(
            chunks=["capa", "SENTENÇA DE MÉRITO\ncorpo", "continuação", "DESPACHO\nfim"],
            paginated=True,
        )
        documents = extraction.into_documents()
        self.assertEqual(
            [document.title for document in documents],
            ["Documento_Geral", "SENTENÇA DE MÉRITO", "DESPACHO"],
        )
        self.assertEqual(documents[1].chunks, ["SENTENÇA DE MÉRITO\ncorpo", "continuação"])

    def test_page_numbering_is_global_across_documents(self) -> None:
        extraction = convert_pdf.Extraction(
            chunks=["capa", "SENTENÇA\ncorpo"], paginated=True
        )
        rendered = extraction.into_documents()[1].render()
        self.assertIn("<!-- Page 2 -->", rendered)

    def test_unpaginated_extraction_emits_no_page_comments(self) -> None:
        extraction = convert_pdf.Extraction(
            chunks=["capa", "SENTENÇA\ncorpo"], paginated=False
        )
        for document in extraction.into_documents():
            self.assertNotIn("<!-- Page", document.render())


class MarkitdownExtractionTests(unittest.TestCase):
    def test_missing_markitdown_returns_no_extraction_instead_of_raising(self) -> None:
        original = convert_pdf.load_markitdown
        convert_pdf.load_markitdown = lambda: None
        try:
            self.assertIsNone(convert_pdf.extract_with_markitdown(Path("x.pdf")))
        finally:
            convert_pdf.load_markitdown = original

    def test_markitdown_output_is_never_reported_as_paginated(self) -> None:
        class FakeResult:
            text_content = "SENTENÇA\ncorpo"

        class FakeMarkItDown:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

            def convert(self, source: object, **kwargs: object) -> FakeResult:
                return FakeResult()

        original = convert_pdf.load_markitdown
        convert_pdf.load_markitdown = lambda: FakeMarkItDown
        try:
            extraction = convert_pdf.extract_with_markitdown(Path("x.pdf"))
        finally:
            convert_pdf.load_markitdown = original
        self.assertIsNotNone(extraction)
        self.assertFalse(extraction.paginated)


class PymupdfExtractionTests(unittest.TestCase):
    def test_real_pdf_pages_are_paginated(self) -> None:
        pymupdf = __import__("fitz")
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "sample.pdf"
            document = pymupdf.open()
            for text in ("SENTENÇA\nprimeira", "segunda"):
                page = document.new_page()
                page.insert_text((72, 72), text)
            document.save(str(pdf_path))
            document.close()

            extraction = convert_pdf.extract_with_pymupdf(pdf_path)

        self.assertIsNotNone(extraction)
        self.assertTrue(extraction.paginated)
        self.assertEqual(len(extraction.chunks), 2)

    def test_unreadable_file_returns_no_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            broken = Path(directory) / "broken.pdf"
            broken.write_text("not a pdf", encoding="utf-8")
            self.assertIsNone(convert_pdf.extract_with_pymupdf(broken))


if __name__ == "__main__":
    unittest.main()
