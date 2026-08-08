from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import benchmark_rnd  # noqa: E402


class BenchmarkRndTests(unittest.TestCase):
    def _write(self, root: Path, name: str, value: object) -> Path:
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_challenge_summary_counts_balance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                Path(tmp),
                "challenge.json",
                [
                    {"id": "p", "target_skill": "alpha", "query": "do alpha", "should_trigger": True, "tags": ["positive"]},
                    {"id": "n", "target_skill": "alpha", "query": "not alpha", "should_trigger": False, "tags": ["hard-negative"]},
                ],
            )
            self.assertEqual(
                benchmark_rnd.validate_challenge(path),
                {"cases": 2, "positives": 1, "negatives": 1},
            )

    def test_catalog_expands_variants_without_model_logic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                Path(tmp),
                "catalog.json",
                [
                    {
                        "id": "c1",
                        "query": "review it",
                        "target_skill": "review",
                        "catalogs": [["review"], ["review", "other"]],
                    }
                ],
            )
            rows = benchmark_rnd.expand_catalog(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["catalog_size"], 1)
            self.assertEqual(rows[1]["catalog_size"], 2)
            self.assertEqual(rows[1]["target_skill"], "review")

    def test_catalog_rejects_variant_that_omits_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                Path(tmp),
                "catalog.json",
                [{"id": "c1", "query": "x", "target_skill": "alpha", "catalogs": [["beta"]]}],
            )
            with self.assertRaisesRegex(ValueError, "omits target skill"):
                benchmark_rnd.expand_catalog(path)

    def test_mutations_require_detection_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                Path(tmp),
                "mutations.json",
                [{"id": "m1", "skill": "alpha", "mutation": "broaden_domain", "expected_detection_tags": []}],
            )
            with self.assertRaisesRegex(ValueError, "expected_detection_tags"):
                benchmark_rnd.validate_mutations(path)

    def test_multiturn_expands_history_per_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                Path(tmp),
                "multiturn.json",
                [
                    {
                        "id": "mt1",
                        "turns": ["first", "second"],
                        "expected_skill_by_turn": ["alpha", "beta"],
                        "tags": ["handoff"],
                    }
                ],
            )
            rows = benchmark_rnd.expand_multiturn(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["history"], ["first"])
            self.assertEqual(rows[1]["history"], ["first", "second"])
            self.assertEqual(rows[1]["expected_skill"], "beta")

    def test_multiturn_allows_explicit_no_skill_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                Path(tmp),
                "multiturn.json",
                [
                    {
                        "id": "mt1",
                        "turns": ["one-off edit", "now build a loop"],
                        "expected_skill_by_turn": [None, "loop-engineering"],
                        "tags": ["late-trigger"],
                    }
                ],
            )
            rows = benchmark_rnd.expand_multiturn(path)
            self.assertIsNone(rows[0]["expected_skill"])
            self.assertEqual(rows[1]["expected_skill"], "loop-engineering")


if __name__ == "__main__":
    unittest.main()
