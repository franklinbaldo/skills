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

SCRIPT = Path(__file__).parents[1] / "scripts" / "project_agent_skills.py"
SPEC = importlib.util.spec_from_file_location("project_agent_skills", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProjectAgentSkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.output = Path(self.tempdir.name) / "projection"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_discovers_skills_and_rewrites_skill_links(self) -> None:
        self.write(
            "a/SKILL.md",
            "---\nname: a\ndescription: A\n---\n\nUse [B](../b/SKILL.md).\n",
        )
        self.write("b/SKILL.md", "---\nname: b\ndescription: B\n---\n")

        skills, relations = MODULE.project(self.root, self.output)

        self.assertEqual([skill.name for skill in skills], ["a", "b"])
        resolved = [relation for relation in relations if relation.resolved]
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].source_link_target, "../b/SKILL.md")
        self.assertEqual(resolved[0].derived_target, "skills/b.md")
        self.assertEqual(resolved[0].target_kind, "skill")

        derived_a = (self.output / "skills" / "a.md").read_text(encoding="utf-8")
        self.assertIn("[b](b.md)", derived_a)
        self.assertNotIn("../b/SKILL.md", derived_a)

    def test_rewrites_links_to_projected_resources(self) -> None:
        self.write(
            "a/SKILL.md",
            "---\nname: a\n---\n\nRead [details](references/details.md).\n",
        )
        self.write("a/references/details.md", "details\n")

        _, relations = MODULE.project(self.root, self.output)

        self.assertEqual(len(relations), 1)
        relation = relations[0]
        self.assertTrue(relation.resolved)
        self.assertEqual(relation.target_kind, "resource")
        self.assertTrue(relation.derived_target.startswith("resources/a--"))

        derived_a = (self.output / "skills" / "a.md").read_text(encoding="utf-8")
        self.assertIn("[details.md](../resources/a--0001.md)", derived_a)

    def test_relation_provenance_is_emitted_separately(self) -> None:
        self.write(
            "a/SKILL.md",
            "---\nname: a\n---\n\nFirst line.\nUse [B](../b/SKILL.md).\n",
        )
        self.write("b/SKILL.md", "---\nname: b\n---\n")

        MODULE.project(self.root, self.output)

        relation_files = sorted((self.output / "relations").glob("*.md"))
        self.assertEqual(len(relation_files), 1)
        relation = relation_files[0].read_text(encoding="utf-8")
        self.assertIn('source_path: "a/SKILL.md"', relation)
        self.assertIn('source_link_target: "../b/SKILL.md"', relation)
        self.assertIn("source_line: 6", relation)
        self.assertIn('derived_source: "skills/a.md"', relation)
        self.assertIn('derived_target: "skills/b.md"', relation)
        self.assertIn('target_kind: "skill"', relation)
        self.assertIn("resolved: true", relation)

    def test_source_scripts_are_never_executed(self) -> None:
        self.write("a/SKILL.md", "---\nname: a\n---\n")
        marker = self.root / "executed.txt"
        self.write(
            "a/scripts/danger.py",
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
        )

        MODULE.project(self.root, self.output)

        self.assertFalse(marker.exists())
        resources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((self.output / "resources").glob("*.md"))
        )
        self.assertIn('kind: "script"', resources)
        self.assertIn('source_path: "a/scripts/danger.py"', resources)

    def test_projection_is_deterministic(self) -> None:
        self.write(
            "z/SKILL.md",
            "---\nname: z\n---\n\nUse [A](../a/SKILL.md).\n",
        )
        self.write("a/SKILL.md", "---\nname: a\n---\n")
        self.write("a/references/note.md", "reference\n")

        MODULE.project(self.root, self.output)
        first = {
            path.relative_to(self.output).as_posix(): path.read_bytes()
            for path in sorted(self.output.rglob("*"))
            if path.is_file()
        }
        MODULE.project(self.root, self.output)
        second = {
            path.relative_to(self.output).as_posix(): path.read_bytes()
            for path in sorted(self.output.rglob("*"))
            if path.is_file()
        }

        self.assertEqual(first, second)

    def test_output_inside_source_is_not_reingested(self) -> None:
        self.write("a/SKILL.md", "---\nname: a\n---\n")
        nested_output = self.root / ".okf" / "agent-skills"

        MODULE.project(self.root, nested_output)
        skills, _ = MODULE.project(self.root, nested_output)

        self.assertEqual([skill.name for skill in skills], ["a"])


if __name__ == "__main__":
    unittest.main()
