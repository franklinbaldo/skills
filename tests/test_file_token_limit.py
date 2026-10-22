"""Black-box tests for the changed-files-only size gate."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECKER = Path(__file__).resolve().parents[1] / "scripts/check_file_token_limit.py"

class FileSizePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.put("legacy.md", "x" * 21000)
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.base = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, text=True, capture_output=True, check=True)

    def put(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def check(self):
        env = dict(os.environ, CI="true", TOKEN_LIMIT_BASE_SHA=self.base)
        return subprocess.run([sys.executable, str(CHECKER)], cwd=self.root, env=env, text=True, capture_output=True)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "change")

    def test_untouched_legacy_file_is_ignored(self):
        self.put("new.md", "short")
        self.commit()
        self.assertEqual(self.check().returncode, 0)

    def test_modified_legacy_file_must_be_reorganized(self):
        self.put("legacy.md", "y" * 20500)
        self.commit()
        self.assertNotEqual(self.check().returncode, 0)
        self.assertIn("semantic", self.check().stdout.lower())

    def test_new_oversized_file_fails(self):
        self.put("new.md", "x" * 20001)
        self.commit()
        self.assertNotEqual(self.check().returncode, 0)

    def test_new_file_at_limit_passes(self):
        self.put("new.md", "x" * 20000)
        self.commit()
        self.assertEqual(self.check().returncode, 0)

if __name__ == "__main__":
    unittest.main()
