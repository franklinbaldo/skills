"""Transcribe one uploaded audio file with VibeVoice-ASR-HF on a Colab GPU."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

CONFIG_PATH = Path("/content/vibevoice-job.json")
WAV_PATH = Path("/content/vibevoice-input.wav")
TRANSCRIPT_PATH = Path("/content/vibevoice-transcript.txt")
METADATA_PATH = Path("/content/vibevoice-metadata.json")
STDERR_PATH = Path("/content/vibevoice-stderr.log")
CACHE_DIR = Path("/content/vibevoice-hf-cache")

MODEL_ID = "microsoft/VibeVoice-ASR-HF"
TRANSFORMERS_REPOSITORY = "https://github.com/huggingface/transformers.git"
TRANSFORMERS_REF = "71c6f699ac9b3f8fc42a6a3e9dc59034c349a678"


def log(message: str) -> None:
    print(message, flush=True)
    with STDERR_PATH.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def run(
    command: list[str],
    *,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command without exposing context text in logs."""
    log("+ " + " ".join(command))
    return subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture,
    )


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        config = json.load(handle)
    audio = Path(config["audio"])
    if not audio.is_file():
        raise FileNotFoundError(f"Uploaded audio not found: {audio}")
    return config


def ensure_system_tools() -> None:
    required = ("ffmpeg", "ffprobe", "git")
    missing = [tool for tool in required if shutil.which(tool) is None]
    if not missing:
        return
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", "ffmpeg", "git"])


def ensure_python_dependencies() -> None:
    requirement = (
        "transformers @ git+"
        f"{TRANSFORMERS_REPOSITORY}@{TRANSFORMERS_REF}"
    )
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--upgrade",
            requirement,
            "accelerate>=1.10,<2",
            "librosa>=0.11,<1",
            "soundfile>=0.13,<1",
        ]
    )


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


def first_decoded(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def main() -> None:
    started = time.monotonic()
    STDERR_PATH.write_text("", encoding="utf-8")
    config = load_config()
    ensure_system_tools()

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("Full mode requires a CUDA GPU; none is visible in this session")

    gpu_index = torch.cuda.current_device()
    gpu_properties = torch.cuda.get_device_properties(gpu_index)
    gpu_name = torch.cuda.get_device_name(gpu_index)
    gpu_total_gib = gpu_properties.total_memory / (1024**3)
    major, minor = torch.cuda.get_device_capability(gpu_index)
    dtype = torch.bfloat16 if major >= 8 else torch.float16
    log(
        f"GPU: {gpu_name}; VRAM: {gpu_total_gib:.1f} GiB; "
        f"compute capability: {major}.{minor}; dtype: {dtype}"
    )

    audio = Path(config["audio"])
    normalize_audio(audio)
    audio_duration = probe_duration()
    ensure_python_dependencies()

    os.environ.setdefault("HF_HOME", str(CACHE_DIR))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(CACHE_DIR / "transformers"))

    from huggingface_hub import HfApi
    from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration

    model_revision = HfApi().model_info(MODEL_ID).sha
    log(f"Loading {MODEL_ID}@{model_revision}")
    processor = AutoProcessor.from_pretrained(
        MODEL_ID,
        revision=model_revision,
        cache_dir=CACHE_DIR,
    )
    model = VibeVoiceAsrForConditionalGeneration.from_pretrained(
        MODEL_ID,
        revision=model_revision,
        cache_dir=CACHE_DIR,
        device_map="auto",
        dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model.eval()
    device_map = getattr(model, "hf_device_map", {})
    offloaded_devices = {
        str(device)
        for device in device_map.values()
        if str(device) in {"cpu", "disk"}
    }
    if offloaded_devices:
        raise RuntimeError(
            "Full model was partially offloaded to CPU/disk; use a larger GPU "
            "or enable the explicit BitNet fallback"
        )

    context = str(config.get("context", "")).strip()
    request: dict[str, Any] = {"audio": str(WAV_PATH)}
    if context:
        request["prompt"] = context
    input_device = next(model.parameters()).device
    inputs = processor.apply_transcription_request(**request).to(
        input_device, model.dtype
    )

    max_tokens = int(config.get("max_tokens", 16384))
    acoustic_chunk_size = int(
        config.get("acoustic_tokenizer_chunk_size", 1_440_000)
    )
    if acoustic_chunk_size % 3200 != 0:
        raise ValueError("acoustic_tokenizer_chunk_size must be a multiple of 3200")

    torch.cuda.reset_peak_memory_stats(gpu_index)
    inference_started = time.monotonic()
    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=max_tokens,
            acoustic_tokenizer_chunk_size=acoustic_chunk_size,
        )
    inference_seconds = time.monotonic() - inference_started
    generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]

    raw_output = str(first_decoded(processor.decode(generated_ids)))
    parsed_output = first_decoded(
        processor.decode(generated_ids, return_format="parsed")
    )
    transcription = str(
        first_decoded(
            processor.decode(generated_ids, return_format="transcription_only")
        )
    ).strip()
    TRANSCRIPT_PATH.write_text(transcription + "\n", encoding="utf-8")

    peak_allocated_gib = torch.cuda.max_memory_allocated(gpu_index) / (1024**3)
    peak_reserved_gib = torch.cuda.max_memory_reserved(gpu_index) / (1024**3)
    metadata = {
        "model_requested": str(config.get("model_requested", "full")),
        "model_effective": "full",
        "fallback_reason": config.get("fallback_reason"),
        "model": MODEL_ID,
        "model_revision": model_revision,
        "runtime": "huggingface-transformers",
        "transformers_repository": TRANSFORMERS_REPOSITORY,
        "transformers_revision": TRANSFORMERS_REF,
        "gpu_requested": config.get("gpu_requested"),
        "gpu": gpu_name,
        "gpu_total_memory_gib": round(gpu_total_gib, 3),
        "gpu_peak_allocated_gib": round(peak_allocated_gib, 3),
        "gpu_peak_reserved_gib": round(peak_reserved_gib, 3),
        "dtype": str(dtype).removeprefix("torch."),
        "source_input_name": str(config.get("source_input_name", audio.name)),
        "uploaded_audio": audio.name,
        "upload_encoding": str(config.get("upload_encoding", "original")),
        "normalized_audio": str(WAV_PATH),
        "audio_duration_seconds": round(audio_duration, 3),
        "context_supplied": bool(context),
        "max_new_tokens": max_tokens,
        "acoustic_tokenizer_chunk_size": acoustic_chunk_size,
        "inference_seconds": round(inference_seconds, 3),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "parsed_segments": parsed_output,
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"Inference: {inference_seconds:.2f}s for {audio_duration:.2f}s of audio")
    log(
        f"Peak GPU memory: {peak_allocated_gib:.2f} GiB allocated; "
        f"{peak_reserved_gib:.2f} GiB reserved"
    )
    log("Raw model output follows:")
    with STDERR_PATH.open("a", encoding="utf-8") as handle:
        handle.write(raw_output + "\n")
    print(transcription, flush=True)
    print(f"Wrote {TRANSCRIPT_PATH}", flush=True)
    print(f"Wrote {METADATA_PATH}", flush=True)
    print(f"Wrote {STDERR_PATH}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        error = traceback.format_exc()
        print(error, file=sys.stderr, flush=True)
        with STDERR_PATH.open("a", encoding="utf-8") as handle:
            handle.write(error)
        raise
