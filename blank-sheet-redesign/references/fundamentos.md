# Fundamentos: why the counterfactual, and where it comes from

Read this to justify the technique or trace its lineage. Running the procedure does not
require it.

## Why not just edit

Editing anchors you. The first question becomes "what do we keep?", which silently ratifies
every past decision, including the ones nobody would make again. The blank sheet forces the
right first question: *what does the reader actually need in order to do the job?*

## Why not just rewrite

A naive blank sheet deletes constraints the system learned painfully. Real examples from a
`CLAUDE.md` this technique was applied to: regex producing fabricated legal citations;
sentinel dates treated as real dates; derived artifacts drifting out of sync with their
sources; audit confused with institutional approval. That knowledge is load-bearing. The
move is not to ignore it — it is to separate three things:

1. the permanent principle that was learned;
2. where that principle belongs (this artifact? a lint rule? a test? a spec?);
3. whether the full incident narrative needs to be re-read in every session.

**Hence: design from zero, confront reality, justify each difference.**

## What this skill is, in relation to what already exists

The seven-step procedure in `SKILL.md` is an operationalization adopted here, not a canonical
external method. It borrows from:

- **McKinsey, *Org redesign: start with a blank page*** — the short, clear statement of
  zero-based / blank-sheet design: imagine how the organization would be built from scratch
  instead of modifying its current shape.
- **Hammer & Champy, *Reengineering the Corporation*** — the classic radical-redesign method:
  understand the existing process, design and prototype the new one, then implement. Source
  of the sharpest framing question: *are we improving the right process, or making a
  structure that should not exist more efficient?*
- **First-principles reasoning** — decompose to fundamental needs and rebuild from them
  rather than reasoning by analogy with what exists.
- **Azure Well-Architected and AWS Prescriptive Guidance** — the technical
  greenfield/brownfield distinction (greenfield = no existing infrastructure, free technology
  choice, no legacy-compatibility constraints). Useful mainly to see that the repo is *not*
  greenfield, which is what makes reconciliation necessary.
- **Feathers, *Working Effectively with Legacy Code*** — how to change an existing system
  without destroying the knowledge and behavior it carries. The counterweight to the blank
  sheet.
- **Ford, Parsons, Kua & Sadalage, *Building Evolutionary Architectures*** — turning an ideal
  design into incremental evolution instead of a total rewrite.

What is specific to this skill is the combination: the counterfactual framing, the
classification of every difference into buckets, and the insistence on a third version
rather than a swap.
