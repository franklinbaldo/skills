# Projection model

The projection is derived state. Agent Skills remain authoritative; OKF exists so the corpus
can be queried and graphed with `okf-parser`.

## Minimum concepts

### Skill

Create one concept per discovered `SKILL.md`.

Recommended fields are deliberately small and objective:

```yaml
---
type: Skill
name: revisao-minutas
source_path: revisao-minutas/SKILL.md
description: Adversarial risk triage of draft legal filings before filing.
line_count: 420
---
```

Project upstream frontmatter fields only when present or when a documented default is
material. Useful candidates include `when_to_use`, `compatibility`, `allowed-tools`,
`user-invocable`, `disable-model-invocation`, `context`, `agent`, `model`, and `effort`.
Preserve whether a value was authored versus derived when that distinction matters.

Do not copy the whole `SKILL.md` body into frontmatter. The source path is the authority.

### SkillResource

Create one concept per supporting file that matters to the requested analysis:

```yaml
---
type: SkillResource
skill: revisao-minutas
source_path: revisao-minutas/references/risco-fatal.md
kind: reference
line_count: 180
size_bytes: 12345
---
```

Useful `kind` values:

- `reference`
- `script`
- `asset`
- `example`
- `other`

Do not infer semantic importance from directory name alone when the repository uses a
nonstandard layout; record the evidence used for classification.

### SkillEval

Only project evals that actually exist. Do not invent an eval format merely to make the
table non-empty.

If the repository already uses OKF concepts for evals, keep that authored representation.
Otherwise a derived representation may record at least:

```yaml
---
type: SkillEval
skill: revisao-minutas
source_path: evals/revisao-minutas/trigger-01.md
expected: trigger
---
```

Execution outcome is separate from the eval case itself.

## Relations

Prefer the normal Markdown link relation already extracted by `okf-parser`.

For example:

```markdown
Use [datajud](../datajud/SKILL.md) to verify process metadata.
```

already supplies source evidence for a skill-to-skill edge. Avoid adding a duplicate
`dependencies:` field to the authored skill.

A semantic mention without a link may be reported separately as a candidate relation, but it
must not be silently upgraded to the same certainty as a resolved link.

## Physical layout

The projection may use any deterministic layout that preserves stable identity. A simple
shape is:

```text
.okf/agent-skills/
  skills/
    revisao-minutas.md
  resources/
    revisao-minutas--references--risco-fatal.md
  evals/
    revisao-minutas--trigger-01.md
```

Prefer a temporary or ignored directory. Version the projection only when reviewing the
projection itself provides value.

## Determinism

For unchanged source files, two projection runs should produce semantically identical OKF.
Sort discovery results and emitted collections. Normalize repository-relative paths to POSIX
form. Never include timestamps, temporary absolute paths, or machine-specific values unless
they are explicitly requested observations.

## Source mapping

Every concept must carry enough information to return from a relational finding to the source
artifact. At minimum this is `source_path` relative to the audited root.

The report should cite the source, not the generated concept path, whenever practical.
