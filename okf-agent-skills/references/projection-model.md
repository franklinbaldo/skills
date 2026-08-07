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

Keep portable Agent Skills fields distinct from Claude Code extensions.

Portable Agent Skills candidates include fields defined by the open specification such as
`name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools` where the
targeted specification version defines it.

Claude Code may add implementation-specific fields such as `when_to_use`, `user-invocable`,
`disable-model-invocation`, `context`, `agent`, `model`, `effort`, `paths`, `hooks`, or other
current extensions. Verify the current Claude Code documentation before treating any such
field as current behavior.

Project fields only when present or when a documented default is material. Preserve whether a
value was authored versus derived when that distinction matters.

Do not copy the whole `SKILL.md` body into frontmatter. The source path is the authority. The
body of a **derived** `Skill` concept may, however, contain translated Markdown links whose
purpose is to materialize source relations inside the derived OKF bundle, as defined below.

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

## Relations are translated into the derived namespace

A link in the source corpus is evidence for a relation, but `okf-parser` cannot graph evidence
that is not present in the bundle it is reading. Therefore the projection MUST materialize
resolved source relations as ordinary Markdown links between the corresponding **derived**
concepts.

For example, if the source contains:

```text
A/SKILL.md -> ../datajud/SKILL.md
```

and those skills project to:

```text
.okf/agent-skills/skills/a.md
.okf/agent-skills/skills/datajud.md
```

then the derived `Skill(A)` body should contain a link equivalent to:

```markdown
Uses [datajud](datajud.md).
```

The exact anchor text is not semantically important; the resolved derived target is. This
gives `okf-parser graph <derived-bundle>` and the bundle's `links` relation an actual edge:

```text
Skill(A) -> Skill(datajud)
```

Do not leave the target as `../datajud/SKILL.md`. That points back into the source corpus,
may escape the derived-bundle root, and defeats the purpose of having a self-contained IR.

### Provenance of a derived edge

Translation changes the link target namespace, not the evidence. Preserve enough provenance
to explain where each edge came from.

At minimum record:

```text
source_path
source_link_target
```

When available deterministically, also retain source line, span, or another stable locator.

The projection may encode provenance in a companion concept/table or in deterministic metadata
associated with the source concept. Do not encode provenance by making the derived edge point
back to the source file: graph identity and provenance are separate concerns.

Conceptually:

```text
source evidence:
A/SKILL.md --../datajud/SKILL.md--> datajud/SKILL.md

compiled relation:
Skill(A) ---------------------------> Skill(datajud)
        provenance: source A + original target
```

### No duplicate dependency declaration

The translation does not justify adding an authored `dependencies:` field to source skills.
The dependency is still derived from the real source link. The projection merely recompiles
that relation into the namespace that `okf-parser` can execute over.

A semantic mention without a link may be reported separately as a candidate relation, but it
must not be silently upgraded to the same certainty as a resolved authored link.

## Physical layout

The projection may use any deterministic layout that preserves stable identity. A simple
shape is:

```text
.okf/agent-skills/
  skills/
    revisao-minutas.md
    datajud.md
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

Derived relation rewriting is part of determinism: the same resolved source target must map
to the same derived concept path on every run.

## Source mapping

Every concept must carry enough information to return from a relational finding to the source
artifact. At minimum this is `source_path` relative to the audited root.

Every derived relation used for dependency analysis must likewise retain enough provenance to
identify the source link that caused it.

The report should cite the source, not the generated concept path, whenever practical.
