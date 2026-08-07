#!/usr/bin/env python3
"""Project official Agent Skills routing eval queries into an existing OKF bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

EVAL_QUERIES = PurePosixPath("evals/eval_queries.json")


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def discover_routing_evals(root: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for skill_file in sorted(root.glob("*/SKILL.md")):
        skill = skill_file.parent.name
        eval_file = skill_file.parent / Path(EVAL_QUERIES.as_posix())
        if not eval_file.exists():
            continue
        data = json.loads(eval_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{eval_file}: expected a JSON array")
        for index, case in enumerate(data, start=1):
            if not isinstance(case, dict):
                raise ValueError(f"{eval_file}: case {index} must be an object")
            query = case.get("query")
            should_trigger = case.get("should_trigger")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(f"{eval_file}: case {index} needs a non-empty query")
            if not isinstance(should_trigger, bool):
                raise ValueError(f"{eval_file}: case {index} needs boolean should_trigger")
            cases.append(
                {
                    "skill": skill,
                    "source_path": eval_file.relative_to(root).as_posix(),
                    "case_index": index,
                    "query": query.strip(),
                    "should_trigger": should_trigger,
                }
            )
    return cases


def project(root: Path, output: Path) -> list[dict[str, object]]:
    root = root.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    eval_dir = output / "evals"
    eval_dir.mkdir(parents=True, exist_ok=True)

    for stale in eval_dir.glob("*.md"):
        stale.unlink()

    cases = discover_routing_evals(root)
    per_skill: dict[str, int] = {}
    for case in cases:
        skill = str(case["skill"])
        per_skill[skill] = per_skill.get(skill, 0) + 1
        ordinal = per_skill[skill]
        query = str(case["query"])
        fields = [
            "---",
            "type: SkillEval",
            f"skill: {_yaml_string(skill)}",
            'eval_kind: "trigger"',
            f"source_path: {_yaml_string(str(case['source_path']))}",
            f"case_index: {int(case['case_index'])}",
            f"should_trigger: {'true' if case['should_trigger'] else 'false'}",
            f"query_sha256: {_yaml_string(_sha256_text(query))}",
            "---",
            "",
            "## Query",
            "",
            query,
            "",
        ]
        (eval_dir / f"{skill}--trigger--{ordinal:03d}.md").write_text(
            "\n".join(fields), encoding="utf-8"
        )
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    cases = project(args.source, args.output)
    positives = sum(bool(case["should_trigger"]) for case in cases)
    print(
        f"projected {len(cases)} trigger evals "
        f"({positives} should-trigger, {len(cases) - positives} should-not-trigger)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
