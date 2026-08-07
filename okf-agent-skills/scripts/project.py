#!/usr/bin/env python3
"""Build the complete Agent Skills inspection IR for current okf-parser surfaces.

This is the single frontend for repository dogfood. It composes the stable static
projectors, applies optional reviewed-relation policy, then writes RFC 0006 DuckDB
declarations for the derived concept types. It never executes code from audited skills.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import project_agent_skills
import project_skill_evals
import project_skill_mentions
import promote_reviewed_relations

SPEC_TEMPLATE = ".okf/contracts/{slug}.md"

DECLARED_SCHEMAS: dict[str, str] = {
    "AgentSkillsProjection": """CREATE TABLE \"AgentSkillsProjection\" (\n    skill_count INTEGER,\n    relation_count INTEGER,\n    resolved_relation_count INTEGER,\n    resource_count INTEGER\n);\n""",
    "Skill": """CREATE TABLE \"Skill\" (\n    name VARCHAR,\n    source_path VARCHAR,\n    source_sha256 VARCHAR,\n    line_count INTEGER\n);\n""",
    "SkillResource": """CREATE TABLE \"SkillResource\" (\n    skill VARCHAR,\n    source_path VARCHAR,\n    kind VARCHAR,\n    size_bytes UBIGINT,\n    source_sha256 VARCHAR,\n    line_count INTEGER\n);\n""",
    "SkillRelation": """CREATE TABLE \"SkillRelation\" (\n    source_skill VARCHAR,\n    target_skill VARCHAR,\n    target_kind VARCHAR,\n    source_path VARCHAR,\n    source_link_target VARCHAR,\n    source_line INTEGER,\n    derived_source VARCHAR,\n    derived_target VARCHAR,\n    resolved BOOLEAN,\n    evidence_kind VARCHAR,\n    review_reason VARCHAR,\n    context_sha256 VARCHAR\n);\n""",
    "SkillEval": """CREATE TABLE \"SkillEval\" (\n    skill VARCHAR,\n    eval_kind VARCHAR,\n    source_path VARCHAR,\n    case_index INTEGER,\n    should_trigger BOOLEAN,\n    query_sha256 VARCHAR\n);\n""",
    "SkillMention": """CREATE TABLE \"SkillMention\" (\n    source_skill VARCHAR,\n    target_skill VARCHAR,\n    source_path VARCHAR,\n    source_line INTEGER,\n    relation_strength VARCHAR,\n    context_sha256 VARCHAR\n);\n""",
}

_SEPARATOR_RE = re.compile(r"[\s/]+")
_REMOVED_RE = re.compile(r"[^a-z0-9-]+")
_HYPHEN_RUN_RE = re.compile(r"-{2,}")


def _slug(concept_type: str) -> str:
    """Mirror okf-parser's public type-slug contract without importing the parser."""
    decomposed = unicodedata.normalize("NFKD", concept_type)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    hyphenated = _SEPARATOR_RE.sub("-", stripped.strip().lower())
    slug = _HYPHEN_RUN_RE.sub("-", _REMOVED_RE.sub("", hyphenated))
    return slug.strip("-")


def write_declared_schemas(output: Path) -> None:
    contract_dir = output / ".okf" / "contracts"
    contract_dir.mkdir(parents=True, exist_ok=True)
    for concept_type, sql in sorted(DECLARED_SCHEMAS.items()):
        (contract_dir / f"{_slug(concept_type)}.schema.sql").write_text(sql, encoding="utf-8")


def project(root: Path, output: Path) -> dict[str, int]:
    root = root.resolve()
    output = output.resolve()

    skills, authored_relations = project_agent_skills.project(root, output)
    evals = project_skill_evals.project(root, output)
    mentions = project_skill_mentions.project(root, output)
    reviewed_relations = promote_reviewed_relations.promote(root, output, mentions)
    write_declared_schemas(output)

    relation_count = len(authored_relations) + len(reviewed_relations)
    return {
        "skills": len(skills),
        "relations": relation_count,
        "authored_relations": len(authored_relations),
        "reviewed_relations": len(reviewed_relations),
        "resolved_relations": sum(relation.resolved for relation in authored_relations)
        + len(reviewed_relations),
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
        f"{counts['skills']} skills, {counts['relations']} relations "
        f"({counts['authored_relations']} authored + {counts['reviewed_relations']} reviewed), "
        f"{counts['evals']} evals, {counts['mentions']} mentions; "
        f"declared {counts['declared_types']} RFC 0006 concept types"
    )
    print(f"spec_template={SPEC_TEMPLATE}")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
