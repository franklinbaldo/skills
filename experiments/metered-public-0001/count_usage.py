#!/usr/bin/env python3
"""Count Experiment 0001 principal-skill invocations from factual usage records."""

from pathlib import Path

ROOT = Path(__file__).parent / "usage"


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def main() -> None:
    records = []
    for path in sorted(ROOT.glob("usage-*.md")):
        data = frontmatter(path)
        if data.get("status") != "experiment_evidence":
            continue
        if data.get("skill") != "okf-agent-skills":
            continue
        if data.get("productive_execution_started") != "true":
            continue
        if data.get("counted") != "true":
            continue
        records.append((path.name, data["invocation_id"]))

    invocation_ids = [invocation_id for _, invocation_id in records]
    if len(invocation_ids) != len(set(invocation_ids)):
        raise SystemExit(f"duplicate invocation_id: {invocation_ids}")

    for path, invocation_id in records:
        print(f"{path}\t{invocation_id}\t+1")
    print(f"usage_total={len(invocation_ids)}")


if __name__ == "__main__":
    main()
