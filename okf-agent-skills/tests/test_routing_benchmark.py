from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "routing_benchmark.py"
SPEC = importlib.util.spec_from_file_location("routing_benchmark", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RoutingBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.root.mkdir()
        skill = self.root / "alpha"
        (skill / "evals").mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
        (skill / "evals" / "eval_queries.json").write_text(
            json.dumps(
                [
                    {"query": "Use alpha for this", "should_trigger": True},
                    {"query": "Do something adjacent", "should_trigger": False},
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_manifest_repeats_each_case_deterministically(self) -> None:
        rows = MODULE.make_manifest(self.root, 3)
        self.assertEqual(len(rows), 6)
        self.assertEqual([row["repetition"] for row in rows[:3]], [1, 2, 3])
        self.assertTrue(rows[0]["should_trigger"])
        self.assertFalse(rows[3]["should_trigger"])
        self.assertIsNone(rows[0]["observed_trigger"])

    def test_aggregate_reports_trigger_rates_and_confusion_matrix(self) -> None:
        rows = [
            {"skill": "alpha", "case_index": 1, "should_trigger": True, "observed_trigger": True},
            {"skill": "alpha", "case_index": 1, "should_trigger": True, "observed_trigger": True},
            {"skill": "alpha", "case_index": 1, "should_trigger": True, "observed_trigger": False},
            {"skill": "alpha", "case_index": 2, "should_trigger": False, "observed_trigger": False},
            {"skill": "alpha", "case_index": 2, "should_trigger": False, "observed_trigger": False},
            {"skill": "alpha", "case_index": 2, "should_trigger": False, "observed_trigger": True},
        ]
        result = MODULE.aggregate(rows)
        self.assertEqual(result["summary"]["true_positive"], 1)
        self.assertEqual(result["summary"]["true_negative"], 1)
        self.assertEqual(result["summary"]["failed_runs"], 0)
        self.assertEqual(result["cases"][0]["trigger_rate"], 0.6667)
        self.assertEqual(result["cases"][1]["trigger_rate"], 0.3333)

    def test_aggregate_does_not_turn_runner_failure_into_false_negative(self) -> None:
        rows = [
            {
                "skill": "alpha",
                "case_index": 1,
                "should_trigger": True,
                "execution_status": "error",
                "error_type": "timeout",
            }
        ]
        result = MODULE.aggregate(rows)
        self.assertEqual(result["summary"]["failed_runs"], 1)
        self.assertEqual(result["summary"]["classified_cases"], 0)
        self.assertEqual(result["summary"]["false_negative"], 0)
        self.assertIsNone(result["cases"][0]["outcome"])

    def test_loads_error_observation_without_trigger_boolean(self) -> None:
        path = Path(self.tempdir.name) / "observations.jsonl"
        path.write_text(
            json.dumps(
                {
                    "skill": "alpha",
                    "case_index": 1,
                    "repetition": 1,
                    "should_trigger": True,
                    "execution_status": "error",
                    "error_type": "timeout",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        rows = MODULE.load_observations(path)
        self.assertEqual(rows[0]["execution_status"], "error")
        self.assertNotIn("observed_trigger", rows[0])

    def test_rejects_missing_observation_for_success(self) -> None:
        path = Path(self.tempdir.name) / "observations.jsonl"
        path.write_text(
            json.dumps({"skill": "alpha", "case_index": 1, "should_trigger": True}) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            MODULE.load_observations(path)

    def test_repetitions_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.make_manifest(self.root, 0)


if __name__ == "__main__":
    unittest.main()
