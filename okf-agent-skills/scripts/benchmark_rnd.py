#!/usr/bin/env python3
"""Validate and expand benchmark-R&D experiment definitions.

This helper never invokes a model and never decides whether a skill should route.
It only validates challenge/mutation/catalog experiment files and expands catalog
perturbations into a deterministic manifest for an external evaluator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_array(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected JSON array")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: row {index} must be object")
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            raise ValueError(f"{path}: row {index} needs non-empty id")
        if row_id in seen:
            raise ValueError(f"{path}: duplicate id {row_id!r}")
        seen.add(row_id)
        rows.append(row)
    return rows


def validate_challenge(path: Path) -> dict[str, int]:
    rows = _load_array(path)
    positives = negatives = 0
    for row in rows:
        if not isinstance(row.get("target_skill"), str):
            raise ValueError(f"{path}: {row['id']} needs target_skill")
        query = row.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"{path}: {row['id']} needs query")
        expected = row.get("should_trigger")
        if not isinstance(expected, bool):
            raise ValueError(f"{path}: {row['id']} needs boolean should_trigger")
        tags = row.get("tags")
        if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) and tag for tag in tags):
            raise ValueError(f"{path}: {row['id']} needs non-empty string tags")
        positives += int(expected)
        negatives += int(not expected)
    return {"cases": len(rows), "positives": positives, "negatives": negatives}


def validate_mutations(path: Path) -> dict[str, int]:
    rows = _load_array(path)
    skills: set[str] = set()
    for row in rows:
        skill = row.get("skill")
        if not isinstance(skill, str) or not skill:
            raise ValueError(f"{path}: {row['id']} needs skill")
        if not isinstance(row.get("mutation"), str) or not row["mutation"]:
            raise ValueError(f"{path}: {row['id']} needs mutation")
        tags = row.get("expected_detection_tags")
        if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) and tag for tag in tags):
            raise ValueError(f"{path}: {row['id']} needs expected_detection_tags")
        skills.add(skill)
    return {"mutations": len(rows), "skills": len(skills)}


def expand_catalog(path: Path) -> list[dict[str, object]]:
    rows = _load_array(path)
    manifest: list[dict[str, object]] = []
    for row in rows:
        query = row.get("query")
        target = row.get("target_skill")
        catalogs = row.get("catalogs")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"{path}: {row['id']} needs query")
        if not isinstance(target, str) or not target:
            raise ValueError(f"{path}: {row['id']} needs target_skill")
        if not isinstance(catalogs, list) or not catalogs:
            raise ValueError(f"{path}: {row['id']} needs catalogs")
        for variant, catalog in enumerate(catalogs, start=1):
            if not isinstance(catalog, list) or not catalog or not all(isinstance(skill, str) and skill for skill in catalog):
                raise ValueError(f"{path}: {row['id']} catalog {variant} must be non-empty strings")
            if len(set(catalog)) != len(catalog):
                raise ValueError(f"{path}: {row['id']} catalog {variant} contains duplicates")
            if target not in catalog:
                raise ValueError(f"{path}: {row['id']} catalog {variant} omits target skill")
            manifest.append(
                {
                    "experiment_id": row["id"],
                    "variant": variant,
                    "query": query.strip(),
                    "target_skill": target,
                    "catalog": catalog,
                    "catalog_size": len(catalog),
                }
            )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("challenge", type=Path)
    validate.add_argument("mutations", type=Path)
    validate.add_argument("catalog", type=Path)

    expand = sub.add_parser("catalog-manifest")
    expand.add_argument("catalog", type=Path)
    expand.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "validate":
        result = {
            "challenge": validate_challenge(args.challenge),
            "mutations": validate_mutations(args.mutations),
            "catalog_variants": len(expand_catalog(args.catalog)),
        }
        print(json.dumps(result, sort_keys=True))
        return 0

    manifest = expand_catalog(args.catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in manifest),
        encoding="utf-8",
    )
    print(f"wrote {len(manifest)} catalog variants to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
