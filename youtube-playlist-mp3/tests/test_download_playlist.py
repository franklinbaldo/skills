#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3,<5", "yt-dlp[default]>=2026.10.26"]
# ///
"""Offline CLI and failure-propagation tests; no media or credentials needed."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "download_playlist.py"
SPEC = importlib.util.spec_from_file_location("playlist_download", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)
URL = "https://www.youtube.com/playlist?list=PLtest"


class DownloadTests(unittest.TestCase):
    def test_help(self):
        with self.assertRaises(SystemExit) as result:
            module.app(["--help"])
        self.assertEqual(result.exception.code, 0)

    def test_invalid_url_never_connects(self):
        with patch.object(module, "YoutubeDL") as downloader:
            for url in ("https://youtube.com.evil.test/?list=x", "http://youtube.com/?list=x", "https://youtube.com/"):
                with self.subTest(url=url), self.assertRaises(SystemExit) as result:
                    module.app([url])
                self.assertEqual(result.exception.code, 2)
            downloader.assert_not_called()

    def test_missing_ffmpeg_never_connects(self):
        with patch.object(module, "which", return_value=None), patch.object(module, "YoutubeDL") as downloader:
            with self.assertRaises(SystemExit) as result:
                module.app([URL])
            self.assertEqual(result.exception.code, 2)
            downloader.assert_not_called()

    def test_listing_without_ffmpeg(self):
        with patch.object(module, "which", return_value=None), patch.object(module, "YoutubeDL") as downloader:
            downloader.return_value.__enter__.return_value.download.return_value = 0
            with self.assertRaises(SystemExit) as result:
                module.app([URL, "--list-only"])
            self.assertEqual(result.exception.code, 0)
            options = downloader.call_args.args[0]
            self.assertTrue(options["skip_download"])
            self.assertNotIn("postprocessors", options)

    def test_partial_failure_is_reported_and_archive_configured(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(module, "which", return_value="tool"), patch.object(module, "YoutubeDL") as downloader:
                downloader.return_value.__enter__.return_value.download.return_value = 1
                with self.assertRaises(SystemExit) as result:
                    module.app([URL, "--destination", folder])
                self.assertEqual(result.exception.code, 1)
                options = downloader.call_args.args[0]
                self.assertEqual(options["download_archive"], str(Path(folder).resolve() / "downloaded.txt"))
                self.assertEqual(options["ignoreerrors"], "only_download")
                self.assertFalse(options["overwrites"])


if __name__ == "__main__":
    unittest.main()
