#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pikepdf[pdfa]>=10.17",
# ]
# ///
"""Tests for pikepdf_backend.py, on fixtures built in memory with pikepdf."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pikepdf
import pikepdf.pdfa
import pikepdf_backend


def make_vector_pdf(path: Path, *, creation_date: str | None = None, font: bool = False) -> None:
    """One A4 page with a filled rectangle; optionally text in a non-embedded Helvetica."""
    pdf = pikepdf.new()
    content = b"1 0 0 rg 72 72 200 100 re f"
    resources = pikepdf.Dictionary()
    if font:
        content += b" BT /F1 12 Tf 72 300 Td (Texto) Tj ET"
        resources.Font = pikepdf.Dictionary(
            F1=pdf.make_indirect(
                pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica)
            )
        )
    page = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=[0, 0, 595, 842],
        Contents=pdf.make_stream(content),
        Resources=resources,
    )
    pdf.pages.append(pikepdf.Page(page))
    pdf.docinfo["/Title"] = "Fixture"
    if creation_date:
        pdf.docinfo["/CreationDate"] = creation_date
    pdf.save(path)


def xmp_of(path: Path) -> str:
    with pikepdf.open(path) as pdf:
        return pdf.Root.Metadata.read_bytes().decode("utf-8")


class PikepdfBackendTests(unittest.TestCase):
    def test_pdf_date_keeps_the_offset(self) -> None:
        when = datetime(2026, 10, 30, 9, 5, 7, tzinfo=timezone(timedelta(hours=-4)))
        self.assertEqual(pikepdf_backend.pdf_date(when), "D:20261030090507-04'00'")
        utc = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        self.assertEqual(pikepdf_backend.pdf_date(utc), "D:20260102030405Z")

    def test_promotes_every_part_without_violations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            make_vector_pdf(source)
            for part in pikepdf_backend.SUPPORTED_PARTS:
                with self.subTest(part=part):
                    output = Path(temp_dir) / f"out-{part}b.pdf"
                    result = pikepdf_backend.convert_pikepdf(source, output, part=part)
                    self.assertEqual(result.violations, ())
                    xmp = xmp_of(output)
                    self.assertIn(f"<pdfaid:part>{part}</pdfaid:part>", xmp)
                    self.assertIn("<pdfaid:conformance>B</pdfaid:conformance>", xmp)
                    with pikepdf.open(output) as pdf:
                        self.assertEqual(len(pdf.Root.OutputIntents), 1)

    def test_missing_creation_date_is_filled_and_reaches_the_xmp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            output = Path(temp_dir) / "out.pdf"
            make_vector_pdf(source)
            when = datetime(2026, 10, 29, 22, 0, tzinfo=timezone(timedelta(hours=-4)))
            result = pikepdf_backend.convert_pikepdf(source, output, part=2, creation_date=when)
            self.assertTrue(any("CreationDate and ModDate" in change for change in result.changes))
            xmp = xmp_of(output)
            self.assertIn("<xmp:CreateDate>2026-10-29T22:00:00-04:00</xmp:CreateDate>", xmp)
            self.assertIn("<xmp:ModifyDate>2026-10-29T22:00:00-04:00</xmp:ModifyDate>", xmp)
            with pikepdf.open(output) as pdf:
                # prepare() rewrites the Info date to agree with the XMP; the value is what counts.
                self.assertTrue(str(pdf.docinfo["/CreationDate"]).startswith("D:20261029220000-04'00"))

    def test_existing_creation_date_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            output = Path(temp_dir) / "out.pdf"
            make_vector_pdf(source, creation_date="D:20240105093000Z")
            result = pikepdf_backend.convert_pikepdf(source, output, part=2)
            self.assertFalse(any("CreationDate" in change for change in result.changes))
            self.assertIn("2024-01-05T09:30:00", xmp_of(output))

    def test_non_embedded_font_blocks_although_pikepdf_calls_it_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            make_vector_pdf(source, font=True)
            result = pikepdf_backend.convert_pikepdf(source, Path(temp_dir) / "out.pdf", part=2)
            self.assertEqual(result.violations, ())
            self.assertTrue(any("6.2.11.4" in finding for finding in result.undecided), result)
            self.assertTrue(result.blocking)

    def test_schema_only_findings_do_not_block(self) -> None:
        finding = pikepdf.pdfa.Finding(
            "pikepdf:schema-MarkInfo", "obj 1 0", "unrecognized key(s) /Type are not checked", "unsupported"
        )
        report = pikepdf.pdfa.Report(flavour="2b", findings=[finding])
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            pikepdf.pdfa, "validate_written", return_value=report
        ):
            source = Path(temp_dir) / "source.pdf"
            make_vector_pdf(source)
            result = pikepdf_backend.convert_pikepdf(source, Path(temp_dir) / "out.pdf", part=2)
        self.assertEqual(result.blocking, ())
        self.assertEqual(len(result.unchecked), 1)


if __name__ == "__main__":
    unittest.main()
