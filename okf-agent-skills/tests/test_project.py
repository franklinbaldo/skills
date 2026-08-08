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
    def test_projects_static_layers_and_rfc0006_contracts(self) -> None:
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
            self.assertEqual(counts["planned_routing_runs"], 5)
            self.assertEqual(counts["challenge_cases"], 0)
            self.assertEqual(counts["benchmark_mutations"], 0)
            self.assertEqual(counts["catalog_scenarios"], 0)
            self.assertEqual(counts["catalog_variants"], 0)
            self.assertGreaterEqual(counts["mentions"], 2)
            self.assertEqual(counts["declared_types"], 10)

            self.assertTrue((output / "skills" / "alpha.md").is_file())
            self.assertTrue((output / "evals" / "alpha--trigger--001.md").is_file())
            self.assertFalse((output / "routing-runs").exists())
            self.assertTrue((output / "mentions").is_dir())
            self.assertTrue((output / "benchmark-rnd").is_dir())

            manifest = (output / "projection.md").read_text(encoding="utf-8")
            self.assertIn("routing_repetitions: 5", manifest)
            self.assertIn("planned_routing_run_count: 5", manifest)
            self.assertIn("challenge_case_count: 0", manifest)

            contract_dir = output / ".okf" / "contracts"
            expected = {
                "agentskillsprojection.schema.sql",
                "skill.schema.sql",
                "skillresource.schema.sql",
                "skillrelation.schema.sql",
                "skilleval.schema.sql",
                "skillchallengecase.schema.sql",
                "skillbenchmarkmutation.schema.sql",
                "skillcatalogscenario.schema.sql",
                "skillmention.schema.sql",
                "skillroutingobservation.schema.sql",
            }
            self.assertEqual({path.name for path in contract_dir.glob("*.sql")}, expected)
            observation_contract = (
                contract_dir / "skillroutingobservation.schema.sql"
            ).read_text(encoding="utf-8")
            self.assertIn('CREATE TABLE "SkillRoutingObservation"', observation_contract)
            self.assertIn("observed_trigger BOOLEAN", observation_contract)
            self.assertIn("error VARCHAR", observation_contract)

    def test_projects_benchmark_rnd_fixtures_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            output = Path(tmp) / "projection"
            (root / "alpha").mkdir(parents=True)
            (root / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
            rnd = root / "okf-agent-skills" / "evals"
            rnd.mkdir(parents=True)
            (rnd / "challenge-frontier-0001.json").write_text(
                json.dumps([
                    {"id": "c1", "target_skill": "alpha", "query": "x", "should_trigger": True, "tags": ["held-out"]}
                ]),
                encoding="utf-8",
            )
            (rnd / "description-mutations-0001.json").write_text(
                json.dumps([
                    {"id": "m1", "skill": "alpha", "mutation": "broaden_domain", "description": "broaden", "expected_detection_tags": ["held-out"]}
                ]),
                encoding="utf-8",
            )
            (rnd / "catalog-perturbation-0001.json").write_text(
                json.dumps([
                    {"id": "s1", "target_skill": "alpha", "query": "x", "catalogs": [["alpha"], ["alpha", "beta"]]}
                ]),
                encoding="utf-8",
            )

            counts = project.project(root, output)

            self.assertEqual(counts["challenge_cases"], 1)
            self.assertEqual(counts["benchmark_mutations"], 1)
            self.assertEqual(counts["catalog_scenarios"], 1)
            self.assertEqual(counts["catalog_variants"], 2)
            self.assertTrue((output / "benchmark-rnd" / "challenge--c1.md").is_file())
            self.assertTrue((output / "benchmark-rnd" / "mutation--m1.md").is_file())
            self.assertTrue((output / "benchmark-rnd" / "catalog--s1.md").is_file())

    def test_slug_matches_okf_parser_camelcase_behavior(self) -> None:
        self.assertEqual(project._slug("SkillEval"), "skilleval")
        self.assertEqual(project._slug("SkillRoutingObservation"), "skillroutingobservation")
        self.assertEqual(project._slug("AgentSkillsProjection"), "agentskillsprojection")
        self.assertEqual(project._slug("Revisão Ciência"), "revisao-ciencia")

    def test_spec_template_matches_contract_location(self) -> None:
        self.assertEqual(project.SPEC_TEMPLATE, ".okf/contracts/{slug}.md")


if __name__ == "__main__":
    unittest.main()
