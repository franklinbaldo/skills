from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "project_skill_evals.py"
SPEC = importlib.util.spec_from_file_location("project_skill_evals", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProjectSkillEvalsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.output = Path(self.tempdir.name) / "projection"
        self.root.mkdir()
        self.output.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_skill(self, name: str, cases: list[dict[str, object]]) -> None:
        skill = self.root / name
        (skill / "evals").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: test\n---\n", encoding="utf-8"
        )
        (skill / "evals" / "eval_queries.json").write_text(
            json.dumps(cases, ensure_ascii=False), encoding="utf-8"
        )

    def test_projects_positive_and_negative_trigger_cases(self) -> None:
        self.write_skill(
            "alpha",
            [
                {"query": "use alpha here", "should_trigger": True},
                {"query": "near miss", "should_trigger": False},
            ],
        )

        cases = MODULE.project(self.root, self.output)

        self.assertEqual(len(cases), 2)
        emitted = sorted((self.output / "evals").glob("*.md"))
        self.assertEqual(len(emitted), 2)
        first = emitted[0].read_text(encoding="utf-8")
        second = emitted[1].read_text(encoding="utf-8")
        self.assertIn("type: SkillEval", first)
        self.assertIn('eval_kind: "trigger"', first)
        self.assertIn("should_trigger: true", first)
        self.assertIn("use alpha here", first)
        self.assertIn("should_trigger: false", second)

    def test_rejects_invalid_case_shape(self) -> None:
        self.write_skill("alpha", [{"query": "missing label"}])
        with self.assertRaises(ValueError):
            MODULE.project(self.root, self.output)

    def test_projection_is_deterministic_and_cleans_stale_files(self) -> None:
        self.write_skill("alpha", [{"query": "hello", "should_trigger": True}])
        MODULE.project(self.root, self.output)
        stale = self.output / "evals" / "stale.md"
        stale.write_text("stale", encoding="utf-8")
        first_case = (self.output / "evals" / "alpha--trigger--001.md").read_bytes()

        MODULE.project(self.root, self.output)

        self.assertFalse(stale.exists())
        self.assertEqual(
            first_case,
            (self.output / "evals" / "alpha--trigger--001.md").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
