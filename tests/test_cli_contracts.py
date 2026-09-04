#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
# ]
# ///
"""Contract tests for the repository's Cyclopts CLIs.

Each migrated script exposes a `cyclopts.App` named `app`. These tests exercise
the CLI surface itself — help text, required arguments, defaults, type errors
and exit codes — without touching the network or the filesystem.

Scripts whose imports need heavy third-party packages (PyMuPDF, mdformat,
torch, fastmcp) are skipped when those packages are absent; the CLI surface of
the stdlib-only scripts is always checked.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# module name -> directory holding it
CLI_MODULES = {
    "datajud": "datajud/scripts",
    "juris": "juris-tjro/scripts",
    "opf_annotate": "opf-finetune/scripts",
    "anonimizar": "anonimizacao-documentos/scripts",
    "create_kaggle_job": "free-gpu/scripts",
    "lean_docgen_md": "scripts",
    "axiom_graph": "scripts",
    "project_agent_skills": "okf-agent-skills/scripts",
    "project_skill_evals": "okf-agent-skills/scripts",
    "project_skill_mentions": "okf-agent-skills/scripts",
}


def load(module_name: str):
    directory = str(REPO_ROOT / CLI_MODULES[module_name])
    if directory not in sys.path:
        sys.path.insert(0, directory)
    return importlib.import_module(module_name)


def run_app(app, tokens: list[str]) -> tuple[int, str]:
    """Invoke a Cyclopts app, returning (exit code, captured output)."""
    stream = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        try:
            result = app(tokens)
            code = result if isinstance(result, int) else 0
        except SystemExit as exit_error:  # --help and parse errors
            code = exit_error.code if isinstance(exit_error.code, int) else 1
    return code, stream.getvalue()


class HelpContractTests(unittest.TestCase):
    def test_every_cli_has_help_and_exits_zero(self) -> None:
        for module_name in CLI_MODULES:
            with self.subTest(module=module_name):
                module = load(module_name)
                code, output = run_app(module.app, ["--help"])
                self.assertEqual(code, 0)
                self.assertIn("Usage:", output)

    def test_subcommands_have_their_own_help(self) -> None:
        for module_name, command in (
            ("datajud", "buscar"),
            ("juris", "buscar"),
            ("opf_annotate", "validate"),
        ):
            with self.subTest(module=module_name, command=command):
                module = load(module_name)
                code, output = run_app(module.app, [command, "--help"])
                self.assertEqual(code, 0)
                self.assertIn(command, output)


class ArgumentContractTests(unittest.TestCase):
    def test_missing_required_argument_fails(self) -> None:
        for module_name, tokens in (
            ("datajud", ["processo"]),
            ("opf_annotate", ["validate"]),
            ("create_kaggle_job", []),
            ("anonimizar", []),
        ):
            with self.subTest(module=module_name):
                module = load(module_name)
                code, _ = run_app(module.app, tokens)
                self.assertNotEqual(code, 0)

    def test_type_error_is_rejected(self) -> None:
        module = load("datajud")
        code, output = run_app(module.app, ["buscar", "--tamanho", "abc"])
        self.assertNotEqual(code, 0)
        self.assertIn("--tamanho", output)

    def test_unknown_command_is_rejected(self) -> None:
        module = load("datajud")
        code, _ = run_app(module.app, ["nao-existe"])
        self.assertNotEqual(code, 0)

    def test_invalid_choice_is_rejected(self) -> None:
        module = load("datajud")
        code, _ = run_app(module.app, ["facetas", "--por", "inexistente"])
        self.assertNotEqual(code, 0)

    def test_defaults_are_documented_in_help(self) -> None:
        module = load("datajud")
        _, output = run_app(module.app, ["buscar", "--help"])
        self.assertIn("tjro", output)
        self.assertIn("20", output)


class SourceContractTests(unittest.TestCase):
    """The repository-wide rules the Ruff gate also enforces."""

    def python_sources(self) -> list[Path]:
        return [
            path
            for path in REPO_ROOT.rglob("*.py")
            if ".git" not in path.parts
            and ".venv" not in path.parts
            and path != Path(__file__).resolve()
        ]

    def test_no_argparse_parsers(self) -> None:
        offenders = [
            str(path.relative_to(REPO_ROOT))
            for path in self.python_sources()
            if re.search(r"^import argparse|argparse\.ArgumentParser", path.read_text(encoding="utf-8"), re.M)
        ]
        self.assertEqual(offenders, [])

    def test_sys_argv_only_in_the_third_party_adapter(self) -> None:
        offenders = [
            str(path.relative_to(REPO_ROOT))
            for path in self.python_sources()
            if "sys.argv" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, ["free-gpu/scripts/colab_windows.py"])

    def test_executable_scripts_declare_pep_723_metadata(self) -> None:
        missing = []
        for path in self.python_sources():
            head = path.read_text(encoding="utf-8")[:400]
            if "# /// script" not in head or "requires-python" not in head:
                missing.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(missing, [])

    def test_ruff_gate_passes(self) -> None:
        try:
            result = subprocess.run(
                ["ruff", "check", "."],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            self.skipTest("ruff is not installed")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
