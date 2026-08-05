---
name: blank-sheet-redesign
description: >-
  Redesign an existing, accreted artifact by drafting it counterfactually — as if it had
  never been written — and then reconciling that draft against the real constraints of the
  system, justifying every difference. Use when the question is "what should this artifact
  be?" rather than "what line do I patch?": CLAUDE.md and agent instructions, docs, prompts,
  schemas, module boundaries, and equally non-software artifacts such as a teoria do caso,
  a tese ou modelo de peça do setor, ato normativo, edital, or an institutional workflow.
  Also use when a rewrite is already underway and is about to discard hard-won constraints.
  Do NOT use for genuine greenfield work, for ordinary edits with a known target, or for
  code refactors that must preserve behavior exactly.
---

# Blank-sheet redesign with brownfield reconciliation

Working name used in this skill. It is not a canonical external methodology: it combines
blank-sheet / zero-based redesign, first-principles reasoning, Business Process
Reengineering, and brownfield/legacy practice into the specific seven-step procedure below.
"Greenfield exercise" is the informal shorthand; the system is not greenfield, so what you
actually run is a *counterfactual*:

> Suppose the system exists exactly as it is, but this artifact had never been written.
> What would we write?

That suspends the **current form of the solution** — not the knowledge available. Read the
repo, the specs, the record, the history. Do not use the old artifact as the template you
edit.

Rationale, and why neither plain editing nor plain rewriting gets here, is in
`references/fundamentos.md` — read it when you need to justify the technique or trace its
lineage, not to run it.

## Procedure

### 1. State the purpose — before opening the old artifact

Write one sentence: *"This artifact exists so that X can do Y without doing Z."*

> "`CLAUDE.md` exists so agents work with technical and legal autonomy, preserving
> traceability, without fabricating institutional acts."

If you cannot write this sentence, stop and find out. Everything downstream is scored
against it.

### 2. List the real constraints

Only constraints that follow from: the domain; decisions currently in force; the artifact's
consumers; security; institutional authority; failure modes already demonstrated in
practice. "It has always been this way" is not a constraint. Mark which constraints you
learned from *incident history* rather than from the domain — those are what step 4 fights
over.

### 3. Draft the ideal

Write v-ideal without using the old artifact as a model. Consult everything else. Write it
whole — a sketch cannot be reconciled.

**If you have already read the old artifact** (likely, since this skill is also for rewrites
already underway), you are anchored and waiting does not fix it. Do one of these instead:

- **Preferred:** delegate step 3 to a subagent in a fresh context. Give it the purpose
  sentence and the constraint list from steps 1–2 — never the old text. Its draft is v-ideal.
- **No isolation available:** declare the anchoring risk explicitly, then run a deliberate
  counterfactual pass — derive each section from the purpose and constraints alone, and for
  every element that survives, state which constraint requires it. Anything you keep only
  because it was there gets marked as unjustified and goes to step 4 as a candidate cut.

### 4. Diff ideal vs. existing, and classify every difference

Give each difference **one primary bucket** — the one that drives the action — plus any
secondary observations. A difference can both duplicate another source and preserve a
superseded decision; the primary bucket decides what you do, the secondary note survives
into the review so nobody has to rediscover it.

| Bucket | Meaning | Action |
| --- | --- | --- |
| Ideal forgot a real constraint | The blank sheet was naive | Restore it — restate as a principle, not as a scar |
| Existing carries necessary knowledge | Load-bearing, correctly placed | Keep, tighten the wording |
| Existing is only history | True but no longer actionable | Move to a changelog / ADR / incident log |
| Existing duplicates another source | Spec, test, and prose disagree eventually | Delete here, point at the source |
| Existing preserves a superseded decision | Ratified by inertia | Drop, and say so in the commit |
| Existing is not available to change | Fixed by authority, contract, or a consumed procedural step | Keep, and record *why* so the next reader sees a reason, not laziness |
| Ideal is a genuine improvement | New structure, clearer contract | Adopt |

The classification *is* the work. An unclassified difference means you do not yet understand
the system.

### 5. Reconcile — produce a third version

Do not ship v-ideal, and do not ship v-existing. Ship v3, informed by both. Every deletion
should be traceable to a bucket; if you cannot name the bucket, you are guessing.

### 6. Test against concrete tasks

Walk real tasks through v3 and check it actually answers:

- Can the reader do the central job the artifact exists for?
- Do they know which files are sources and which are derived?
- Do they know how to validate that the work is done?
- Can they tell analysis from approval, proposal from decision?
- Does any rule block legitimate initiative?
- Does any omission leave a material risk invisible?

If v3 fails a task, that is a missing constraint — back to step 2, not to prose polish.

### 7. Ship it as a diff people can review

Present v3 with the classification for the non-obvious differences. Reviewers should be able
to argue with a bucket assignment, which is far cheaper than arguing with a 2000-line
rewrite.

## Failure modes

- **Peeking.** Reading the old artifact "just to warm up" in step 3 collapses the exercise
  into an edit. Use the step-3 fallback above; waiting is not a remedy.
- **Nostalgia buckets.** Everything classified as "necessary knowledge." If nothing lands in
  *history* or *superseded*, you did not really diff.
- **Vandalism buckets.** Everything classified as "only history." Ask what incident produced
  each rule before deleting it.
- **Rewriting behavior instead of the artifact.** This technique redesigns *descriptions,
  contracts, and structure*. When the target is running code whose behavior must be
  preserved, characterize first and evolve incrementally — do not swap in a from-scratch
  implementation.
- **Big-bang delivery.** A correct v3 that lands as one unreviewable commit gets reverted
  or, worse, ignored.

## Non-software artifacts

The technique applies wherever an artifact accreted and its current form became a premise:
legal strategy, normative acts, contract templates, institutional workflows, public policy,
org charts, curricula.

What changes across domains is not whether the blank sheet may *examine* a constraint — it
always may, and can redesign around any of them — but how legally or institutionally
**available** each constraint is to be replaced. Law is where that gradient is steepest and
getting it wrong is most expensive.

For legal work, read `references/estrategia-juridica.md` before starting: it replaces the
single "not available to change" bucket with a five-class gradient of availability, adapts
the step-6 tests, and states the non-negotiables (never cite an unverified precedent, never
describe a fabricated institutional act, never let analysis pass for approval).

## Saying it precisely

Instead of "let's do a greenfield exercise":

> "Let's do a blank-sheet redesign, driven by first principles, and then reconcile it against
> the brownfield constraints of the repo."
