---
name: okf-agent-skills
description: >-
  Inspect, model, and govern collections of Agent Skills with franklinbaldo/okf-parser
  without changing SKILL.md into a new format. Use when auditing a skills repository,
  analyzing skill-to-skill dependencies, checking progressive disclosure and routing
  metadata, building a queryable DuckDB/graph view of skills, or deciding which repeated
  integration behavior belongs in a skill versus okf-parser core.
when_to_use: >-
  Use for repository-wide Agent Skills analysis, current best-practice audits, dependency
  graphs, relational checks, or deterministic inspection that combines Agent Skills with OKF.
compatibility: >-
  The projection frontend requires Python 3 only. Full relational inspection requires a
  current okf-parser installation; typed audit views additionally require DuckDB.
---

# Use OKF as the inspection layer for Agent Skills

Treat **Agent Skills as authored source** and **OKF as a derived inspection representation**.
Do not require OKF-specific fields in `SKILL.md`, do not invent a replacement skill format,
and do not add Agent-Skills-specific code to `okf-parser` just because an agent can benefit
from this integration.

The default architecture is:

```text
Agent Skills
  → deterministic domain frontend
  → derived OKF + RFC 0006 .schema.sql contracts
  → okf-parser graph / schema / DuckDB
  → canonical static audit queries
```

Real-use learning is intentionally outside this projection. Production postmortems and GitHub
feedback issues belong to `loop-engineering`; static routing evals remain useful regression
memory but are not expanded here into synthetic runs or host/model observations.

## Before starting

1. Identify the skills root and authoritative `SKILL.md` files.
2. Check current upstream documentation when the task depends on current Agent Skills behavior.
3. Inspect the current `okf-parser` interface instead of assuming a remembered CLI version.
4. Never execute scripts belonging to audited/source skills merely to inspect the repository.

For projection details, read `references/projection-model.md`.
For rule classification, read `references/upstream-rules.md`.
For parser-core promotion boundaries, read `references/diagnostics-and-promotion.md`.

## Workflow

### 1. Inventory source

Discover directories whose entry point is `SKILL.md`. Supporting files under a skill directory
are resources of that skill. Do not mutate source skills during inspection unless explicitly
asked.

### 2. Separate authored and derived facts

Authored facts are actually present in source. Derived facts include line counts, file sizes,
resolved links, resource kind, graph structure, static routing eval cases, and semantic mentions.
Never fill absent upstream fields with guessed values.

### 3. Build the disposable typed projection

Use the single public frontend:

```bash
python <skill-dir>/scripts/project.py <skills-root> <derived-bundle>
```

The projection contains:

- one `Skill` concept per `SKILL.md`;
- `SkillResource` concepts for bundled resources;
- provenance-preserving `SkillRelation` concepts for local Markdown relations;
- `SkillEval` concepts for supported static routing-eval files;
- `SkillMention` observations for semantic mentions of sibling skills;
- one `AgentSkillsProjection` manifest;
- RFC 0006 DuckDB declarations under `.okf/contracts/*.schema.sql`.

It deliberately does **not** contain planned routing runs, repeated-run manifests, benchmark
mutations, catalog perturbations, host adapters, or imported `SkillRoutingObservation` state.
Those were laboratory machinery and are no longer part of the canonical learning loop.

### 4. Materialize relations without overstating them

A source Markdown link is stronger evidence than a semantic mention. Hard graph edges should
come from materialized links; ordinary mentions remain observations unless reviewed/promoted.
Keep source path, original target, line, and derived endpoint provenance.

### 5. Compile with current okf-parser

```bash
SPEC='.okf/contracts/{slug}.md'

okf-parser check <derived-bundle>
okf-parser inventory <derived-bundle>
okf-parser graph <derived-bundle>
okf-parser schema <derived-bundle> --format json --spec-template "$SPEC"
okf-parser duckdb <derived-bundle> <output.duckdb> okf --overwrite --spec-template "$SPEC"
```

Do not create a second parser or type system for facts already represented by `okf-parser`.

### 6. Query through the canonical audit layer

```bash
python <skill-dir>/scripts/run_typed_audit.py <output.duckdb> --output audit.json
```

The canonical views cover:

- static routing-eval coverage per skill;
- resolved skill relations;
- semantic mentions without hard edges;
- isolated skills;
- resource/reference/script/eval surface.

These are observations and review queues, not automatic defects.

### 7. Keep real-use evidence outside static projection

Do not infer production quality, routing reliability, or model behavior from this structural
projection. When a skill is used materially, its postmortem/self-report loop is governed by
`../loop-engineering/SKILL.md` and durable actionable learning belongs in GitHub feedback issues.

If a real incident reveals a stable routing boundary, add a static eval later as regression
memory. The regression traces back to the incident; the projection does not manufacture the
incident through repeated synthetic prompts.

### 8. Reassess architecture after real use

When repeated friction appears, classify it before changing `okf-parser`:

```text
keep as skill instruction
keep as bundled deterministic script/query
candidate for generic okf-parser primitive
candidate for Agent-Skills-specific native support
discard
```

Prefer parser-core changes only when the same generic abstraction benefits domains beyond Agent
Skills.

## Guardrails

- Do not execute scripts from audited/source skills during static projection merely to inspect them.
- Do not treat `.schema.sql` as inert data; follow `okf-parser`'s trust model.
- Do not claim static structure proves runtime behavior.
- Do not turn coverage statistics into normative failures without an explicit policy.
- Do not create host adapters or synthetic repeated-run ledgers to approximate production use.
- Do not add parser support merely to save a few lines of skill instructions.

## Definition of done

A repository-wide analysis is complete when:

1. source skills remain authoritative;
2. the static projection is reproducible through `project.py`;
3. relations used for dependency analysis preserve source provenance;
4. static evals and semantic mentions remain distinct from hard relations;
5. current `okf-parser` consumes the generated contracts through generic surfaces;
6. repeated architecture questions use canonical relational views when possible;
7. every reported rule is classified by authority and traces back to source;
8. runtime/quality claims are deferred to real-use postmortems rather than inferred from static data.
