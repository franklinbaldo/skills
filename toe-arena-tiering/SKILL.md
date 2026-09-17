---
name: toe-arena-tiering
description: >-
  Evaluate, compare, clash, and tier candidate theories of everything or adjacent
  fundamental-physics frameworks for the ToE Arena. Use when cataloguing a new theory,
  comparing it with existing contenders, deciding whether its tier should move, or
  producing an evidence-backed arena entry. Keep scientific strength separate from
  novelty/interest and never treat a tier as truth.
---

# ToE Arena tiering

The ToE Arena is a living comparative catalogue, not a truth machine. Its job is to make
competing claims legible, auditable, and fun to compare without laundering speculation into
consensus.

## Output contract

For every theory, produce:

- `slug`, canonical name, authors/origin, first-publication date, and source URLs;
- a one-paragraph statement of what the theory actually claims;
- scope: which interactions/problems it attempts to unify or explain;
- strongest evidence **for** it;
- strongest evidence **against / unresolved**;
- distinctive predictions or discriminating tests, if any;
- relationship to established theories and observations;
- `scientific_tier`: S/A/B/C/D/F;
- `interest_tier`: S/A/B/C/D/F;
- confidence in the placement: low/medium/high;
- explicit reasons for placement and for any movement since the previous evaluation;
- at least one meaningful clash against an existing Arena entry.

Never collapse `scientific_tier` and `interest_tier` into one score.

## Scientific tier rubric

The letters are comparative shorthand for the Arena and must be justified in prose.

- **S — benchmark contender**: unusually broad unifying scope with deep mathematical
  development and substantial contact with established physics; still not labelled proven.
- **A — mature research programme**: technically developed, actively testable or constrained,
  and connected to known physics, but with major open empirical or conceptual gaps.
- **B — serious contender**: coherent and non-trivial, with peer/preprint literature and
  identifiable tests or derivations, but materially less mature or less comprehensive.
- **C — structured speculation**: a concrete mathematical proposal with meaningful internal
  structure, but weak empirical contact, missing derivations, or limited independent uptake.
- **D — early hypothesis**: interesting idea with substantial missing formalism, validation,
  or connection to known results.
- **F — presently non-viable**: contradicted by strong evidence, internally inconsistent as
  presented, unfalsifiable in the relevant form, or not developed enough to count as a
  scientific theory. Explain which condition applies.

Tier placement is not a popularity contest. Do not reward branding as a “Theory of
Everything”. Do not punish a framework merely for being new.

## Evidence dimensions

Evaluate qualitatively, citing concrete evidence:

1. **Scope** — gravity + Standard Model? cosmology? quantum foundations? merely one sector?
2. **Internal coherence** — mathematical definition, anomaly/control issues, well-posedness.
3. **Recovery** — ability to reproduce established low-energy/large-scale physics.
4. **Explanatory compression** — whether assumptions actually replace rather than rename
   unexplained structure.
5. **Novel predictions** — predictions not inserted after the fact.
6. **Empirical contact** — existing tests, constraints, observations, simulations.
7. **Falsifiability / discrimination** — what result would move the theory down?
8. **Technical maturity** — solved toy models, calculations, numerical machinery, literature.
9. **Independent scrutiny** — meaningful work by people other than the originator.
10. **Open problems** — unresolved issues severe enough to block the programme's central claim.

Do not turn these into a fake-precision numerical average unless an Arena schema explicitly
requests numbers. Evidence and uncertainty matter more than arithmetic.

## Interest tier rubric

`interest_tier` answers a different question: how generative is this theory for thought,
experiments, visualisation, or surprising connections? A scientifically weak but unusually
fruitful idea can be high-interest. Say why.

## Clash protocol

A clash is not “which theory wins?” in the abstract. Pick one discriminating battleground,
for example:

- UV completion / renormalisation;
- background independence;
- recovery of GR;
- matter and Standard Model incorporation;
- black-hole entropy;
- cosmological predictions;
- experimentally accessible signatures;
- number of free assumptions;
- mathematical completeness.

For theories A and B:

1. state the battleground;
2. state A's concrete advantage and liability;
3. state B's concrete advantage and liability;
4. identify observations/calculations that could change the comparison;
5. record whether the clash warrants a tier movement. Usually it does not.

## Freshness and provenance

For claims about current status, search current primary sources first: original papers,
arXiv records, collaboration/project pages, experiment results, or review literature. Record
publication/update dates. Secondary summaries may help discovery but cannot be the only basis
for a tier move.

A new paper does not automatically move a theory. Promotion/relegation requires a material
change: new empirical evidence, a solved blocking problem, a newly demonstrated contradiction,
a significant independent replication/calculation, or a substantial expansion/retraction of
scope.

## Self-authored theories

The Arena may include theories from `franklinbaldo/papers`. Apply exactly the same rubric and
provenance requirements. Do not give them bonus points for being local. Label self-authored,
unpublished, unreviewed, or exploratory status plainly when applicable.

## Tone

The public Arena can be playful — clashes, promotions, relegations, belts, seasons — while the
scientific record underneath stays sober. Attack claims, not people. Make uncertainty visible.
