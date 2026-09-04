#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "paddleocr",
#     "paddlepaddle",
#     "cyclopts>=3.0",
# ]
# ///
"""Run PaddleOCR on one image or PDF and export Markdown plus metrics."""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import cyclopts

DEFAULT_INPUT_DIR = Path("/content/input")
DEFAULT_OUTPUT = Path("/content/output/result.md")
SUPPORTED_SUFFIXES = {
    ".bmp",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


def find_colab_input() -> Path:
    candidates = sorted(
        path
        for path in DEFAULT_INPUT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if len(candidates) != 1:
        names = ", ".join(path.name for path in candidates) or "none"
        raise RuntimeError(
            f"Expected exactly one PDF or image in {DEFAULT_INPUT_DIR}; found {names}."
        )
    return candidates[0]


def resolve_paths(input_path: Path | None, output_path: Path | None) -> tuple[Path, Path]:
    if input_path is None:
        configured_input = os.environ.get("PADDLE_OCR_INPUT")
        input_path = Path(configured_input) if configured_input else find_colab_input()

    if output_path is None:
        output_path = Path(os.environ.get("PADDLE_OCR_OUTPUT", str(DEFAULT_OUTPUT)))

    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if input_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported input type: {input_path.suffix}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return input_path, output_path


def resolve_device(paddle: Any, configured: str) -> str:
    if configured != "auto":
        return configured
    if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
        return "gpu:0"
    return "cpu"


def result_payload(result: Any) -> dict[str, Any]:
    payload = result.json
    if callable(payload):
        payload = payload()
    return payload.get("res", payload)


def run_pass(
    ocr: Any,
    input_path: Path,
    *,
    min_confidence: float,
    json_dir: Path | None,
) -> tuple[float, list[float], list[float], list[str]]:
    started = time.perf_counter()
    previous = started
    page_times: list[float] = []
    page_scores: list[float] = []
    markdown_pages: list[str] = []

    for page_number, result in enumerate(ocr.predict_iter(str(input_path)), start=1):
        now = time.perf_counter()
        page_times.append(now - previous)
        previous = now

        payload = result_payload(result)
        texts = list(payload.get("rec_texts", []))
        scores = [float(score) for score in payload.get("rec_scores", [])]
        accepted = [
            text.strip()
            for text, score in zip(texts, scores, strict=False)
            if text.strip() and score >= min_confidence
        ]
        mean_score = statistics.fmean(scores) if scores else 0.0
        page_scores.append(mean_score)
        markdown_pages.append(
            f"<!-- Page {page_number}; mean confidence {mean_score:.4f} -->\n\n"
            + "\n".join(accepted)
        )

        if json_dir is not None:
            json_dir.mkdir(parents=True, exist_ok=True)
            result.save_to_json(str(json_dir / f"page-{page_number:04d}.json"))

        print(
            f"Page {page_number}: {page_times[-1]:.3f}s, "
            f"{len(accepted)} lines, mean confidence {mean_score:.4f}",
            flush=True,
        )

    return time.perf_counter() - started, page_times, page_scores, markdown_pages


app = cyclopts.App(name="ocr", help=__doc__)


@app.default
def main(
    input: Path | None = None,  # noqa: A002
    output: Path | None = None,
    *,
    device: str = os.environ.get("PADDLE_OCR_DEVICE", "auto"),
    lang: str = os.environ.get("PADDLE_OCR_LANG", "pt"),
    ocr_version: str = os.environ.get("PADDLE_OCR_VERSION", "PP-OCRv6"),
    min_confidence: float = 0.0,
    json_dir: Path | None = None,
    warm_benchmark: bool = False,
) -> None:
    """Run PaddleOCR and export Markdown plus metrics.

    Parameters
    ----------
    input
        Image or PDF; defaults to PADDLE_OCR_INPUT or the Colab upload.
    output
        Markdown output path; defaults to PADDLE_OCR_OUTPUT.
    device
        auto, cpu, gpu, or gpu:N.
    lang
        PaddleOCR language code.
    ocr_version
        PaddleOCR pipeline version.
    min_confidence
        Drop recognized lines below this confidence.
    json_dir
        Directory for the raw per-page JSON results.
    warm_benchmark
        Run a second warm pass and record its timings.
    """
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    import paddle

    from paddleocr import PaddleOCR

    input_path, output_path = resolve_paths(input, output)
    device = resolve_device(paddle, device)
    if device == "cpu":
        print(
            "WARNING: CPU OCR is much slower than GPU for multi-page documents.",
            file=sys.stderr,
            flush=True,
        )
    if device.startswith("gpu") and not paddle.device.is_compiled_with_cuda():
        raise RuntimeError("GPU requested, but PaddlePaddle has no CUDA support.")

    paddle.set_device(device)
    initialization_started = time.perf_counter()
    ocr = PaddleOCR(
        lang=lang,
        ocr_version=ocr_version,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        device=device,
    )
    initialization_time = time.perf_counter() - initialization_started
    print(f"Device: {device}", flush=True)
    print(f"Pipeline initialization: {initialization_time:.3f}s", flush=True)

    total, page_times, page_scores, markdown_pages = run_pass(
        ocr,
        input_path,
        min_confidence=min_confidence,
        json_dir=json_dir,
    )
    if not page_times:
        raise RuntimeError("PaddleOCR returned no pages.")
    output_path.write_text(
        "\n\n".join(markdown_pages).strip() + "\n",
        encoding="utf-8",
    )

    metrics: dict[str, Any] = {
        "device": device,
        "paddle": paddle.__version__,
        "input": str(input_path),
        "output": str(output_path),
        "pages": len(page_times),
        "pipeline_initialization_seconds": initialization_time,
        "inference_seconds": total,
        "page_seconds": page_times,
        "mean_seconds_per_page": statistics.fmean(page_times),
        "mean_page_confidence": statistics.fmean(page_scores),
    }
    if warm_benchmark:
        warm_total, warm_times, _, _ = run_pass(
            ocr,
            input_path,
            min_confidence=min_confidence,
            json_dir=None,
        )
        metrics["warm_inference_seconds"] = warm_total
        metrics["warm_page_seconds"] = warm_times
        metrics["warm_mean_seconds_per_page"] = statistics.fmean(warm_times)

    metrics_path = output_path.with_suffix(".metrics.json")
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2, ensure_ascii=False), flush=True)
    print(f"Markdown: {output_path}", flush=True)
    print(f"Metrics: {metrics_path}", flush=True)


if __name__ == "__main__":
    app()
