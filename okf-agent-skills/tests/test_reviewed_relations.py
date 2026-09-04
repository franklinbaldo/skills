#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
# ]
# ///
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project  # noqa: E402


class ReviewedRelationTests(unittest.TestCase):
    def test_reviewed_mention_becomes_relation_and_derived_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            output = Path(tmp) / "projection"
            (root / "alpha").mkdir(parents=True)
            (root / "beta").mkdir(parents=True)
            (root / ".okf").mkdir(parents=True)
            (root / "alpha" / "SKILL.md").write_text(
                "---\nname: alpha\n---\n\nDelegate this branch to beta.\n",
                encoding="utf-8",
            )
            (root / "beta" / "SKILL.md").write_text(
                "---\nname: beta\n---\n\nBeta workflow.\n",
                encoding="utf-8",
            )
            (root / ".okf" / "agent-skills-reviewed-relations.json").write_text(
                json.dumps([
                    {
                        "source_skill": "alpha",
                        "target_skill": "beta",
                        "reason": "reviewed delegation",
                    }
                ]),
                encoding="utf-8",
            )

            counts = project.project(root, output)

            self.assertEqual(counts["authored_relations"], 0)
            self.assertEqual(counts["reviewed_relations"], 1)
            self.assertEqual(counts["relations"], 1)
            relation = (output / "relations" / "reviewed--0001.md").read_text(encoding="utf-8")
            self.assertIn('evidence_kind: "reviewed_mention"', relation)
            self.assertIn('review_reason: "reviewed delegation"', relation)
            alpha = (output / "skills" / "alpha.md").read_text(encoding="utf-8")
            self.assertIn("## Reviewed relations", alpha)
            self.assertIn("[beta](beta.md)", alpha)

    def test_stale_reviewed_relation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            output = Path(tmp) / "projection"
            (root / "alpha").mkdir(parents=True)
            (root / "beta").mkdir(parents=True)
            (root / ".okf").mkdir(parents=True)
            (root / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
            (root / "beta" / "SKILL.md").write_text("---\nname: beta\n---\n", encoding="utf-8")
            (root / ".okf" / "agent-skills-reviewed-relations.json").write_text(
                json.dumps([
                    {
                        "source_skill": "alpha",
                        "target_skill": "beta",
                        "reason": "stale relation",
                    }
                ]),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "no current mention evidence"):
                project.project(root, output)


if __name__ == "__main__":
    unittest.main()
