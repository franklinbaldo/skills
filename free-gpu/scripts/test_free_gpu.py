"""Regression tests for the free GPU helper scripts."""

from __future__ import annotations

import unittest

from colab_windows import requested_command
from create_kaggle_job import (
    KaggleJobError,
    build_metadata,
    validate_owner,
    validate_slug,
)


class FreeGpuTests(unittest.TestCase):
    def test_colab_command_ignores_global_options(self) -> None:
        self.assertEqual(
            requested_command(["--auth", "oauth2", "run", "--gpu", "T4", "job.py"]),
            "run",
        )

    def test_validates_kaggle_slugs(self) -> None:
        self.assertEqual(validate_slug("gpu-job", "slug"), "gpu-job")
        self.assertEqual(validate_owner("User_Name"), "User_Name")
        with self.assertRaises(KaggleJobError):
            validate_slug("GPU Job", "slug")

    def test_kaggle_job_is_private_and_gpu_enabled(self) -> None:
        metadata = build_metadata(
            owner="user",
            slug="gpu-job",
            title="GPU Job",
            code_file="job.py",
            accelerator="NvidiaTeslaT4",
            internet=False,
        )
        self.assertIs(metadata["is_private"], True)
        self.assertIs(metadata["enable_gpu"], True)
        self.assertEqual(metadata["machine_shape"], "NvidiaTeslaT4")


if __name__ == "__main__":
    unittest.main()
