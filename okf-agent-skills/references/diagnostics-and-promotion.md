# Diagnostics and promotion boundary

The integration is useful only if it resists two opposite mistakes:

1. turning every measurable property into a lint error;
2. moving Agent-Skills-specific behavior into `okf-parser` core before the abstraction is proven.

## Diagnostics should be relational, narrow, and sourced

Prefer checks that can state exactly which observed facts produced the finding.

Examples:

```sql
-- Large entry points: advisory, threshold verified against current guidance.
SELECT name, line_count
FROM Skill
WHERE line_count > 500
ORDER BY line_count DESC;
```

```sql
-- Architecture information, not a defect.
SELECT target_skill, count(*) AS dependents
FROM SkillLink
WHERE resolved
GROUP BY target_skill
ORDER BY dependents DESC;
```

```sql
-- Potentially orphaned scripts: advisory until repository semantics are checked.
SELECT r.skill, r.source_path
FROM SkillResource r
LEFT JOIN SkillLink l ON l.target = r.source_path
WHERE r.kind = 'script'
  AND l.target IS NULL;
```

Adapt table names to the actual relational projection produced by the current `okf-parser`
surface. Do not pretend illustrative SQL is a stable package API.

## Facts versus heuristics

Good deterministic facts:

- file exists;
- frontmatter value is authored;
- line count is N;
- link resolves or does not resolve under the selected root;
- graph has a cycle;
- an eval concept exists;
- a script is reachable by an authored Markdown link.

Heuristics that need explicit labeling:

- two descriptions overlap semantically;
- a skill is too broad;
- a reference is unnecessary;
- a dependency hub should be split;
- a tool permission is excessive;
- a prose mention probably refers to another skill.

Use the relational layer to select candidates for model judgment; do not make SQL impersonate
semantic review.

## Promotion ladder

When the integration repeats work, use this order.

### 1. Keep it in `SKILL.md`

Use prose when the work is judgment, sequencing, source selection, or deciding which generic
surface fits the current task.

### 2. Add a bundled helper

Use a script when the step is mechanical and benefits from reproducibility, for example:

- deterministic discovery of skill roots;
- stable path normalization;
- frontmatter projection;
- resource enumeration;
- repeatable generation of derived OKF files.

The script belongs beside this skill first because Agent-Skills-specific knowledge still
belongs to the integration.

### 3. Propose a generic `okf-parser` primitive

Promote behavior when evidence shows a reusable abstraction beyond this domain, such as:

- generic projection of external Markdown collections;
- reusable source-to-derived provenance mapping;
- a generic relation needed by several profiles;
- parser internals that no public surface can express safely.

Prefer this over a named `agent-skills` special case.

### 4. Propose Agent-Skills-specific native support only with stronger evidence

A native feature is justified only when repeated use shows that domain-specific behavior is
both stable and materially better in core. Useful evidence includes:

- independent consumers reimplementing the same transformation;
- unacceptable performance from external projection;
- correctness depending on parser internals;
- filesystem identity/round-trip guarantees that a helper cannot provide;
- a stable upstream format whose maintenance cost is now lower in core.

“An agent would like this command” is not sufficient.

## What not to promote

Keep these out of core unless a separate generic abstraction appears:

- current Claude Code routing advice;
- model-specific eval heuristics;
- editorial judgments about skill quality;
- repository-specific security policy;
- local naming conventions;
- recommendations that change frequently upstream.

These belong in the skill or its references because they can evolve without a package release.

## Reporting a proposed core change

Any recommendation to modify `okf-parser` should include:

1. the repeated workflow observed;
2. why current generic surfaces plus a bundled helper are insufficient;
3. the smallest generic primitive that would solve it;
4. at least one non-Agent-Skills use case if claiming the primitive is generic;
5. compatibility and trust-model consequences;
6. what remains in the skill after promotion.

This keeps the skill as the domain adapter even when the engine gains a new primitive.
