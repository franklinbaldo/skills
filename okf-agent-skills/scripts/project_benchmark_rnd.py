#!/usr/bin/env python3
"""Project benchmark-R&D fixtures into an existing OKF bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

FILES = {
    "challenge": Path("okf-agent-skills/evals/challenge-frontier-0001.json"),
    "mutations": Path("okf-agent-skills/evals/description-mutations-0001.json"),
    "catalog": Path("okf-agent-skills/evals/catalog-perturbation-0001.json"),
}


def _yaml(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected JSON array")
    rows: list[dict[str, object]] = []
    for index, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: row {index} must be object")
        rows.append(row)
    return rows


def project(root: Path, output: Path) -> dict[str, int]:
    root = root.resolve()
    output = output.resolve()
    rnd_dir = output / "benchmark-rnd"
    rnd_dir.mkdir(parents=True, exist_ok=True)
    for stale in rnd_dir.glob("*.md"):
        stale.unlink()

    challenge = _load(root / FILES["challenge"])
    mutations = _load(root / FILES["mutations"])
    catalog = _load(root / FILES["catalog"])

    for row in challenge:
        row_id = str(row["id"])
        query = str(row["query"])
        tags = ",".join(str(tag) for tag in row.get("tags", []))
        text = [
            "---",
            "type: SkillChallengeCase",
            f"challenge_id: {_yaml(row_id)}",
            f"skill: {_yaml(str(row['target_skill']))}",
            f"should_trigger: {'true' if bool(row['should_trigger']) else 'false'}",
            f"query_sha256: {_yaml(_sha(query))}",
            f"tags: {_yaml(tags)}",
            "---",
            "",
            "## Query",
            "",
            query,
            "",
        ]
        (rnd_dir / f"challenge--{row_id}.md").write_text("\n".join(text), encoding="utf-8")

    for row in mutations:
        row_id = str(row["id"])
        tags = ",".join(str(tag) for tag in row.get("expected_detection_tags", []))
        text = [
            "---",
            "type: SkillBenchmarkMutation",
            f"mutation_id: {_yaml(row_id)}",
            f"skill: {_yaml(str(row['skill']))}",
            f"mutation_kind: {_yaml(str(row['mutation']))}",
            f"expected_detection_tags: {_yaml(tags)}",
            "---",
            "",
            str(row.get("description", "")),
            "",
        ]
        (rnd_dir / f"mutation--{row_id}.md").write_text("\n".join(text), encoding="utf-8")

    catalog_variants = 0
    for row in catalog:
        row_id = str(row["id"])
        catalogs = row.get("catalogs", [])
        if not isinstance(catalogs, list):
            raise ValueError(f"catalog scenario {row_id!r}: catalogs must be list")
        catalog_variants += len(catalogs)
        text = [
            "---",
            "type: SkillCatalogScenario",
            f"scenario_id: {_yaml(row_id)}",
            f"skill: {_yaml(str(row['target_skill']))}",
            f"query_sha256: {_yaml(_sha(str(row['query'])))}",
            f"variant_count: {len(catalogs)}",
            "---",
            "",
            "# Catalog perturbation scenario",
            "",
        ]
        (rnd_dir / f"catalog--{row_id}.md").write_text("\n".join(text), encoding="utf-8")

    return {
        "challenge_cases": len(challenge),
        "mutations": len(mutations),
        "catalog_scenarios": len(catalog),
        "catalog_variants": catalog_variants,
    }
