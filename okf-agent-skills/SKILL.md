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
---

# Use OKF as the inspection layer for Agent Skills

Treat **Agent Skills as authored source** and **OKF as a derived inspection representation**.
Do not require OKF-specific fields in `SKILL.md`, do not invent a replacement skill format,
and do not add Agent-Skills-specific code to `okf-parser` just because an agent can benefit
from this integration.

The default architecture is:

```text
Agent Skills → this skill / deterministic helper → derived OKF → okf-parser → SQL / graph / diagnostics
```

The integration is deliberately **skill-first**. Keep domain knowledge here. Move only
stable mechanical work into bundled scripts. Propose a new `okf-parser` primitive only
after real use shows that the behavior is repeated, deterministic, and awkward to express
through the existing generic surfaces.

## Before starting

1. Identify the skills root and the authoritative `SKILL.md` files.
2. Check the current upstream documentation when the task depends on current Claude Code or
   Agent Skills behavior. Prefer:
   - <https://code.claude.com/docs/pt/skills>
   - <https://agentskills.io/specification>
3. Inspect the installed/current `okf-parser` interface rather than assuming a remembered
   CLI version. The integration should use existing commands and public APIs wherever
   possible.
4. Never execute bundled scripts merely to inspect a skill repository.

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
and other deterministic measurements.

Never silently fill an absent upstream field with a guessed value. If an upstream default is
material to a query, retain whether the value was authored or derived.

### 3. Build a disposable OKF projection

Create a temporary or ignored OKF bundle representing the corpus. The first version should
stay small:

- one `Skill` concept per discovered `SKILL.md`;
- one `SkillResource` concept per relevant bundled file;
- ordinary Markdown links for relations wherever the source already contains links;
- optional `SkillEval` concepts only when the repository has a real eval corpus.

Do **not** add `type: Skill` to the original `SKILL.md`. Put OKF metadata only in the derived
bundle or in supporting documents that are intentionally authored as OKF concepts.

### 4. Prefer evidence already present in the source

If `A/SKILL.md` links to `B/SKILL.md`, use that link as dependency evidence. Do not duplicate
it into an invented `dependencies:` field unless there is a real relation that cannot be
represented by the source evidence.

Prose such as “use the datajud skill” without a link may be reported as a semantic candidate,
but do not pretend a heuristic extraction is equivalent to a resolved authored link.

### 5. Use `okf-parser` as the generic engine

Use the existing surfaces to validate and inspect the derived bundle:

```bash
okf-parser check <derived-bundle>
okf-parser inventory <derived-bundle>
okf-parser graph <derived-bundle>
okf-parser duckdb <derived-bundle> <output.duckdb>
```

Use `apply`, Ibis, DuckDB SQL, schema export, or MCP surfaces when they are available and
fit the task. Do not create a second parser or linter for facts already represented by OKF.

### 6. Express measurable policy relationally

Good checks operate on facts the projection can establish, for example:

- entry-point line count;
- broken local links;
- reference depth;
- unreferenced bundled scripts;
- dependency hubs or cycles;
- coverage by repository eval concepts;
- presence and values of current frontmatter fields.

Treat graph statistics as architecture information, not defects by default.

### 7. Classify every finding

Every check must say what kind of rule it represents:

- **upstream requirement** — nonconformance with the targeted specification;
- **upstream recommendation** — valid skill, but worth review;
- **repository policy** — a local convention, never presented as universal;
- **observation** — useful structure or measurement, not a diagnostic.

Do not promote recommendations such as “keep the main skill concise” into normative errors.

### 8. Trace findings back to source

Reports must identify the authoritative `SKILL.md` or bundled resource that caused the
finding. The derived OKF document is infrastructure, not the artifact the author edits.

### 9. Keep behavioral claims separate

Static structure cannot prove that a model routes or follows a skill correctly. If routing or
behavior matters, inspect or create behavioral evals. OKF may store and query the eval corpus;
the model run remains a separate evaluation step.

### 10. Reassess the architecture after real use

When a repeated step is annoying, classify it before changing `okf-parser`:

```text
keep as skill instruction
keep as bundled deterministic script
candidate for generic okf-parser primitive
candidate for Agent-Skills-specific native support
discard
```

Prefer a generic primitive when the same abstraction benefits domains beyond Agent Skills.

## Guardrails

- Do not execute source skill scripts during static projection.
- Do not treat `.schema.sql` as inert data; follow `okf-parser`'s documented trust model.
- Do not claim static presence of a tool/script proves harmful behavior.
- Do not freeze current Claude Code extensions into a portable Agent Skills rule without
  checking which layer defines the field.
- Do not version the derived bundle by default; version it only when reviewing the graph or
  relational projection itself is useful.
- Do not add native parser support merely to save a few lines of skill instructions.

## Definition of done

A repository-wide analysis is complete when:

1. source skills remain untouched unless the user asked to change them;
2. the OKF projection is reproducible from the source tree;
3. `okf-parser` can inspect the projection using generic surfaces;
4. every reported rule is classified by authority;
5. every finding traces back to source;
6. heuristic findings are labeled as heuristic;
7. any proposed core change explains why a skill or bundled helper is no longer enough.
