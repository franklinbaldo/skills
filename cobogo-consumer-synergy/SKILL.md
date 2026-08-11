---
name: cobogo-consumer-synergy
description: >-
  Analyze Cobogó's registered consumers as a portfolio, detect reusable needs and duplicated
  solutions across repositories, decide the correct authority for each improvement, and create
  coordinated Cobogó/consumer issues or PRs while keeping adoption evidence factual in OKF.
---

# Coordinate Cobogó across real consumers

Use this skill when working on `franklinbaldo/cobogo` and the next useful design-system move may
come from understanding one or more registered consumers rather than from changing Cobogó in
isolation.

Cobogó is not only a library consumed downstream. It is a knowledge system that should learn
from its consumers, detect synergies among them, upstream reusable design knowledge, and offer
concrete downstream adoption work when a shared capability is ready.

The canonical consumer registry lives in `franklinbaldo/cobogo/knowledge/consumers` and must be
read through the current OKF corpus. Prefer `okf-parser` inventory/graph/query surfaces when
available. Do not treat Astronauta as a mandatory gateway to this knowledge.

## Operating principle

Run a closed evidence loop:

`consumer -> need/local solution -> cross-consumer comparison -> authority decision -> issue/PR -> downstream evidence -> consumer registry update`

A finding is not complete merely because an issue was opened. The Cobogó corpus should remain
capable of telling which consumers need a capability, which actually adopted it, what remains
local, and what evidence supports promoting or rejecting an abstraction.

## 1. Read consumers before inventing roadmap

Start by querying or reading the registered consumer concepts.

For each relevant consumer establish factual state:

- product purpose and real user task;
- adoption status (`candidate`, `evaluating`, `adopting`, `active`, `legacy`, `retired`, or the
  current registry vocabulary);
- surfaces and interaction/density profile;
- runtime/framework constraints;
- accessibility/performance constraints;
- local visual identity that must remain local;
- Cobogó capabilities actually used;
- explicit unmet needs;
- known local duplication or legacy Cobogó-like foundations;
- linked specimens, issues, PRs and adoption evidence;
- last verified revision/date when materially useful.

Do not infer active adoption from the existence of a specimen, design review, issue, or PR.

## 2. Inspect real repositories when the registry points to a need

The registry is an index, not a substitute for brownfield inspection.

When a need, overlap or migration question is material, inspect the consumer repository itself:

- current implementation and architecture docs;
- design tokens/foundations;
- repeated patterns/components;
- active PRs/issues that may already solve the problem;
- accessibility/performance constraints encoded in code or CI;
- product-specific decisions that should not be generalized.

Prefer current source over stale descriptions. If repository state has changed, update the
consumer concept as part of the work.

## 3. Look for synergies, not visual similarity

Candidate synergy signals include:

- two or more consumers report equivalent unmet needs;
- different consumers maintain equivalent semantic token/state roles locally;
- one consumer already solved a problem another consumer has;
- several consumers independently implement the same information relation;
- a Cobogó capability exists but consumers duplicate it locally;
- a consumer-specific solution has enough evidence to become experimental shared knowledge;
- removing/deprecating a Cobogó role would affect multiple consumers;
- a capability has no real consumer evidence and may be speculative.

Do **not** create a shared abstraction merely because two components, CSS files, screenshots or
framework APIs look alike. Name the shared product/design relation and the concrete maintenance
or usability benefit first.

Negative evidence counts: if two consumers intentionally require different solutions, persist
that difference as evidence for `Parentesco sem uniformidade` instead of forcing convergence.

## 4. Decide authority before writing code

### Change Cobogó when

- the capability is reusable across consumer contexts;
- canon/grammar/foundation/pattern semantics are missing;
- compatibility/versioning belongs to the shared design system;
- a local solution should be generalized without carrying product branding or architecture;
- multiple consumers independently exercise the same relation;
- one consumer provides enough evidence for an experimental capability that should be tested
  elsewhere before stabilization.

### Change a consumer when

- the work is adoption/integration;
- local duplication can be removed after Cobogó provides the capability;
- information architecture, brand, copy or domain state is product-specific;
- a released/available Cobogó capability can replace local infrastructure;
- a consumer implementation bypasses an accepted consumer contract;
- a concrete local improvement is useful even if it does not generalize.

### Coordinate multiple repositories when

- a shared capability and its first adoption need to evolve together;
- upstream extraction needs downstream proof;
- a compatibility/migration change has both shared and local parts;
- two consumers should adopt the same semantic relation through distinct presentations.

Do not use consumer repositories as sandboxes for speculative Cobogó experiments.

## 5. Open issues proactively when a decision needs design work

A Cobogó agent may and should open issues in Cobogó or registered consumer repositories when
analysis reveals a concrete next problem.

Every cross-repo issue should state:

- the observed consumer evidence;
- the shared or local problem;
- why this repository is the correct authority;
- links to related consumer/Cobogó concepts or issues;
- the smallest useful acceptance test;
- what remains intentionally out of scope.

