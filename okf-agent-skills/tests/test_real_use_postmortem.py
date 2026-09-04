#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
# ]
# ///
from __future__ import annotations

import unittest
from pathlib import Path


class RealUsePostmortemContractTests(unittest.TestCase):
    def test_every_skill_carries_real_use_postmortem_contract(self) -> None:
        root = Path(__file__).resolve().parents[2]
        skill_files = sorted(root.glob("*/SKILL.md"))
        self.assertTrue(skill_files, "expected repository skills")

        missing: list[str] = []
        for path in skill_files:
            text = path.read_text(encoding="utf-8")
            if "## Real-use postmortem" not in text and "## Mandatory postmortem" not in text:
                missing.append(path.relative_to(root).as_posix())

        self.assertEqual(missing, [], f"skills missing real-use postmortem contract: {missing}")


if __name__ == "__main__":
    unittest.main()
