#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
# ]
# ///
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "project_skill_mentions.py"
SPEC = importlib.util.spec_from_file_location("project_skill_mentions", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProjectSkillMentionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.output = Path(self.tempdir.name) / "projection"
        self.root.mkdir()
        self.output.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_skill(self, name: str, body: str) -> None:
        path = self.root / name / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text(f"---\nname: {name}\ndescription: test\n---\n\n{body}\n", encoding="utf-8")

    def test_projects_known_skill_mentions_without_edges(self) -> None:
        self.write_skill("alpha", "Use beta when the second workflow is needed.")
        self.write_skill("beta", "Standalone.")

        mentions = MODULE.project(self.root, self.output)

        self.assertEqual(len(mentions), 1)
        self.assertEqual(mentions[0]["source_skill"], "alpha")
        self.assertEqual(mentions[0]["target_skill"], "beta")
        emitted = next((self.output / "mentions").glob("*.md")).read_text(encoding="utf-8")
        self.assertIn("type: SkillMention", emitted)
        self.assertIn('relation_strength: "mention"', emitted)
        self.assertNotIn("](", emitted)

    def test_does_not_match_skill_name_as_substring(self) -> None:
        self.write_skill("data", "This is about metadata, not the sibling.")
        self.write_skill("meta", "Standalone.")
        mentions = MODULE.project(self.root, self.output)
        self.assertEqual(mentions, [])

    def test_frontmatter_is_not_scanned(self) -> None:
        alpha = self.root / "alpha" / "SKILL.md"
        alpha.parent.mkdir(parents=True)
        alpha.write_text("---\nname: alpha\ndescription: mentions beta only here\n---\n\nNo companion.\n", encoding="utf-8")
        self.write_skill("beta", "Standalone.")
        mentions = MODULE.project(self.root, self.output)
        self.assertEqual(mentions, [])


if __name__ == "__main__":
    unittest.main()