Avoid duplicate bookkeeping issues whose only purpose is to mirror another repo's issue. Each
issue must own a real decision or implementation boundary.

## 6. Open PRs when the change is concrete and reviewable

A Cobogó agent may create PRs directly in consumer repositories when:

- the consumer is accessible and policy permits it;
- the desired change is already sufficiently specified by accepted Cobogó knowledge or strong
  brownfield evidence;
- the PR is independently reviewable and reversible;
- product identity is preserved;
- migration can be demonstrated on a real surface;
- tests/accessibility/performance checks appropriate to that repository are included.

Good first PRs are usually additive mappings, one-surface migrations, removal of proven
duplication, or adoption of a stable semantic role/pattern. Avoid whole-site rewrites.

Never merge automatically unless current repository/user policy explicitly permits it.

## 7. Use coordinated extraction/adoption stacks when useful

A strong cross-repo sequence often looks like:

1. consumer evidence or unmet need recorded in Cobogó OKF;
2. Cobogó issue defining the reusable capability;
3. Cobogó PR implementing/documenting the smallest shared capability;
4. consumer PR adopting it on one real surface;
5. comparison against another registered consumer;
6. Cobogó follow-up refining or promoting the capability;
7. registry update marking factual adoption and remaining gaps.

The order may differ when downstream proof must precede upstream generalization. Preserve the
links so the reasoning remains reconstructible.

## 8. Test for parentage without uniformity

For every proposed synergy ask:

- What semantic/visual relation is truly shared?
- What values, density, brand, workflow or information hierarchy must stay consumer-local?
- Could the consumers adopt the same capability and still be obviously different products?
- Does extracting the shared part reduce duplication or improve quality?
- Would a smaller contract accomplish the same goal with less centralization?

If the proposed shared abstraction makes consumers converge visually without a task reason,
reduce the abstraction.

## 9. Promote local knowledge carefully

Before upstreaming a local consumer solution record:

1. the real problem it solves;
2. which part is semantic/reusable rather than product styling;
3. at least one consumer that exercises it;
4. whether another consumer shares or plausibly tests the relation;
5. what remains local after extraction;
6. how downstream adoption will validate it;
7. whether status should be experimental or stable.

One consumer can justify experimentation. Multiple independent consumers are stronger evidence
for stable core.

## 10. Feed outcomes back into OKF

After a cross-repo decision or implementation, update the consumer registry so it remains
factual.

Typical updates:

- remove a resolved item from `unmet_needs` or replace it with the remaining narrower gap;
- add only actually adopted capabilities to `capabilities_used`;
- link adoption PR/evidence/specimen when the corpus convention supports it;
- update adoption status only when the dependency state really changed;
- record negative evidence when a proposed shared solution was rejected as product-specific;
- update `last_verified` when repository facts were rechecked.

Issues and PRs are execution records. The OKF corpus is the reusable knowledge/state model.
Do not let the latter become stale after the former land.

## Examples

### CausaGanha + Astronauta

Both may need dense accessible tabular/status relations. Derive shared semantics/patterns in
Cobogó, but keep different density, interaction and branding. Then create separate adoption PRs
when useful.

### CausaGanha + O Vigia

Both may expose source, freshness and provenance. A shared `Inscrição`/provenance pattern may be
useful even though one is a public data-reading interface and the other is editorial. Do not
force the same visual block.

### Equivalent local foundation roles

If CausaGanha and Astronauta independently have equivalent semantic tokens, upstream the role
only if its meaning generalizes. Keep each consumer's actual values/theme local unless a
Cobogó default theme has separate evidence.

## Guardrails

- Do not equate registry membership with code dependency.
- Do not create cross-repo churn without a named shared benefit.
- Do not force framework changes for design-system adoption.
- Do not move product brand, domain terminology or workflow-specific states into Cobogó merely
  to centralize them.
- Do not duplicate `okf-parser` with a new consumer database, graph, identity or schema engine.
- Do not route agents through Astronauta when direct OKF access is available.
- Do not treat a single successful consumer presentation as a universal template.
- Do not merge downstream changes without explicit permission under the current repo policy.

## Definition of done

Consumer-synergy work is complete when:

1. relevant consumer state was read and, where needed, verified against real repositories;
2. the shared/local relation is explicit;
3. authority for each change is justified;
4. issues/PRs were opened in the smallest appropriate repo boundaries when action is warranted;
5. downstream evidence exists or is explicitly identified as the next validation step;
6. consumer identity remains local;
7. negative evidence is preserved when abstraction does not generalize;
8. the Cobogó consumer registry is updated to reflect factual outcome/adoption state.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any
friction/workaround. Routine success stays ephemeral. If there is actionable learning, search
`franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use
feedback** issue. Never publish secrets, private repository data, credentials, personal data or
confidential material merely to report feedback.
