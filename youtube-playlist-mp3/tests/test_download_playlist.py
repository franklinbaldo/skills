#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3,<5", "yt-dlp[default]>=2026.10.26", "static-ffmpeg==3.0"]
# ///
"""Offline CLI and failure-propagation tests; no media or credentials needed."""

import importlib.util
import sys
import tempfile
import unittest
from concurrent.futures import Future
from pathlib import Path
from threading import Event
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

    def test_failed_provisioning_keeps_source(self):
        ready = Future()
        ready.set_exception(RuntimeError("offline"))
        with module.YoutubeDL({"quiet": True}) as downloader, tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.webm"
            source.write_bytes(b"original")
            processor = module.DeferredAudioPP(downloader, ready)
            with self.assertRaises(module.PostProcessingError):
                processor.run({"filepath": str(source)})
            self.assertEqual(source.read_bytes(), b"original")

    def test_download_starts_before_ffmpeg_is_ready(self):
        started = Event()

        def prepare():
            if not started.wait(timeout=5):
                raise AssertionError("Media download was blocked by FFmpeg preparation")

        with tempfile.TemporaryDirectory() as folder:
            with (
                patch.object(module, "ensure_ffmpeg", side_effect=prepare),
                patch.object(module, "YoutubeDL") as factory,
            ):
                downloader = factory.return_value.__enter__.return_value
                downloader.download.side_effect = lambda urls: started.set() or 0
                with self.assertRaises(SystemExit) as result:
                    module.app([URL, "--destination", folder])
                self.assertEqual(result.exception.code, 0)
                processor = downloader.add_post_processor.call_args.args[0]
                self.assertIsNone(processor.ready.result())

    def test_download_uses_private_ffmpeg(self):
        with tempfile.TemporaryDirectory() as folder:
            binaries = [Path(folder) / name for name in ("ffmpeg.exe", "ffprobe.exe")]
            for binary in binaries:
                binary.touch()
            with (
                patch.object(module, "which", return_value=None),
                patch.object(module, "get_or_fetch_platform_executables_else_raise", return_value=binaries),
                patch.object(module, "YoutubeDL") as downloader,
            ):
                downloader.return_value.__enter__.return_value.download.return_value = 0
                with self.assertRaises(SystemExit) as result:
                    module.app([URL, "--destination", folder])
                self.assertEqual(result.exception.code, 0)
                instance = downloader.return_value.__enter__.return_value
                processor = instance.add_post_processor.call_args.args[0]
                self.assertEqual(processor.ready.result(), folder)
                with (
                    patch.object(module, "FFmpegExtractAudioPP") as extract,
                    patch.object(module, "FFmpegMetadataPP") as metadata,
                ):
                    extract.return_value.run.return_value = (["source.webm"], {"filepath": "audio.mp3"})
                    metadata.return_value.run.return_value = ([], {"filepath": "audio.mp3"})
                    self.assertEqual(processor.run({})[0], ["source.webm"])
                    instance.params.__setitem__.assert_called_with("ffmpeg_location", folder)

    def test_listing_without_ffmpeg(self):
        with (
            patch.object(module, "ensure_ffmpeg") as prepare,
            patch.object(module, "YoutubeDL") as downloader,
        ):
            downloader.return_value.__enter__.return_value.download.return_value = 0
            with self.assertRaises(SystemExit) as result:
                module.app([URL, "--list-only"])
            self.assertEqual(result.exception.code, 0)
            options = downloader.call_args.args[0]
            self.assertTrue(options["skip_download"])
            self.assertNotIn("postprocessors", options)
            prepare.assert_not_called()

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
