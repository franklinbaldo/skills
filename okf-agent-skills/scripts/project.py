#!/usr/bin/env python3
"""Build the complete Agent Skills inspection IR for current okf-parser surfaces.

This is the single frontend for repository dogfood. It composes the stable static
projectors, then writes RFC 0006 DuckDB declarations for the derived concept types.
It never executes code from the audited skills.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import project_agent_skills
import project_skill_evals
import project_skill_mentions

SPEC_TEMPLATE = ".okf/contracts/{slug}.md"

DECLARED_SCHEMAS: dict[str, str] = {
    "AgentSkillsProjection": """CREATE TABLE \"AgentSkillsProjection\" (\n    skill_count INTEGER,\n    relation_count INTEGER,\n    resolved_relation_count INTEGER,\n    resource_count INTEGER\n);\n""",
    "Skill": """CREATE TABLE \"Skill\" (\n    name VARCHAR,\n    source_path VARCHAR,\n    source_sha256 VARCHAR,\n    line_count INTEGER\n);\n""",
    "SkillResource": """CREATE TABLE \"SkillResource\" (\n    skill VARCHAR,\n    source_path VARCHAR,\n    kind VARCHAR,\n    size_bytes UBIGINT,\n    source_sha256 VARCHAR,\n    line_count INTEGER\n);\n""",
    "SkillRelation": """CREATE TABLE \"SkillRelation\" (\n    source_skill VARCHAR,\n    target_skill VARCHAR,\n    target_kind VARCHAR,\n    source_path VARCHAR,\n    source_link_target VARCHAR,\n    source_line INTEGER,\n    derived_source VARCHAR,\n    derived_target VARCHAR,\n    resolved BOOLEAN\n);\n""",
    "SkillEval": """CREATE TABLE \"SkillEval\" (\n    skill VARCHAR,\n    eval_kind VARCHAR,\n    source_path VARCHAR,\n    case_index INTEGER,\n    should_trigger BOOLEAN,\n    query_sha256 VARCHAR\n);\n""",
    "SkillMention": """CREATE TABLE \"SkillMention\" (\n    source_skill VARCHAR,\n    target_skill VARCHAR,\n    source_path VARCHAR,\n    source_line INTEGER,\n    relation_strength VARCHAR,\n    context_sha256 VARCHAR\n);\n""",
}


def _slug(concept_type: str) -> str:
    """Return the okf-parser slug for the ASCII concept names used by this IR."""
    parts: list[str] = []
    current = ""
    for char in concept_type:
        if char.isupper() and current:
            parts.append(current.lower())
            current = char
        else:
            current += char
    if current:
        parts.append(current.lower())
    return "-".join(parts)


def write_declared_schemas(output: Path) -> None:
    contract_dir = output / ".okf" / "contracts"
    contract_dir.mkdir(parents=True, exist_ok=True)
    for concept_type, sql in sorted(DECLARED_SCHEMAS.items()):
        (contract_dir / f"{_slug(concept_type)}.schema.sql").write_text(sql, encoding="utf-8")


def project(root: Path, output: Path) -> dict[str, int]:
    root = root.resolve()
    output = output.resolve()

    skills, relations = project_agent_skills.project(root, output)
    evals = project_skill_evals.project(root, output)
    mentions = project_skill_mentions.project(root, output)
    write_declared_schemas(output)

    return {
        "skills": len(skills),
        "relations": len(relations),
        "resolved_relations": sum(relation.resolved for relation in relations),
        "evals": len(evals),
        "mentions": len(mentions),
        "declared_types": len(DECLARED_SCHEMAS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Agent Skills repository/root")
    parser.add_argument("output", type=Path, help="Disposable OKF output directory")
    args = parser.parse_args()

    counts = project(args.source, args.output)
    print(
        "projected "
        f"{counts['skills']} skills, {counts['relations']} relations, "
        f"{counts['evals']} evals, {counts['mentions']} mentions; "
        f"declared {counts['declared_types']} RFC 0006 concept types"
    )
    print(f"spec_template={SPEC_TEMPLATE}")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
