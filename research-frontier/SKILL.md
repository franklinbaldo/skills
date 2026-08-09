---
name: research-frontier
description: >-
  Keep an active research programme synchronized with the external scientific frontier by
  comparing current literature against live claims, experiments, controls, baselines and
  novelty boundaries across main and open PR stacks. Use when checking whether a paper or
  research programme is still cutting-edge, running a frontier/prior-art scan, deciding what
  recent work changes an active manuscript, or turning new literature into concrete research
  actions. Do not use for generic paper search, one-off paper summarization, bibliography
  collection, or purely internal software review with no external research question.
---

# Keep the research state, not the bibliography, close to the frontier

The unit of work is a **live claim or experiment**. Literature discovery is useful only when it
changes what the research programme should believe, test, narrow, defend, or stop claiming.

The default loop is:

```text
effective research state
→ live claims / experiments / novelty boundaries
→ external discovery and prioritization
→ primary-source reading
→ claim collisions
→ research consequences
→ updated experiment / debate / synthesis / manuscript
→ harder next frontier
```

A scan that finds no material collision can be a valid result. Never manufacture a paper change
merely to make the scan look productive.

## 1. Reconstruct the effective research state

Do not assume the default branch is current.

Before searching literature, identify the state that a researcher would actually review now:

- default branch;
- open manuscript PRs;
- stacked ancestors/descendants that materially change the same research programme;
- preregistrations and experiment code;
- current protocols, audits, debate artifacts and result artifacts;
- explicit unresolved issues or claim boundaries.

For a stacked programme, record the relevant PR chain or immutable commits. If a later PR narrows
a claim made by an earlier manuscript, scan the narrowed claim rather than attacking a stale
version.

## 2. Build a live-claim ledger before discovery

Extract the smallest useful set of research obligations. For each item record:

```text
claim_or_experiment_id
statement
status: hypothesis | preregistered | measured | falsified | retired
novelty_boundary
required_evidence
known_baselines_or_controls
source_location
```

Prefer explicit claim boundaries already written by the programme. Do not infer a stronger claim
for the purpose of finding a collision.

For experimental programmes, use the same discipline as software review:

```text
claim
→ operationalization
→ experiment
→ observable gate
→ baseline/control
→ falsification state
```

A proxy that cannot distinguish the claimed mechanism is a false green.

## 3. Discover broadly, prioritize narrowly

Use current discovery surfaces appropriate to the field: arXiv/category feeds, Kurate or similar
ranking layers, conference proceedings, primary research indexes, citation trails, and direct
search.

Discovery/ranking systems are **prioritization signals only**. Their ranking, rating, AI summary or
pairwise judgment is not evidence for changing the research programme.

When using a ranking service:

- record the date and relevant methodology snapshot if its scoring affects prioritization;
- avoid hard-coding today's categories, models or score definitions into this skill;
- use rankings to decide what deserves inspection, not what is true;
- include lower-ranked or unranked work when semantic relevance to a live claim is high.

Search at the claim level, not only by manuscript title or keywords. Query neighboring terminology,
mechanisms, negative results, baselines and alternate formulations that could collide without using
the same vocabulary.

## 4. Read primary sources semantically

Any material consequence requires inspection of the primary source: paper/preprint, official code,
dataset, theorem artifact, or other first-party research artifact as appropriate.

Do not conclude novelty from keyword absence. Determine what the source actually claims and what its
method demonstrates.

For a human-scale batch of papers, when the host can spawn subagents, compose with
[`../llm-work-via-subagents/SKILL.md`](../llm-work-via-subagents/SKILL.md):

- shard papers across readers for factual summaries; and/or
- use differentiated roles to decorrelate errors, for example:
  - prior-art/novelty reviewer;
  - experimental-controls reviewer;
  - adversarial claim reviewer;
  - replication/resource reviewer.

The orchestrator merges structured findings and resolves conflicts against the primary source.
Do not replace this with a scripted LLM API loop for an interactive human-scale scan.

## 5. Produce claim collisions, not paper summaries

For every inspected source that survives triage, record:

```text
external_source
primary_source_checked: yes | no
live_claim_or_experiment
relation: supports | challenges | supersedes | enables_experiment | orthogonal
what_the_source_actually_establishes
why_it_matters_here
required_action
confidence_or_open_question
```

Interpret relations conservatively:

