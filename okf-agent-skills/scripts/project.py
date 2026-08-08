#!/usr/bin/env python3
"""Build the static Agent Skills inspection IR for current okf-parser surfaces.

This frontend projects authored/static repository facts only. Behavioral routing
observations are produced separately and imported by okf-parser; pending runs are
therefore derived from eval definitions rather than materialized as fake concepts.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import project_agent_skills
import project_benchmark_rnd
import project_skill_evals
import project_skill_mentions
import promote_reviewed_relations

SPEC_TEMPLATE = ".okf/contracts/{slug}.md"
ROUTING_REPETITIONS = 5

DECLARED_SCHEMAS: dict[str, str] = {
    "AgentSkillsProjection": """CREATE TABLE \"AgentSkillsProjection\" (\n    skill_count INTEGER,\n    relation_count INTEGER,\n    authored_relation_count INTEGER,\n    reviewed_relation_count INTEGER,\n    resolved_relation_count INTEGER,\n    resource_count INTEGER,\n    eval_count INTEGER,\n    routing_repetitions INTEGER,\n    planned_routing_run_count INTEGER,\n    mention_count INTEGER,\n    challenge_case_count INTEGER,\n    benchmark_mutation_count INTEGER,\n    catalog_scenario_count INTEGER,\n    catalog_variant_count INTEGER\n);\n""",
    "Skill": """CREATE TABLE \"Skill\" (\n    name VARCHAR,\n    source_path VARCHAR,\n    source_sha256 VARCHAR,\n    line_count INTEGER\n);\n""",
    "SkillResource": """CREATE TABLE \"SkillResource\" (\n    skill VARCHAR,\n    source_path VARCHAR,\n    kind VARCHAR,\n    size_bytes UBIGINT,\n    source_sha256 VARCHAR,\n    line_count INTEGER\n);\n""",
    "SkillRelation": """CREATE TABLE \"SkillRelation\" (\n    source_skill VARCHAR,\n    target_skill VARCHAR,\n    target_kind VARCHAR,\n    source_path VARCHAR,\n    source_link_target VARCHAR,\n    source_line INTEGER,\n    derived_source VARCHAR,\n    derived_target VARCHAR,\n    resolved BOOLEAN,\n    evidence_kind VARCHAR,\n    review_reason VARCHAR,\n    context_sha256 VARCHAR\n);\n""",
    "SkillEval": """CREATE TABLE \"SkillEval\" (\n    skill VARCHAR,\n    eval_kind VARCHAR,\n    source_path VARCHAR,\n    case_index INTEGER,\n    should_trigger BOOLEAN,\n    query_sha256 VARCHAR\n);\n""",
    "SkillChallengeCase": """CREATE TABLE \"SkillChallengeCase\" (\n    challenge_id VARCHAR,\n    skill VARCHAR,\n    should_trigger BOOLEAN,\n    query_sha256 VARCHAR,\n    tags VARCHAR\n);\n""",
    "SkillBenchmarkMutation": """CREATE TABLE \"SkillBenchmarkMutation\" (\n    mutation_id VARCHAR,\n    skill VARCHAR,\n    mutation_kind VARCHAR,\n    expected_detection_tags VARCHAR\n);\n""",
    "SkillCatalogScenario": """CREATE TABLE \"SkillCatalogScenario\" (\n    scenario_id VARCHAR,\n    skill VARCHAR,\n    query_sha256 VARCHAR,\n    variant_count INTEGER\n);\n""",
    "SkillMention": """CREATE TABLE \"SkillMention\" (\n    source_skill VARCHAR,\n    target_skill VARCHAR,\n    source_path VARCHAR,\n    source_line INTEGER,\n    relation_strength VARCHAR,\n    context_sha256 VARCHAR\n);\n""",
    "SkillRoutingObservation": """CREATE TABLE \"SkillRoutingObservation\" (\n    observation_id VARCHAR,\n    skill VARCHAR,\n    case_index INTEGER,\n    repetition INTEGER,\n    should_trigger BOOLEAN,\n    query_sha256 VARCHAR,\n    observed_trigger BOOLEAN,\n    runner VARCHAR,\n    model VARCHAR,\n    error VARCHAR\n);\n""",
}

_SEPARATOR_RE = re.compile(r"[\s/]+")
_REMOVED_RE = re.compile(r"[^a-z0-9-]+")
_HYPHEN_RUN_RE = re.compile(r"-{2,}")


def _slug(concept_type: str) -> str:
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


def write_final_manifest(output: Path, counts: dict[str, int]) -> None:
    manifest = [
        "---",
        "type: AgentSkillsProjection",
        f"skill_count: {counts['skills']}",
        f"relation_count: {counts['relations']}",
        f"authored_relation_count: {counts['authored_relations']}",
        f"reviewed_relation_count: {counts['reviewed_relations']}",
        f"resolved_relation_count: {counts['resolved_relations']}",
        f"resource_count: {counts['resources']}",
        f"eval_count: {counts['evals']}",
        f"routing_repetitions: {ROUTING_REPETITIONS}",
        f"planned_routing_run_count: {counts['planned_routing_runs']}",
        f"mention_count: {counts['mentions']}",
        f"challenge_case_count: {counts['challenge_cases']}",
        f"benchmark_mutation_count: {counts['benchmark_mutations']}",
        f"catalog_scenario_count: {counts['catalog_scenarios']}",
        f"catalog_variant_count: {counts['catalog_variants']}",
        "---",
        "",
        "# Agent Skills projection",
        "",
        "Derived inspection bundle. Edit the source skills, not this directory.",
        "",
    ]
    (output / "projection.md").write_text("\n".join(manifest), encoding="utf-8")


def project(root: Path, output: Path) -> dict[str, int]:
    root = root.resolve()
    output = output.resolve()

    skills, authored_relations = project_agent_skills.project(root, output)
    evals = project_skill_evals.project(root, output)
    benchmark_rnd = project_benchmark_rnd.project(root, output)
    mentions = project_skill_mentions.project(root, output)
    reviewed_relations = promote_reviewed_relations.promote(root, output, mentions)

    counts = {
        "skills": len(skills),
        "relations": len(authored_relations) + len(reviewed_relations),
        "authored_relations": len(authored_relations),
        "reviewed_relations": len(reviewed_relations),
        "resolved_relations": sum(relation.resolved for relation in authored_relations)
        + len(reviewed_relations),
        "resources": len(list((output / "resources").glob("*.md"))),
        "evals": len(evals),
        "planned_routing_runs": len(evals) * ROUTING_REPETITIONS,
        "mentions": len(mentions),
        "challenge_cases": benchmark_rnd["challenge_cases"],
        "benchmark_mutations": benchmark_rnd["mutations"],
        "catalog_scenarios": benchmark_rnd["catalog_scenarios"],
        "catalog_variants": benchmark_rnd["catalog_variants"],
        "declared_types": len(DECLARED_SCHEMAS),
    }
    write_final_manifest(output, counts)
    write_declared_schemas(output)
    return counts


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
        f"{counts['evals']} evals -> {counts['planned_routing_runs']} planned routing runs, "
        f"{counts['challenge_cases']} challenge cases, {counts['benchmark_mutations']} mutations, "
        f"{counts['catalog_scenarios']} catalog scenarios/{counts['catalog_variants']} variants, "
        f"{counts['mentions']} mentions; declared {counts['declared_types']} RFC 0006 concept types"
    )
    print(f"spec_template={SPEC_TEMPLATE}")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
