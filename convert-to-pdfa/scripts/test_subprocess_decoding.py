#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "pymupdf",
# ]
# ///
"""Regression for #93: subprocess diagnostics may contain non-UTF-8 bytes."""

from __future__ import annotations

import sys
import unittest

import convert_to_pdfa


class SubprocessDecodingTests(unittest.TestCase):
    def test_run_preserves_diagnostics_when_child_emits_invalid_utf8(self) -> None:
        """Invalid bytes must not abort decoding or hide the child's diagnostics."""
        command = [
            sys.executable,
            "-c",
            "import os; os.write(2, b'before\\xfeafter\\n')",
        ]

        result = convert_to_pdfa._run(command)

        self.assertEqual(result.returncode, 0)
        self.assertIn("before", result.stderr)
        self.assertIn("after", result.stderr)


if __name__ == "__main__":
    unittest.main()
