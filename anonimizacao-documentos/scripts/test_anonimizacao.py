"""Regression tests for deterministic and OPF-assisted anonymization helpers."""

from __future__ import annotations

import unittest

from anonimizar import AnonymizationError, anonymize_tagged_text
from anonimizar_opf import Span, deterministic_spans, merge_spans, tag_text


class AnonymizationTests(unittest.TestCase):
    def test_repeated_reference_reuses_marker(self) -> None:
        tagged = (
            "<pii tipo='nome_pessoa' ref='p1'>Ana</pii> viu "
            "<pii tipo='nome_pessoa' ref='p1'>Ana</pii>."
        )
        anonymized, count = anonymize_tagged_text(tagged)
        self.assertEqual(count, 2)
        self.assertEqual(
            anonymized,
            "_NOME_PESSOA_1_ viu _NOME_PESSOA_1_.",
        )

    def test_rejects_nested_and_unbalanced_tags(self) -> None:
        with self.assertRaises(AnonymizationError):
            anonymize_tagged_text(
                "<pii tipo='nome_pessoa' ref='1'>A"
                "<pii tipo='cpf' ref='1'>123</pii></pii>"
            )
        with self.assertRaises(AnonymizationError):
            anonymize_tagged_text("</pii>")

    def test_regex_spans_cover_cpf_and_cnj(self) -> None:
        text = "CPF 123.456.789-00; processo 7005781-78.2017.8.22.0007."
        spans = deterministic_spans(text)
        self.assertEqual(
            [span.pii_type for span in spans], ["cpf", "processo_judicial"]
        )

    def test_regex_wins_over_overlapping_model_span(self) -> None:
        spans = merge_spans(
            [
                Span(0, 14, "cpf", "regex"),
                Span(0, 20, "identificador_conta", "opf"),
            ]
        )
        self.assertEqual(spans, [Span(0, 14, "cpf", "regex")])

    def test_tag_text_reuses_reference_for_equal_values(self) -> None:
        text = "Ana encontrou Ana."
        tagged, counts = tag_text(
            text,
            [
                Span(0, 3, "nome_pessoa", "opf"),
                Span(14, 17, "nome_pessoa", "opf"),
            ],
        )
        self.assertEqual(counts["nome_pessoa"], 2)
        self.assertEqual(
            tagged,
            "<pii tipo='nome_pessoa' ref='1'>Ana</pii> encontrou "
            "<pii tipo='nome_pessoa' ref='1'>Ana</pii>.",
        )


if __name__ == "__main__":
    unittest.main()
