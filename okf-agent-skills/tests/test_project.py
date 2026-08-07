from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project  # noqa: E402


class UnifiedProjectionTests(unittest.TestCase):
    def test_projects_all_layers_and_rfc0006_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            output = Path(tmp) / "projection"
            (root / "alpha" / "evals").mkdir(parents=True)
            (root / "beta").mkdir(parents=True)
            (root / "alpha" / "SKILL.md").write_text(
                "---\nname: alpha\n---\n\nUse [beta](../beta/SKILL.md).\n",
                encoding="utf-8",
            )
            (root / "beta" / "SKILL.md").write_text(
                "---\nname: beta\n---\n\nCompanion: alpha.\n",
                encoding="utf-8",
            )
            (root / "alpha" / "evals" / "eval_queries.json").write_text(
                json.dumps([{"query": "Use alpha", "should_trigger": True}]),
                encoding="utf-8",
            )

            counts = project.project(root, output)

            self.assertEqual(counts["skills"], 2)
            self.assertEqual(counts["relations"], 1)
            self.assertEqual(counts["resolved_relations"], 1)
            self.assertEqual(counts["evals"], 1)
            self.assertEqual(counts["routing_runs"], 5)
            self.assertEqual(counts["observed_routing_runs"], 0)
            self.assertGreaterEqual(counts["mentions"], 2)
            self.assertEqual(counts["declared_types"], 7)

            self.assertTrue((output / "skills" / "alpha.md").is_file())
            self.assertTrue((output / "evals" / "alpha--trigger--001.md").is_file())
            self.assertTrue((output / "routing-runs" / "alpha--case-001--run-01.md").is_file())
            self.assertTrue((output / "mentions").is_dir())

            contract_dir = output / ".okf" / "contracts"
            expected = {
                "agentskillsprojection.schema.sql",
                "skill.schema.sql",
                "skillresource.schema.sql",
                "skillrelation.schema.sql",
                "skilleval.schema.sql",
                "skillmention.schema.sql",
                "skillroutingrun.schema.sql",
            }
            self.assertEqual({path.name for path in contract_dir.glob("*.sql")}, expected)
            self.assertIn(
                'CREATE TABLE "SkillEval"',
                (contract_dir / "skilleval.schema.sql").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "should_trigger BOOLEAN",
                (contract_dir / "skilleval.schema.sql").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "observed_trigger BOOLEAN",
                (contract_dir / "skillroutingrun.schema.sql").read_text(encoding="utf-8"),
            )

    def test_slug_matches_okf_parser_camelcase_behavior(self) -> None:
        self.assertEqual(project._slug("SkillEval"), "skilleval")
        self.assertEqual(project._slug("SkillRoutingRun"), "skillroutingrun")
        self.assertEqual(project._slug("AgentSkillsProjection"), "agentskillsprojection")
        self.assertEqual(project._slug("Revisão Ciência"), "revisao-ciencia")

    def test_spec_template_matches_contract_location(self) -> None:
        self.assertEqual(project.SPEC_TEMPLATE, ".okf/contracts/{slug}.md")


if __name__ == "__main__":
    unittest.main()
