#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=8.4",
#   "sqlglot>=27,<29",
# ]
# ///
"""Tests for corpus-scale DuckDB SQL -> MBQL conformance."""
# ruff: noqa: E402, I001

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import corpus_runner


def test_corpus_reports_supported_ambiguous_and_unsupported(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.sql"
    corpus.write_text(
        "SELECT id FROM orders WHERE total > 10;\n"
        "SELECT id FROM orders ORDER BY id LIMIT 10 OFFSET 20;\n"
        "SELECT id FROM orders ORDER BY id LIMIT 10 OFFSET 5;\n"
        "SELECT DISTINCT status FROM orders;\n"
        "WITH x AS (SELECT id FROM orders) SELECT * FROM x;\n",
        encoding="utf-8",
    )

    payload = corpus_runner.run_corpus(corpus, database="Analytics")

    assert payload["statements"] == 5
    assert payload["counts"]["supported"] == 3
    assert payload["counts"]["ambiguous"] == 1
    assert payload["counts"]["unsupported"] == 1
    assert payload["contract_gaps"] == 0


def test_supported_matrix_drift_is_a_contract_gap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = tmp_path / "corpus.sql"
    corpus.write_text("SELECT id FROM orders;", encoding="utf-8")

    def broken_converter(*args, **kwargs):
        raise corpus_runner.ConversionError("regression")

    monkeypatch.setattr(corpus_runner, "convert_sql", broken_converter)
    payload = corpus_runner.run_corpus(corpus, database="Analytics")

    assert payload["counts"] == {"contract_gap": 1}
    assert payload["contract_gaps"] == 1
    assert payload["results"][0]["error"] == "regression"


def test_classifier_drift_is_a_classification_gap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = tmp_path / "corpus.sql"
    corpus.write_text("SELECT id FROM orders;", encoding="utf-8")

    monkeypatch.setattr(
        corpus_runner,
        "_effective_status",
        lambda sql: (corpus_runner.Status.AMBIGUOUS, ("pretend_ambiguous",)),
    )
    payload = corpus_runner.run_corpus(corpus, database="Analytics")

    assert payload["counts"] == {"classification_gap": 1}
    assert payload["classification_gaps"] == 1
    assert payload["contract_gaps"] == 0
    assert payload["results"][0]["converted"] is True


def test_directory_corpus_is_recursive(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "one.sql").write_text("SELECT id FROM orders;", encoding="utf-8")
    (tmp_path / "b" / "two.sql").write_text("SELECT count(*) FROM orders;", encoding="utf-8")

    payload = corpus_runner.run_corpus(tmp_path, database="Analytics")

    assert payload["statements"] == 2
    assert payload["contract_gaps"] == 0


def test_sqllogictest_extracts_query_blocks_and_ignores_setup(tmp_path: Path) -> None:
    corpus = tmp_path / "sample.test"
    corpus.write_text(
        "statement ok\n"
        "CREATE TABLE orders(id INTEGER, status VARCHAR);\n\n"
        "query I rowsort\n"
        "SELECT id FROM orders ORDER BY id LIMIT 10 OFFSET 20;\n"
        "----\n"
        "1\n\n"
        "query I rowsort\n"
        "SELECT DISTINCT status FROM orders;\n"
        "----\n"
        "paid\n",
        encoding="utf-8",
    )

    payload = corpus_runner.run_corpus(corpus, database="Analytics")

    assert payload["statements"] == 2
    assert payload["counts"] == {"supported": 2}
    assert all("CREATE TABLE" not in row["sql"] for row in payload["results"])
    assert payload["feature_counts"]["offset_aligned"] == 1
    assert payload["feature_counts"]["select_distinct_simple"] == 1


def test_sqllogictest_pivot_query_is_visible_as_unsupported(tmp_path: Path) -> None:
    corpus = tmp_path / "pivot.test"
    corpus.write_text(
        "query III rowsort\n"
        "PIVOT Cities ON Year IN (2000, 2010) USING SUM(Population);\n"
        "----\n"
        "NL\\tAmsterdam\\t1005\n",
        encoding="utf-8",
    )

    payload = corpus_runner.run_corpus(corpus, database="Analytics")

    assert payload["statements"] == 1
    assert payload["counts"] == {"unsupported": 1}
    assert payload["feature_counts"]["pivot"] == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
