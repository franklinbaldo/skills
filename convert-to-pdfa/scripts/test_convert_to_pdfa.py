#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "pymupdf",
#     "pikepdf[pdfa]>=10.17",
# ]
# ///
"""Regression tests for convert_to_pdfa.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import convert_to_pdfa
import pikepdf
import pikepdf.pdfa
import pymupdf
from test_pikepdf_backend import make_vector_pdf


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

    def test_scoop_shim_is_followed_to_the_real_install(self) -> None:
        """A Scoop shim points elsewhere; PDFA_def.ps lives next to the real binary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            shims = Path(temp_dir) / "shims"
            shims.mkdir()
            shim_exe = shims / "gswin64c.exe"
            shim_exe.write_bytes(b"MZ")
            real = Path(temp_dir) / "apps" / "ghostscript" / "current" / "bin" / "gswin64c.exe"
            shim_exe.with_suffix(".shim").write_text(f'path = "{real}"\n', encoding="utf-8")
            self.assertEqual(convert_to_pdfa._scoop_target(shim_exe), real)
            plain = Path(temp_dir) / "gs"
            self.assertEqual(convert_to_pdfa._scoop_target(plain), plain)

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

    def _convert(self, source: Path, output: Path, backend: str) -> convert_to_pdfa.Verification:
        return convert_to_pdfa.convert(
            source,
            output,
            part=2,
            policy=2,
            backend=backend,
            ghostscript=None,
            rasterize=False,
            dpi=300,
            require_verapdf=False,
            allow_signed=False,
        )

    @staticmethod
    def _violation_report() -> pikepdf.pdfa.Report:
        finding = pikepdf.pdfa.Finding("ISO_19005_2:6.2.4.3-2", "page 1", "simulated violation", "violation")
        return pikepdf.pdfa.Report(flavour="2b", findings=[finding])

    def test_auto_promotes_with_pikepdf_without_ghostscript(self) -> None:
        """A document pikepdf can promote never reaches Ghostscript."""
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            convert_to_pdfa, "_select_backend", side_effect=AssertionError("Ghostscript was used")
        ):
            source = Path(temp_dir) / "source.pdf"
            make_vector_pdf(source)
            verification = self._convert(source, Path(temp_dir) / "out.pdf", "auto")
        self.assertEqual(verification.backend, "pikepdf (no Ghostscript)")
        self.assertEqual(verification.pages, 1)

    def test_auto_falls_back_to_ghostscript_on_a_pikepdf_violation(self) -> None:
        """A violation discards pikepdf's output and runs the Ghostscript path instead."""

        def fake_ghostscript(_gs: str, source: Path, candidate: Path, **_kwargs: object) -> None:
            with pikepdf.open(source) as pdf:
                pikepdf.pdfa.prepare(pdf, "2b")
                pdf.save(candidate, **pikepdf.pdfa.resolve_save_kwargs("2b"))

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            pikepdf.pdfa, "validate_written", return_value=self._violation_report()
        ), mock.patch.object(convert_to_pdfa, "_select_backend", return_value=("native", "gs")), mock.patch.object(
            convert_to_pdfa, "_convert_native", side_effect=fake_ghostscript
        ) as ghostscript, mock.patch.object(convert_to_pdfa, "_ghostscript_parse"):
            source = Path(temp_dir) / "source.pdf"
            make_vector_pdf(source)
            verification = self._convert(source, Path(temp_dir) / "out.pdf", "auto")
        ghostscript.assert_called_once()
        self.assertEqual(verification.backend, "ghostscript (native)")
        self.assertIn("fell back to Ghostscript", verification.notes[0])
        self.assertIn("simulated violation", verification.notes[0])

    def test_pikepdf_backend_fails_loudly_instead_of_falling_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            pikepdf.pdfa, "validate_written", return_value=self._violation_report()
        ), mock.patch.object(convert_to_pdfa, "_select_backend", side_effect=AssertionError("Ghostscript was used")):
            source = Path(temp_dir) / "source.pdf"
            output = Path(temp_dir) / "out.pdf"
            make_vector_pdf(source)
            with self.assertRaisesRegex(convert_to_pdfa.PdfaError, "simulated violation"):
                self._convert(source, output, "pikepdf")
            self.assertFalse(output.exists())

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
