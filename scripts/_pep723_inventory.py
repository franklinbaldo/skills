from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPF_COMMIT = "f7f00ca7fb869683eb732c010299d901457f19c3"
SPECIAL = ROOT / "experiments/metered-public-0001/count_usage.py"

DEPENDENCIES: dict[str, list[str]] = {
    "anonimizacao-documentos/scripts/anonimizar.py": [],
    "anonimizacao-documentos/scripts/anonimizar_opf.py": [
        f"opf @ git+https://github.com/openai/privacy-filter.git@{OPF_COMMIT}",
        "torch",
    ],
    "anonimizacao-documentos/scripts/auditar_pii.py": ["litellm"],
    "anonimizacao-documentos/scripts/setup_colab_opf.py": [],
    "convert-to-pdfa/scripts/convert_to_pdfa.py": ["pymupdf"],
    "datajud/scripts/datajud.py": [],
    "datajud/scripts/datajud_mcp.py": ["fastmcp>=2.0"],
    "free-gpu/scripts/colab_windows.py": ["google-colab-cli"],
    "free-gpu/scripts/create_kaggle_job.py": [],
    "juris-tjro/scripts/juris.py": [],
    "okf-agent-skills/scripts/project.py": [],
    "okf-agent-skills/scripts/project_agent_skills.py": [],
    "okf-agent-skills/scripts/project_skill_evals.py": [],
    "okf-agent-skills/scripts/project_skill_mentions.py": [],
    "okf-agent-skills/scripts/promote_reviewed_relations.py": [],
    "okf-agent-skills/scripts/run_typed_audit.py": ["duckdb"],
    "opf-finetune/scripts/opf_annotate.py": [],
    "paddleocr/scripts/ocr.py": ["paddleocr", "paddlepaddle"],
    "paddleocr/scripts/setup_colab_gpu.py": [],
    "pdf-compression/scripts/2up.py": ["pymupdf"],
    "pdf-compression/scripts/compress.py": [
        "numpy",
        "opencv-python-headless",
        "pillow",
        "pymupdf",
    ],
    "pdf-compression/scripts/process_pdf.py": ["pillow", "pymupdf"],
    "pdf-to-markdown/scripts/convert_pdf.py": ["pymupdf"],
    "scripts/axiom_graph.py": [],
    "scripts/check_markdown_format.py": ["mdformat"],
    "scripts/lean_docgen_md.py": [],
    "vibevoice-asr/scripts/colab_job_bitnet.py": ["huggingface-hub"],
    "vibevoice-asr/scripts/colab_job_full.py": [
        "huggingface-hub",
        "torch",
        "transformers",
    ],
    "experiments/metered-public-0001/count_usage.py": [],
}

PEP_BLOCK = re.compile(r"(?ms)^# /// script\n.*?^# ///\n")


def candidates() -> list[Path]:
    paths = {
        p
        for p in ROOT.rglob("*.py")
        if "scripts" in p.parts
        and not p.name.startswith("test_")
        and p.name != Path(__file__).name
    }
    if SPECIAL.exists():
        paths.add(SPECIAL)
    return sorted(paths)


def metadata(dependencies: list[str]) -> str:
    lines = ["# /// script", '# requires-python = ">=3.11"', "# dependencies = ["]
    lines.extend(f'#     "{dep}",' for dep in dependencies)
    lines.extend(["# ]", "# ///", ""])
    return "\n".join(lines)


def migrate(path: Path, dependencies: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    text = PEP_BLOCK.sub("", text, count=1)
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("#!"):
        lines[0] = "#!/usr/bin/env -S uv run --script\n"
        body = "".join(lines)
    else:
        body = text
        if body and not body.endswith("\n"):
            body += "\n"
        body = "#!/usr/bin/env -S uv run --script\n" + body
    first, rest = body.split("\n", 1)
    path.write_text(first + "\n" + metadata(dependencies) + rest, encoding="utf-8")
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def main() -> None:
    found = {p.relative_to(ROOT).as_posix() for p in candidates()}
    expected = set(DEPENDENCIES)
    if found != expected:
        missing = sorted(found - expected)
        stale = sorted(expected - found)
        raise SystemExit(f"candidate map drift: unmapped={missing} stale={stale}")

    for path in candidates():
        rel = path.relative_to(ROOT).as_posix()
        migrate(path, DEPENDENCIES[rel])
        print(f"migrated {rel}: {DEPENDENCIES[rel]}")

    residual = [
        p.relative_to(ROOT).as_posix()
        for p in candidates()
        if "# /// script" not in p.read_text(encoding="utf-8")
    ]
    if residual:
        raise SystemExit(f"scripts without PEP 723 after migration: {residual}")


if __name__ == "__main__":
    main()
