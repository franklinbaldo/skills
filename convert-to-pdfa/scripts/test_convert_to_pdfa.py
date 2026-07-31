"""Regression tests for convert_to_pdfa.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import convert_to_pdfa
import pymupdf


class ConvertToPdfaTests(unittest.TestCase):
    """Exercise safety checks and the real Ghostscript backend."""

    def test_pdfa_claim_accepts_attribute_and_element_forms(self) -> None:
        """Both common XMP serializations must be recognized."""
        attribute = "<rdf:Description pdfaid:part='2' pdfaid:conformance='B'/>"
        element = (
            "<pdfaid:part>2</pdfaid:part><pdfaid:conformance>B</pdfaid:conformance>"
        )
        self.assertTrue(convert_to_pdfa._pdfa_claim(attribute, 2))
        self.assertTrue(convert_to_pdfa._pdfa_claim(element, 2))
        self.assertFalse(convert_to_pdfa._pdfa_claim(attribute, 1))

    def test_resolve_paths_refuses_in_place_and_existing_output(self) -> None:
        """Conversion never overwrites input or output without explicit force."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            source.write_bytes(b"%PDF-placeholder")
            with self.assertRaises(convert_to_pdfa.PdfaError):
                convert_to_pdfa._resolve_paths(str(source), str(source), force=False)

            output = Path(temp_dir) / "output.pdf"
            output.write_bytes(b"existing")
            with self.assertRaises(convert_to_pdfa.PdfaError):
                convert_to_pdfa._resolve_paths(str(source), str(output), force=False)

    def test_real_backend_preserves_text_and_geometry_for_all_parts(self) -> None:
        """A native-text page survives real PDF/A-1b, 2b, and 3b conversion."""
        backend, ghostscript = self._backend_or_skip()
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            self._make_source(source)

            for part in convert_to_pdfa.SUPPORTED_PARTS:
                with self.subTest(part=part):
                    output = Path(temp_dir) / f"source-PDFA-{part}b.pdf"
                    verification = convert_to_pdfa.convert(
                        source,
                        output,
                        part=part,
                        policy=2,
                        backend=backend,
                        ghostscript=ghostscript,
                        rasterize=False,
                        dpi=300,
                        require_verapdf=False,
                        allow_signed=False,
                    )

                    self.assertTrue(output.is_file())
                    self.assertEqual(verification.pages, 1)
                    self.assertEqual(verification.text_similarity, 1.0)
                    with pymupdf.open(output) as document:
                        self.assertIn("Texto pesquisável", document[0].get_text())

    def test_raster_fallback_is_explicitly_image_only(self) -> None:
        """The raster fallback preserves geometry but intentionally loses text."""
        backend, ghostscript = self._backend_or_skip()
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            output = Path(temp_dir) / "source-raster-PDFA.pdf"
            self._make_source(source)

            verification = convert_to_pdfa.convert(
                source,
                output,
                part=2,
                policy=2,
                backend=backend,
                ghostscript=ghostscript,
                rasterize=True,
                dpi=72,
                require_verapdf=False,
                allow_signed=False,
            )

            self.assertEqual(verification.pages, 1)
            self.assertIsNone(verification.text_similarity)
            with pymupdf.open(output) as document:
                self.assertEqual(document[0].get_text(), "")

    def _backend_or_skip(self) -> tuple[convert_to_pdfa.Backend, str | None]:
        try:
            return convert_to_pdfa._select_backend("auto")
        except convert_to_pdfa.PdfaError as error:
            self.skipTest(str(error))

    def _make_source(self, path: Path) -> None:
        with pymupdf.open() as document:
            page = document.new_page(width=595, height=842)
            page.insert_text((72, 72), "Texto pesquisável — PDF/A")
            page.draw_rect(pymupdf.Rect(70, 90, 300, 180), color=(0.1, 0.2, 0.8))
            document.save(path)


if __name__ == "__main__":
    unittest.main()
