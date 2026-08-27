#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "huggingface-hub",
# ]
# ///
"""Build VibeASR.cpp and transcribe one uploaded audio file in Colab.

The local wrapper uploads /content/vibevoice-job.json and the audio before this
script is sent with ``colab exec -f``. Build and model directories are retained
inside a named session so later jobs can reuse them.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

CONFIG_PATH = Path("/content/vibevoice-job.json")
REPO_DIR = Path("/content/VibeASR.cpp")
BUILD_DIR = REPO_DIR / "build"
MODEL_DIR = Path("/content/vibevoice-models")
WAV_PATH = Path("/content/vibevoice-input.wav")
TRANSCRIPT_PATH = Path("/content/vibevoice-transcript.txt")
METADATA_PATH = Path("/content/vibevoice-metadata.json")
STDERR_PATH = Path("/content/vibevoice-stderr.log")
BUILD_REF_PATH = BUILD_DIR / ".vibeasr-ref"

REPO_URL = "https://github.com/microsoft/VibeASR.cpp.git"
REPO_REF = "da6991219d83dcc5e13be487ab71cc0cdb1bf226"
MODEL_ID = "microsoft/VibeVoice-ASR-BitNet"
VAE_NAME = "vibeasr-vae-encoder-i8_s.gguf"
LM_NAME = "vibeasr-lm-i2_s-embed-q6_k.gguf"


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command, echoing a shell-like representation first."""
    shown = [
        "<redacted-context>"
        if index > 0 and command[index - 1] == "--context"
        else part
        for index, part in enumerate(command)
    ]
    print("+", " ".join(shown), flush=True)
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )


def ensure_system_tools() -> None:
    required = ("git", "cmake", "g++", "ffmpeg", "ffprobe")
    missing = [tool for tool in required if shutil.which(tool) is None]
    if not missing:
        return
    run(["apt-get", "update"])
    run(
        [
            "apt-get",
            "install",
            "-y",
            "git",
            "cmake",
            "build-essential",
            "ffmpeg",
        ]
    )


def ensure_repo() -> None:
    if not (REPO_DIR / ".git").exists():
        run(["git", "clone", "--recursive", REPO_URL, str(REPO_DIR)])
    run(["git", "fetch", "--depth", "1", "origin", REPO_REF], cwd=REPO_DIR)
    run(["git", "checkout", "--detach", REPO_REF], cwd=REPO_DIR)
    run(
        ["git", "submodule", "update", "--init", "--recursive", "--depth", "1"],
        cwd=REPO_DIR,
    )


def ensure_build(build_jobs: int) -> Path:
    executable = BUILD_DIR / "bin" / "asr_infer"
    built_ref = ""
    if BUILD_REF_PATH.exists():
        built_ref = BUILD_REF_PATH.read_text(encoding="utf-8").strip()
    if executable.exists() and built_ref == REPO_REF:
        return executable
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    run(
        [
            "cmake",
            "-S",
            str(REPO_DIR),
            "-B",
            str(BUILD_DIR),
            "-DCMAKE_BUILD_TYPE=Release",
        ]
    )
    run(
        [
            "cmake",
            "--build",
            str(BUILD_DIR),
            "--target",
            "asr_infer",
            "-j",
            str(build_jobs),
        ]
    )
    if not executable.exists():
        raise RuntimeError(f"Build completed without {executable}")
    BUILD_REF_PATH.write_text(REPO_REF + "\n", encoding="utf-8")
    return executable


def ensure_models() -> tuple[Path, Path, str]:
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "huggingface_hub>=0.34,<2",
        ]
    )
    from huggingface_hub import HfApi, snapshot_download

    model_revision = HfApi().model_info(MODEL_ID).sha
    snapshot_download(
        repo_id=MODEL_ID,
        revision=model_revision,
        local_dir=MODEL_DIR,
        allow_patterns=[VAE_NAME, LM_NAME],
    )
    vae = MODEL_DIR / VAE_NAME
    lm = MODEL_DIR / LM_NAME
    for model in (vae, lm):
        if not model.exists():
            raise FileNotFoundError(f"Model download did not produce {model}")
    return vae, lm, model_revision


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        config = json.load(handle)
    audio = Path(config["audio"])
    if not audio.is_file():
        raise FileNotFoundError(f"Uploaded audio not found: {audio}")
    return config


def cpu_description() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def normalize_audio(audio: Path) -> None:
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(audio),
            "-ac",
            "1",
            "-ar",
            "24000",
            "-c:a",
            "pcm_s16le",
            str(WAV_PATH),
        ]
    )


def probe_duration() -> float:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(WAV_PATH),
        ],
        capture=True,
    )
    return float(result.stdout.strip())


def main() -> None:
    started = time.monotonic()
    config = load_config()
    ensure_system_tools()

    cpu_count = os.cpu_count() or 1
    requested_threads = int(config.get("threads", 0))
    threads = requested_threads or min(cpu_count, 8)
    threads = max(1, min(threads, cpu_count))
    build_jobs = max(1, min(cpu_count, 8))

    audio = Path(config["audio"])
    normalize_audio(audio)
    ensure_repo()
    executable = ensure_build(build_jobs)
    vae, lm, model_revision = ensure_models()

    command = [
        str(executable),
        "--vae-model",
        str(vae),
        "--lm-model",
        str(lm),
        "--audio",
        str(WAV_PATH),
        "-t",
        str(threads),
        "--max-tokens",
        str(int(config.get("max_tokens", 16384))),
    ]
    if bool(config.get("greedy", True)):
        command.append("--greedy")
    context = str(config.get("context", "")).strip()
    if context:
        command.extend(["--context", context])

    result = run(command, capture=True)
    transcript = result.stdout.strip()
    audio_duration = probe_duration()
    TRANSCRIPT_PATH.write_text(transcript + "\n", encoding="utf-8")
    STDERR_PATH.write_text(result.stderr, encoding="utf-8")

    metadata = {
        "model_requested": str(config.get("model_requested", "bitnet")),
        "model_effective": "bitnet",
        "fallback_reason": config.get("fallback_reason"),
        "model": MODEL_ID,
        "model_revision": model_revision,
        "runtime_repository": REPO_URL,
        "runtime_revision": REPO_REF,
        "cpu": cpu_description(),
        "cpu_count": cpu_count,
        "threads": threads,
        "source_input_name": str(config.get("source_input_name", audio.name)),
        "uploaded_audio": audio.name,
        "upload_encoding": str(config.get("upload_encoding", "original")),
        "normalized_audio": str(WAV_PATH),
        "audio_duration_seconds": round(audio_duration, 3),
        "context_supplied": bool(context),
        "greedy": bool(config.get("greedy", True)),
        "max_tokens": int(config.get("max_tokens", 16384)),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "command": [
            "<redacted-context>"
            if index > 0 and command[index - 1] == "--context"
            else part
            for index, part in enumerate(command)
        ],
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(transcript, flush=True)
    print(f"Wrote {TRANSCRIPT_PATH}", flush=True)
    print(f"Wrote {METADATA_PATH}", flush=True)
    print(f"Wrote {STDERR_PATH}", flush=True)


if __name__ == "__main__":
    main()
