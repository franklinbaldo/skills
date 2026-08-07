#!/usr/bin/env python3
"""Project semantic mentions of known sibling skills as non-edge OKF observations."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _body_lines(path: Path) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                start = index + 1
                return [(i + 1, text) for i, text in enumerate(lines[start:], start=start)]
    return [(i, text) for i, text in enumerate(lines, start=1)]


def discover_mentions(root: Path) -> list[dict[str, object]]:
    skill_files = sorted(root.glob("*/SKILL.md"))
    names = [path.parent.name for path in skill_files]
    mentions: list[dict[str, object]] = []

    for source_file in skill_files:
        source_skill = source_file.parent.name
        for line_no, line in _body_lines(source_file):
            for target_skill in names:
                if target_skill == source_skill:
                    continue
                pattern = rf"(?<![A-Za-z0-9-]){re.escape(target_skill)}(?![A-Za-z0-9-])"
                if not re.search(pattern, line, flags=re.IGNORECASE):
                    continue
                mentions.append(
                    {
                        "source_skill": source_skill,
                        "target_skill": target_skill,
                        "source_path": source_file.relative_to(root).as_posix(),
                        "source_line": line_no,
                        "context_sha256": hashlib.sha256(line.strip().encode("utf-8")).hexdigest(),
                    }
                )
    return sorted(
        mentions,
        key=lambda item: (
            str(item["source_skill"]),
            str(item["target_skill"]),
            int(item["source_line"]),
        ),
    )


def project(root: Path, output: Path) -> list[dict[str, object]]:
    root = root.resolve()
    output = output.resolve()
    mention_dir = output / "mentions"
    mention_dir.mkdir(parents=True, exist_ok=True)
    for stale in mention_dir.glob("*.md"):
        stale.unlink()

    mentions = discover_mentions(root)
    for index, mention in enumerate(mentions, start=1):
        fields = [
            "---",
            "type: SkillMention",
            f"source_skill: {_yaml_string(str(mention['source_skill']))}",
            f"target_skill: {_yaml_string(str(mention['target_skill']))}",
            f"source_path: {_yaml_string(str(mention['source_path']))}",
            f"source_line: {int(mention['source_line'])}",
            'relation_strength: "mention"',
            f"context_sha256: {_yaml_string(str(mention['context_sha256']))}",
            "---",
            "",
        ]
        (mention_dir / f"mention--{index:04d}.md").write_text("\n".join(fields), encoding="utf-8")
    return mentions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    mentions = project(args.source, args.output)
    pairs = {(str(item['source_skill']), str(item['target_skill'])) for item in mentions}
    print(f"projected {len(mentions)} skill mentions across {len(pairs)} source/target pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
