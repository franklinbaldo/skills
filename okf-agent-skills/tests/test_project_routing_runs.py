from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project_routing_runs  # noqa: E402


class RoutingRunProjectionTests(unittest.TestCase):
    def _repo(self, root: Path) -> None:
        (root / "alpha" / "evals").mkdir(parents=True)
        (root / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
        (root / "alpha" / "evals" / "eval_queries.json").write_text(
            json.dumps([{"query": "Use alpha", "should_trigger": True}]), encoding="utf-8"
        )

    def test_merges_observation_into_planned_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            output = Path(tmp) / "out"
            self._repo(root)
            (root / ".okf").mkdir()
            (root / ".okf" / "agent-skills-routing-observations.jsonl").write_text(
                json.dumps(
                    {
                        "skill": "alpha",
                        "case_index": 1,
                        "repetition": 1,
                        "query": "Use alpha",
                        "should_trigger": True,
                        "execution_status": "observed",
                        "observed_trigger": False,
                        "runner": "skill-creator",
                        "model": "example-model",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            rows = project_routing_runs.project(root, output, repetitions=2)
            self.assertEqual(len(rows), 2)
            self.assertFalse(rows[0]["observed_trigger"])
            self.assertEqual(rows[0]["execution_status"], "observed")
            self.assertIsNone(rows[1]["observed_trigger"])
            self.assertIsNone(rows[1]["execution_status"])
            text = (output / "routing-runs" / "alpha--case-001--run-01.md").read_text(encoding="utf-8")
            self.assertIn("observed_trigger: false", text)
            self.assertIn('execution_status: "observed"', text)
            self.assertIn('runner: "skill-creator"', text)

    def test_projects_execution_error_without_observed_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            output = Path(tmp) / "out"
            self._repo(root)
            (root / ".okf").mkdir()
            (root / ".okf" / "agent-skills-routing-observations.jsonl").write_text(
                json.dumps(
                    {
                        "skill": "alpha",
                        "case_index": 1,
                        "repetition": 1,
                        "should_trigger": True,
                        "execution_status": "error",
                        "runner": "fake-runner",
                        "error_type": "timeout",
                        "error_message": "runner timed out",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            rows = project_routing_runs.project(root, output, repetitions=1)
            self.assertIsNone(rows[0]["observed_trigger"])
            self.assertEqual(rows[0]["execution_status"], "error")
            text = (output / "routing-runs" / "alpha--case-001--run-01.md").read_text(encoding="utf-8")
            self.assertNotIn("observed_trigger:", text)
            self.assertIn('execution_status: "error"', text)
            self.assertIn('error_type: "timeout"', text)

    def test_rejects_observation_for_stale_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            output = Path(tmp) / "out"
            self._repo(root)
            (root / ".okf").mkdir()
            (root / ".okf" / "agent-skills-routing-observations.jsonl").write_text(
                json.dumps(
                    {
                        "skill": "alpha",
                        "case_index": 99,
                        "repetition": 1,
                        "should_trigger": True,
                        "observed_trigger": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "do not match current routing manifest"):
                project_routing_runs.project(root, output, repetitions=2)


if __name__ == "__main__":
    unittest.main()
