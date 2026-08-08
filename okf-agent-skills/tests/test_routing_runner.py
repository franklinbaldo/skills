from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import routing_runner  # noqa: E402


class RoutingRunnerTests(unittest.TestCase):
    def _row(self) -> dict[str, object]:
        return {
            "skill": "alpha",
            "case_index": 1,
            "repetition": 2,
            "query": "Use alpha",
            "should_trigger": True,
            "source_path": "alpha/evals/eval_queries.json",
        }

    def test_successful_adapter_records_observed_trigger_and_model(self) -> None:
        code = (
            "import json,sys; q=sys.stdin.read(); "
            "print(json.dumps({'observed_trigger': q == 'Use alpha', 'model': 'fake-model'}))"
        )
        result = routing_runner.run_one(
            self._row(), [sys.executable, "-c", code], "fake-runner", 5
        )
        self.assertEqual(result["execution_status"], "observed")
        self.assertTrue(result["observed_trigger"])
        self.assertEqual(result["model"], "fake-model")
        self.assertEqual(result["runner"], "fake-runner")

    def test_nonzero_exit_is_execution_error_not_false_negative(self) -> None:
        code = "import sys; print('boom', file=sys.stderr); raise SystemExit(7)"
        result = routing_runner.run_one(
            self._row(), [sys.executable, "-c", code], "fake-runner", 5
        )
        self.assertEqual(result["execution_status"], "error")
        self.assertEqual(result["error_type"], "process_exit")
        self.assertNotIn("observed_trigger", result)

    def test_invalid_json_is_execution_error(self) -> None:
        result = routing_runner.run_one(
            self._row(), [sys.executable, "-c", "print('not-json')"], "fake-runner", 5
        )
        self.assertEqual(result["execution_status"], "error")
        self.assertEqual(result["error_type"], "invalid_json")
        self.assertNotIn("observed_trigger", result)

    def test_select_runs_can_address_one_repetition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "alpha" / "evals").mkdir(parents=True)
            (root / "alpha" / "SKILL.md").write_text(
                "---\nname: alpha\n---\n", encoding="utf-8"
            )
            (root / "alpha" / "evals" / "eval_queries.json").write_text(
                json.dumps([{"query": "Use alpha", "should_trigger": True}]),
                encoding="utf-8",
            )
            rows = routing_runner.select_runs(
                root, 5, skill="alpha", case_index=1, repetition=3
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["repetition"], 3)


if __name__ == "__main__":
    unittest.main()
