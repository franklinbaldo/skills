# Frontier scan protocol

Use this reference when turning external literature into a reviewable research-state change.

## Minimal scan header

Record enough context that a future reader can reconstruct what was actually compared.

```yaml
scan_date: YYYY-MM-DD
effective_state:
  default_branch: <branch or commit>
  open_prs: [<pr-or-range>]
  experiment_artifacts: [<paths-or-ids>]
cutoff: YYYY-MM-DD
discovery_surfaces:
  - name: <Kurate/arXiv/conference/citation-trail/etc>
    query_or_filter: <human-readable search/filter>
    methodology_checked: <date/url/commit when ranking affected triage>
primary_sources_checked: <count>
```

The scan date is not the literature cutoff. A source published before the cutoff can still be newly
discovered; record both facts when it matters.

## Effective state for stacked PRs is an overlay, not necessarily the leaf HEAD

Do not assume that the newest-looking or deepest PR contains every correction made earlier in the
stack. An ancestor can move after a descendant was branched, leaving the descendant **behind** while
both PRs remain open and individually valid.

Before freezing claims for a stacked programme:

1. list every live PR that contributes to the programme, with its current head commit and base;
2. compare adjacent stack members or otherwise detect whether an ancestor head changed after the
   descendant's base point;
3. when the same path exists in multiple live PRs, determine which PR currently owns the latest
   applicable version rather than trusting the leaf copy;
4. construct the effective research state as a documented **overlay of live heads**;
5. record stack drift explicitly and, when useful, recommend a later rebase/re-stack as repository
   hygiene — but do not silently substitute stale descendant content for a newer ancestor correction.

The research scan answers "what is the programme currently proposing?", not "what files happen to
exist in one convenient branch?"

A useful state record is:

```yaml
effective_state:
  default_branch: <commit>
  overlays:
    - pr: 101
      head: <commit>
      owns: [paper.md]
    - pr: 102
      head: <commit>
      owns: [experiments/protocol-a.md]
      drift: "descendants still contain the pre-correction copy of protocol-a.md"
    - pr: 103
      head: <commit>
      owns: [experiments/protocol-b.md]
```

If the overlay cannot be reconstructed confidently, mark the affected claim as `state-ambiguous`
and resolve that ambiguity before making a novelty or supersession judgment.

## Step A — freeze the live obligations

Before reading candidates, write a compact ledger:

| ID | Claim / experiment | Status | Novelty boundary | Observable / falsifier | Source location |
| --- | --- | --- | --- | --- | --- |

Use the strongest claim the programme actually makes, not an imagined stronger version.

For stacked PRs, the newest applicable wording controls. Note superseded wording only when it helps
explain why a candidate initially looked like a collision.

## Step B — candidate triage

A ranking/discovery service may prioritize candidates, but semantic relevance to a live obligation
beats rank.

For each candidate ask:

1. What is the strongest result actually established by the primary source?
2. Which live obligation, if any, could it change?
3. Is the overlap conceptual, mechanistic, experimental, empirical, or merely terminological?
4. Does it provide a stronger baseline/control/metric even if it does not threaten novelty?
5. What would have to be true for this source to be irrelevant?

Drop candidates whose connection is only shared vocabulary. Keep a short `orthogonal` record for
nearby work when its exclusion itself is useful evidence.

## Step C — collision record

Use one row/block per material mapping:

```yaml
source: <citation/arXiv/etc>
primary_source_checked: true
live_item: <claim-or-experiment-id>
relation: supports | challenges | supersedes | enables_experiment | orthogonal
source_result: <what the source actually establishes>
collision: <why that result matters to this exact live item>
action: <concrete change, follow-up, or no-action rationale>
confidence: high | medium | low
open_question: <optional>
```

A single source may map differently to multiple live items. Do not force one global verdict per
paper.

## Decision rules

### `supports`

Use only when the source supplies genuinely independent support or a useful method consistent with
the programme. Similar framing alone is not support.

Possible actions:

- related-work addition;
- stronger motivation;
- external validation target;
- replication issue;
- confidence increase without changing the claim.

### `challenges`

Use when the source weakens a claim or exposes a missing baseline/control.

Possible actions:

- narrow or split the claim;
- add a negative control;
- add a stronger baseline;
- open an adversarial critique;
- change a preregistration gate so the challenged mechanism is distinguishable.

### `supersedes`

Reserve for cases where the programme's claimed central contribution is already achieved more
strongly or directly enough that continuing to present it as the same contribution would be
misleading.

Possible actions:

- retire the claim;
- reframe the paper around the remaining distinct contribution;
- run a blank-sheet redesign;
- stop an experiment whose only purpose was to establish the superseded contribution.

### `enables_experiment`

Use when a source contributes a technique, artifact, metric, benchmark, dataset, model, or control
that materially changes experiment quality/cost without itself settling the live claim.

Possible actions:

- add the method as a baseline;
- add a dataset/control;
- reorder experiments because one became cheaper or more diagnostic;
- create a bounded reproduction.

### `orthogonal`

Use for close-looking work that does not materially alter the live obligation after inspection.
State why. This is often valuable negative prior-art evidence.

## Negative scan result

`No material collision found` is acceptable only when accompanied by:

- the live claim/experiment searched;
- cutoff date;
- discovery/search surfaces;
- candidate classes/alternate terminology inspected;
- primary sources actually checked;
- known coverage limitations.

Do not write `no prior art exists`. Write the bounded statement the scan supports, for example:

> No material collision was found for the route-conditioned inverse-atlas claim in the inspected
> retrieval/memory sources through 2026-08-09. This is a search result, not a proof of global
> novelty.

## Suggested reviewer roles

For a batch large enough to benefit from multiple readers, use differentiated roles rather than
asking every reader the same vague question.

### Primary-source factual reader

Return only claims/method/results directly supported by the source, with section/page anchors when
available. Avoid novelty judgment.

### Prior-art collision reviewer

Compare the source against one or more live novelty boundaries. Return the narrowest collision and
what remains distinct.

### Experiment/control reviewer

Ask whether the source supplies a stronger baseline, missing negative control, better observable,
or cheaper replication path.

### Adversarial reviewer

Try to construct the strongest defensible case that the live claim is already known, not identified,
or falsely green. The orchestrator must verify every assertion against the primary source.

### Replication/resource reviewer

Estimate whether a direct reproduction is worth doing, what resources it requires, and what result
would actually update the programme.

## Research-state action table

| Collision | Default destination |
| --- | --- |
| supporting evidence | existing supportive/related-work mechanism |
| adversarial evidence | existing adversarial mechanism |
| experimental method/control | experiment/preregistration issue or PR |
| settled multi-sided conclusion | synthesis/manuscript absorption |
| central contribution superseded | reframe/retire/blank-sheet redesign |
| orthogonal or negative result | scan/audit ledger |

Repository-specific machinery overrides this table when it already defines a clearer destination.

## Quality checks before closing a scan

- Did we accidentally scan a stale branch instead of the effective state?
- In a stacked programme, did an ancestor move after a descendant branched?
- Does the chosen snapshot silently contain an older copy of a claim/protocol than another live PR?
- Did any conclusion come from a ranking/AI summary rather than the primary source?
- Did keyword mismatch cause us to miss a semantic collision?
- Did shared vocabulary get mislabeled as a collision?
- Did a source challenge only an older version of a claim already narrowed in a later PR?
- Did we add a citation without changing any research obligation? If so, was that actually useful?
- Did we preserve negative evidence and search limitations?
- Did the cycle create a stronger next search/control rather than merely exhaust today's candidate list?
