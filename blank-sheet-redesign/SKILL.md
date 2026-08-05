---
name: blank-sheet-redesign
description: >-
  Redesign an existing artifact from a blank sheet, by first principles, then reconcile the
  ideal draft against the brownfield constraints of the real system and justify every
  difference. Use whenever the target is an existing artifact that has accreted layers and
  the question is "what should this be?" rather than "what line should I patch?" — CLAUDE.md
  and agent instructions, README and docs, prompts, schemas, config, CI pipelines, module
  boundaries, team process. Triggers on "exercício greenfield", "greenfield exercise",
  "reescreve do zero", "do zero", "blank sheet", "folha em branco", "zero-based",
  "from first principles", "redesenha isso", "start over", "rewrite this file from scratch",
  "esse arquivo virou uma colcha de retalhos", "if we were writing this today". Also use
  when a rewrite is already underway and is about to drop hard-won constraints. Do NOT use
  for genuine greenfield work (nothing exists yet — just design it), for ordinary edits with
  a known target, or for code refactors where behavior must be preserved exactly.
---

# Blank-sheet redesign with brownfield reconciliation

"Greenfield exercise" is an informal name. The precise one: **blank-sheet (zero-based)
redesign, driven by first principles, reconciled against brownfield constraints.** The
repository is not greenfield. What you run is a *counterfactual*:

> Suppose the system exists exactly as it is, but this artifact had never been written.
> What would we write?

That suspends the **current form of the solution** — not the knowledge available. You may
read the repo, the specs, the workflows, the history. You may not use the old artifact as
the template you edit.

## Why not just edit

Editing anchors you. The first question becomes "what do we keep?", which silently ratifies
every past decision, including the ones nobody would make again. The blank sheet forces the
right first question: *what does the reader/agent actually need in order to do the job?*

## Why not just rewrite

A naive blank sheet deletes constraints the system learned painfully. Real examples from a
`CLAUDE.md` this technique was applied to: regex producing fabricated legal citations;
sentinel dates treated as real dates; derived artifacts drifting out of sync with sources;
audit confused with institutional approval. That knowledge is load-bearing. The move is not
to ignore it — it is to separate three things:

1. the permanent principle that was learned;
2. where that principle belongs (this artifact? a lint rule? a test? a spec?);
3. whether the full incident narrative needs to be re-read in every session.

**The technique is: design from zero, confront reality, justify each difference.**

## Procedure

### 1. State the purpose — before opening the old file

Write one sentence: *"This artifact exists so that X can do Y without doing Z."*

> "`CLAUDE.md` exists so agents work with technical and legal autonomy, preserving
> traceability, without fabricating institutional acts."

If you cannot write this sentence, stop and find out. Everything downstream is scored
against it.

### 2. List the real constraints

Only constraints that follow from: the domain; decisions currently in force; the artifact's
consumers; security; institutional authority; failure modes already demonstrated in
practice. "It has always been this way" is not a constraint. Note which constraints you
learned from the *incident history* rather than from the domain — those are the ones step 4
will fight over.

### 3. Draft the ideal

Write v-ideal without consulting the old artifact as a model. Consult everything else.
Write it whole — a sketch cannot be reconciled.

### 4. Diff ideal vs. existing, and classify every difference

Go difference by difference. Each one lands in exactly one bucket:

| Bucket | Meaning | Action |
| --- | --- | --- |
| Ideal forgot a real constraint | The blank sheet was naive | Restore it — restate as a principle, not as a scar |
| Existing carries necessary knowledge | Load-bearing, correctly placed | Keep, tighten the wording |
| Existing is only history | True but no longer actionable | Move to a changelog / ADR / incident log |
| Existing duplicates another source | Spec, test, and prose disagree eventually | Delete here, point at the source |
| Existing preserves a superseded decision | Ratified by inertia | Drop, and say so in the commit |
| Ideal is a genuine improvement | New structure, clearer contract | Adopt |

The classification *is* the work. An unclassified difference means you do not yet understand
the system.

### 5. Reconcile — produce a third version

Do not ship v-ideal, and do not ship v-existing. Ship v3, informed by both. Every deletion
should be traceable to a bucket above; if you cannot name the bucket, you are guessing.

### 6. Test against concrete tasks

Walk real tasks through v3 and check it actually answers:

- Can the reader do the central job the artifact exists for?
- Do they know which files to edit and which are generated?
- Do they know how to validate that the work is done?
- Can they tell analysis from approval, proposal from decision?
- Does any rule block legitimate initiative?
- Does any omission leave a material risk invisible?

If v3 fails a task, that failure is a missing constraint — back to step 2, not to prose
polish.

### 7. Ship it as a diff people can review

Present v3 with the classification table for the non-obvious differences. Reviewers should
be able to argue with a bucket assignment, which is much cheaper than arguing with a
2000-line rewrite.

## Failure modes

- **Peeking.** Reading the old file "just to warm up" in step 3 collapses the exercise into
  an edit. If you have already read it, wait — or hand step 3 to a subagent that has not.
- **Nostalgia buckets.** Everything classified as "necessary knowledge." If nothing lands in
  *history* or *superseded*, you did not really diff.
- **Vandalism buckets.** Everything classified as "only history." Ask what incident produced
  each rule before deleting it.
- **Rewriting behavior instead of the artifact.** This technique redesigns *descriptions,
  contracts, and structure*. When the target is running code whose behavior must be
  preserved, characterize first (Feathers) and evolve incrementally (Ford et al.) — do not
  swap in a from-scratch implementation.
- **Big-bang delivery.** A correct v3 that lands as one unreviewable commit will be reverted
  or, worse, ignored.

## Lineage

- McKinsey, *Org redesign: start with a blank page* — the short, clear statement of
  zero-based / blank-sheet design.
- Hammer & Champy, *Reengineering the Corporation* — the classic radical-redesign method:
  understand the existing process, design and prototype the new one, then implement. Source
  of the sharpest framing question: *are we improving the right process, or making a
  structure that should not exist more efficient?*
- Azure Well-Architected and AWS Prescriptive Guidance — the technical greenfield/brownfield
  distinction (greenfield = no existing infrastructure, free technology choice, no legacy
  compatibility constraints).
- Feathers, *Working Effectively with Legacy Code* — how to change an existing system
  without destroying the knowledge and behavior it carries.
- Ford, Parsons, Kua & Sadalage, *Building Evolutionary Architectures* — turning the ideal
  design into incremental evolution instead of a total rewrite.

## Saying it precisely

Instead of "let's do a greenfield exercise":

> "Let's do a blank-sheet redesign, driven by first principles, and then reconcile it against
> the brownfield constraints of the repo."