- **supports** — independent evidence or method strengthens a live claim without making it redundant;
- **challenges** — evidence, method or result weakens the claim, mechanism, baseline or interpretation;
- **supersedes** — the programme's central contribution is already achieved more strongly enough that
  novelty or purpose must be redefined;
- **enables_experiment** — provides a method, dataset, control, metric or implementation that makes a
  registered test materially stronger or cheaper;
- **orthogonal** — nearby work that does not materially change a live obligation.

`orthogonal` and `no material collision found` are first-class negative evidence when the search
surface and cutoff are recorded.

Read [`references/frontier-scan.md`](references/frontier-scan.md) for the scan template and decision
rules.

## 6. Route consequences into the programme's existing machinery

Prefer existing research mechanisms over a parallel frontier subsystem.

Typical routing:

```text
supports           → supportive evidence / related-work update / stronger baseline confidence
challenges         → adversarial critique / claim narrowing / new control
supersedes         → manuscript reframe, retirement, or blank-sheet redesign
enables_experiment → preregistration or experiment issue/PR
orthogonal         → scan ledger only
```

If the repository already has adversarial/supportive/synthesis roles, use them. If it already has
an audit-report type, use that before inventing a `Frontier Scan` ontology type.

Use [`../software-review/SKILL.md`](../software-review/SKILL.md) when a frontier consequence changes
an implementation, preregistration gate or experimental mechanism and the resulting PR/RFC needs a
correctness review.

Use [`../blank-sheet-redesign/SKILL.md`](../blank-sheet-redesign/SKILL.md) when accumulated frontier
evidence suggests the right question is no longer "how do we patch this paper?" but "knowing what
we know now, what paper would we write if this one had never existed?"

Use [`../free-gpu/SKILL.md`](../free-gpu/SKILL.md) when the highest-value consequence is a bounded GPU
experiment that can be executed on Colab/Kaggle.

## 7. Measure research movement, not bibliography growth

Useful scan outcomes include:

- claims narrowed, split, retired or strengthened;
- prior-art boundaries made more precise;
- new baselines or negative controls;
- experiments added, reordered or made cheaper;
- false-green gates removed;
- external results reproduced or deliberately not reproduced with a reason;
- unresolved collisions escalated to debate/synthesis;
- negative frontier coverage recorded with cutoff and search surface.

Do not optimize for papers found, citations added, or novelty scores.

For recurring use, track metrics such as:

- live claims with a current external scan;
- material claim collisions per cycle;
- source-to-action conversion rate;
- time from relevant source appearance to programme absorption;
- experiments/baselines/controls changed by frontier evidence;
- claims narrowed/retracted after external evidence;
- explicit negative-result coverage;
- stale active PRs whose literature boundary has not been refreshed.

A cycle may look "worse" after stronger literature is discovered. That is scientific progress, not
a failed benchmark.

## 8. Evolve the frontier itself

Compose with [`../loop-engineering/SKILL.md`](../loop-engineering/SKILL.md) after each substantial
cycle. Ask:

1. Which kind of external work did the current scan fail to notice until late?
2. Which claim was hard to map to literature and why?
3. Which ranking/search surface produced noise or blind spots?
4. What new control, negative query, field source or reviewer role would expose a failure that the
   current protocol cannot see?
5. Does a recurring neighboring capability justify another skill, or is it merely a workflow branch?

The next frontier must be capable of finding something the current one could not.

## Guardrails

- Do not use a ranking score as scientific evidence.
- Do not mutate a paper from an AI-generated summary without checking the primary source.
- Do not treat a missing keyword as evidence that prior art is absent.
- Do not scan only `main` when active PRs contain research-state changes.
- Do not strengthen a source's conclusion beyond what its evidence supports.
- Do not confuse relatedness with collision.
- Do not force every source into `supports` or `challenges`; `orthogonal` is valid.
- Do not force a manuscript change when the scan result is negative.
- Do not create a new ontology/runtime/database merely to store a first scan if existing repository
  primitives can represent it.

## Definition of done for one frontier cycle

A cycle is complete when:

- the effective research state and cutoff are recorded;
- live claims/experiments were reconstructed before literature triage;
- discovery sources and search surfaces are identifiable;
- every material consequence is grounded in a checked primary source;
- selected sources are mapped to explicit live claims or experiments;
- negative findings are preserved rather than discarded;
- each material collision has a concrete research action or an explicit reason for no action;
- consequences are routed through existing research machinery when available;
- the scan produced at least one harder question/search/control for the next cycle;
- no novelty claim rests solely on keyword absence or ranking output.
