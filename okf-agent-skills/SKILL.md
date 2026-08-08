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
  graphs, relational checks, or experiments that combine Claude Code skills with OKF.
compatibility: >-
  The projection frontend requires Python 3 only. Full relational inspection requires a
  current okf-parser installation; typed audit views additionally require DuckDB. If
  okf-parser is invoked through the documented uvx-from-GitHub path, uv and outbound network
  access are also required.
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
  → okf-parser TypeContract / import / graph / DuckDB
  → canonical audit queries + behavioral evidence
```

The integration is deliberately **skill-first**. Keep domain knowledge here. Move stable
mechanical work into bundled scripts. Propose a new `okf-parser` primitive only after real use
shows that the behavior is repeated, deterministic, and awkward to express through the
existing generic surfaces.

## Before starting

1. Identify the skills root and the authoritative `SKILL.md` files.
2. Check the current upstream documentation when the task depends on current Claude Code or
   Agent Skills behavior. Prefer:
   - <https://code.claude.com/docs/pt/skills>
   - <https://agentskills.io/specification>
3. Inspect the installed/current `okf-parser` interface rather than assuming a remembered
   CLI version. The integration should use existing commands and public APIs wherever
   possible.
4. Never execute scripts belonging to the audited/source skills merely to inspect the
   repository. Deterministic helpers bundled with this integration skill may be executed for
   projection when their behavior is appropriate and understood.

For the projection contract, read `references/projection-model.md`.
For rule classification and current-best-practice audits, read
`references/upstream-rules.md`.
For diagnostic design and the boundary between skill code and parser core, read
`references/diagnostics-and-promotion.md`.

## Workflow

### 1. Inventory the source tree

Discover directories whose entry point is `SKILL.md`. Record source paths exactly. Treat
supporting files as resources of the owning skill when they live under that skill directory.

Do not mutate source skills during inspection.

### 2. Separate authored facts from derived facts

Authored facts include frontmatter values and file contents actually present in the source.
Derived facts include line counts, file sizes, resolved links, resource kind, graph degree,
routing eval cases, semantic mentions, and other deterministic measurements.

Never silently fill an absent upstream field with a guessed value. If an upstream default is
material to a query, retain whether the value was authored or derived.

### 3. Build the disposable typed OKF projection

For normal filesystem-backed audits, use the single public projection frontend:

```bash
python <skill-dir>/scripts/project.py <skills-root> <derived-bundle>
```

The frontend is stdlib-only and composes the specialized deterministic helpers. It never
executes scripts from the audited skills and does not materialize one document per planned
behavioral run.

The derived bundle contains:

- one `Skill` concept per discovered `SKILL.md`;
- one `SkillResource` concept per bundled supporting file;
- one `SkillRelation` provenance concept per local Markdown relation considered by the
  projector;
- ordinary derived Markdown links for resolved source relations;
- `SkillEval` concepts for supported routing-eval files;
- `SkillMention` observations for semantic mentions of known sibling skills;
- an `AgentSkillsProjection` manifest containing the repetition policy and derived planned
  routing-run count;
- RFC 0006 DuckDB declarations under `.okf/contracts/*.schema.sql` for projected and imported
  concept types, including `SkillRoutingObservation`.

A planned routing run is **not** a fact worth storing as its own concept. The audit layer
derives the plan from `SkillEval × routing_repetitions`; an absent observation is pending by
definition.

The `.schema.sql` files are generated projection metadata, not authored Agent Skills
requirements. They remain outside the concept walk and are addressed through:

```text
.okf/contracts/{slug}.md
```

as the `--spec-template`; current `okf-parser` derives the sibling `.schema.sql` path from
that template.

Do **not** add `type: Skill` or OKF schema fields to the original `SKILL.md` files.

The source projector intentionally does not implement a complete YAML parser. Use source
documents directly when an audit depends on richer frontmatter semantics that the projection
does not yet model.

### 4. Materialize source relations without overstating them

A source Markdown link is stronger evidence than a semantic mention. `okf-parser graph` and
the hard relation layer should contain only relations actually materialized in the derived
bundle.

Example:

```text
source:  A/SKILL.md -> ../datajud/SKILL.md
derived: skills/a.md -> skills/datajud.md
```

A separate `SkillRelation` concept preserves the source path, original target, line and
derived endpoint. A phrase such as “use the datajud skill” without a link may become a
`SkillMention`, but must not silently become the same kind of graph edge.

Do not add a duplicate authored `dependencies:` field merely to make analysis easier.

### 5. Use current `okf-parser` as the generic compiler

For typed inspection, keep one spec template and pass it to schema/DuckDB consumers:

```bash
SPEC='.okf/contracts/{slug}.md'

okf-parser check <derived-bundle>
okf-parser inventory <derived-bundle>
okf-parser graph <derived-bundle>
okf-parser schema <derived-bundle> --format json --spec-template "$SPEC"
okf-parser duckdb <derived-bundle> <output.duckdb> okf --overwrite --spec-template "$SPEC"
```

The RFC 0006 declarations preserve intended physical types such as booleans, integers and
unsigned byte counts instead of forcing every projected scalar through a string-shaped query
surface. Persistent DuckDB keeps the compiler-owned raw carrier beside the typed snapshot.

When `okf-parser` is not installed locally, a current checkout can be invoked with `uvx`, for
example:

```bash
uvx --from 'git+https://github.com/franklinbaldo/okf-parser.git' \
  okf-parser check <derived-bundle>
```

Treat `.schema.sql` as trusted executable DuckDB SQL, following `okf-parser`'s trust model.
Do not create a second parser or type system for facts already represented by `TypeContract`.

### 6. Query architecture through the canonical audit layer

After producing the DuckDB artifact, materialize the bundled audit views:

```bash
python <skill-dir>/scripts/run_typed_audit.py <output.duckdb> --output audit.json
```

The canonical SQL lives at `queries/typed-audit.sql` and creates an `audit` schema with views
for:

- routing-eval coverage per skill;
- resolved skill-to-skill relations;
- semantic mentions that do not currently have a hard edge;
- skills isolated from the hard skill graph;
- resource/reference/script/eval surface per skill;
- imported routing observations;
- routing observation/eval mismatches;
- planned, observed, failed and pending routing runs derived relationally;
- case- and skill-level routing results.

These views are **review queues and observations**, not lint errors. A mention without an
edge, an isolated skill, or a skill without evals can all be legitimate states.

Prefer extending this relational layer when a repeated audit question can be answered from
facts already in the projection. Do not add another text scraper for the same fact.

### 7. Express measurable policy relationally

Good checks operate on facts the projection can establish, for example:

- entry-point line count;
- broken local links;
- reference depth;
- bundled script/resource surface;
- dependency hubs or cycles;
- routing-eval coverage;
- semantic mentions without hard relations;
- presence and values of projected frontmatter facts.

Treat graph statistics and coverage statistics as architecture information, not defects by
default.

### 8. Classify every finding

Every check must say what kind of rule it represents:

- **upstream requirement** — nonconformance with the targeted specification;
- **upstream recommendation** — valid skill, but worth review;
- **repository policy** — a local convention, never presented as universal;
- **observation** — useful structure or measurement, not a diagnostic.

Do not promote recommendations such as “keep the main skill concise” into normative errors.

### 9. Trace findings back to source

Reports must identify the authoritative `SKILL.md` or bundled resource that caused the
finding. For a derived relation, report both the derived endpoints and the source evidence
that produced the edge. The derived OKF document and typed DuckDB artifact are infrastructure,
not the artifacts the author edits.

### 10. Keep behavioral claims separate

Static structure cannot prove that a model routes or follows a skill correctly. Routing eval
concepts express expected behavior; actual model runs are separate evidence.

Use the bundled runner only for the Agent-Skills-specific act of executing a query and
recording the result:

```bash
python <skill-dir>/scripts/routing_runner.py <skills-root> \
  --skill revisao-minutas --case-index 1 --repetition 1 \
  --runner <adapter-name> -- <adapter-command>
```

The output is NDJSON at `.okf/agent-skills-routing-observations.jsonl`. Each row has a stable
`observation_id` and contains either `observed_trigger` or `error`, never a fabricated routing
result for a failed execution.

Do not write a second importer. Feed those rows to the generic backend:

```bash
okf-parser import .okf/agent-skills-routing-observations.jsonl <derived-bundle> \
  --type SkillRoutingObservation --id-column observation_id --write
```

`okf-parser import` owns row-to-concept materialization and duplicate-id rejection; `duckdb`
owns relational materialization; the canonical audit SQL joins observations to the static
`SkillEval` plan. Pending means no matching observation exists. A runner failure is an
observation with `error`, not `observed_trigger: false`.

### 11. Reassess the architecture after real use

When a repeated step is annoying, classify it before changing `okf-parser`:

```text
keep as skill instruction
keep as bundled deterministic script/query
candidate for generic okf-parser primitive
candidate for Agent-Skills-specific native support
discard
```

Prefer a generic primitive only when the same abstraction benefits domains beyond Agent
Skills.

## Guardrails

- Do not execute scripts from the audited/source skills during static projection merely to
  inspect them. Integration-owned deterministic helpers are allowed.
- Do not treat `.schema.sql` as inert data; follow `okf-parser`'s documented trust model.
- Do not claim static presence of a tool/script proves harmful behavior.
- Do not freeze current Claude Code extensions into a portable Agent Skills rule without
  checking which layer defines the field.
- Do not version the derived bundle or DuckDB artifact by default; version them only when
  reviewing the projection itself is useful.
- Do not convert observations from `audit.*` into normative failures without an explicit
  authority or repository policy.
- Do not add native parser support merely to save a few lines of skill instructions.
- Do not represent pending behavioral work as placeholder observation concepts.

## Definition of done

A repository-wide analysis is complete when:

1. source skills remain untouched unless the user asked to change them;
2. the full static OKF projection is reproducible from the source tree through `project.py`;
3. source relations used for dependency analysis are materialized with provenance;
4. routing evals and semantic mentions are represented separately from hard relations;
5. current `okf-parser` consumes generated declarations and imported observation facts through
   generic import/schema/DuckDB surfaces;
6. planned routing runs are derived from evals and repetition policy rather than stored as
   synthetic state;
7. repeated architecture questions use the canonical relational audit layer when possible;
8. every reported rule is classified by authority and traces back to source;
9. behavioral claims rely on model-run evidence rather than static structure alone;
10. any proposed parser-core change explains why a skill, query, or bundled helper is no
    longer enough.
