# Evolution loop

This reference defines the system-level intent behind `loop-engineering`: make skills and their evaluation machinery co-evolve instead of optimizing a static artifact against a static test suite.

## The loop has four simultaneous products

Each cycle should leave behind four things:

1. a better-behaved skill or skill set;
2. a stronger benchmark corpus;
3. a more revealing evaluation method when the old method is saturated or blind;
4. a map of lateral opportunities for new skills, splits, handoffs or compositions.

If only the first product changes, the loop is likely overfitting.

## Vertical evolution

Vertical evolution improves the capability already named by a skill. It includes trigger calibration, workflow refinement, references, tools, output contracts and quality criteria.

Use vertical evolution while these remain true:

- one sentence still describes the skill's job accurately;
- the same users/intents benefit from the capability;
- the same evidence and definition of done largely apply;
- new branches do not require a meaningfully different routing decision.

## Lateral evolution

Lateral evolution discovers a new capability adjacent to the current one. It may emerge from failures, near misses, repeated handoffs, collisions or unexpected successful uses.

A lateral candidate is stronger when:

- it recurs across independent tasks;
- the current skill should often *not* trigger for it;
- it has a distinct success criterion;
- it uses different evidence/tools or a different workflow;
- naming it would make routing boundaries clearer rather than blurrier.

Do not require a skill hierarchy. Sibling skills may compose through explicit links/instructions and ordinary agent routing.

## Pollination

Pollination means one skill creates useful pressure or input for another without merging their responsibilities.

Examples:

- `software-review` repeatedly discovers that a class of architectural redesign deserves a dedicated skill;
- `revisao-minutas` routes evidence gathering to `notebooklm-processos` and later resumes review;
- a quality benchmark discovers a reusable adversarial-checking method that becomes its own skill;
- a routing collision reveals a missing intermediate skill with a narrower contract than either neighbor.

Pollination should produce explicit evidence: links, routing evals, composition cases or workflow references. Avoid a hidden web of implied dependencies.

## Benchmark evolution

A benchmark has its own lifecycle:

```text
regression corpus
→ challenge frontier
→ failure discovery
→ candidate change
→ held-out validation
→ promote useful cases
→ invent next frontier/method
```

The frontier should be generated from multiple sources:

- observed false positives/negatives;
- unstable real runs;
- successful cases that have become trivial;
- cross-skill semantic neighborhoods;
- mutations of descriptions/instructions;
- realistic user-history continuations;
- deliberately perturbed catalogs;
- model/host disagreements;
- output-quality disagreements;
- human discoveries of missing capabilities.

## Innovation backlog

Do not canonize this list. It exists to seed new methods, not bound them.

### Routing

- **catalog perturbation** — add/remove irrelevant and competing skills and measure routing invariance/explainable change;
- **mutation testing** — deliberately weaken/broaden a description and measure whether evals detect degradation;
- **ambiguity gradient** — create a sequence from obvious positive through ambiguous to obvious negative and inspect the boundary;
- **multi-turn routing** — evaluate follow-ups where intent is only recoverable from preceding turns;
- **counterfactual catalog** — compare behavior when the best skill is absent and inspect fallback behavior;
- **cross-host/model matrix** — separate skill quality from host/model routing behavior;
- **calibration** — when supported, compare confidence/uncertainty to actual routing correctness.

### Output quality

- blind pairwise skill-vs-no-skill judging;
- current-vs-previous skill version comparisons;
- rubric dimensions instead of one total score;
- adversarial judges tasked to find regressions;
- metamorphic tests where irrelevant wording changes should not alter quality materially;
- task transformations where core intent is preserved across language/register/format.

### Skill-system evolution

- **split test** — compare one broad skill against two proposed siblings on routing + quality;
- **handoff test** — measure whether composed skills outperform either skill alone on a naturally multi-stage task;
- **coverage mining** — cluster repeated near-misses/unhandled tasks to propose candidate skills;
- **collision mining** — find pairs of skills whose descriptions overlap and create tests at their semantic boundary;
- **orphan detection** — find high-value recurring tasks with no plausible skill candidate.

## Split/create decision

Before creating a skill, compare these options:

```text
A. improve existing skill
B. add a branch/reference inside it
C. create a sibling skill
D. define an explicit handoff/composition
E. do nothing yet; collect more evidence
```

Prefer the smallest option that produces a clean semantic contract. New skills are justified by distinct purpose and routing, not by organizational neatness.

## System health

A healthy loop should make some old metrics harder to interpret because the evaluation surface keeps improving. Record benchmark-version context when comparing scores over time.

Useful system-level measures include:

- number and share of skills with routing eval coverage;
- number and share with quality eval coverage;
- challenge-frontier size;
- hard-negative/collision density;
- mutation kill rate;
- catalog perturbation stability;
- real-run variance by host/model;
- number of active benchmark methodologies;
- number of blind spots newly discovered per cycle;
- number of lateral candidates proposed, rejected, promoted to reference/branch, or promoted to skill;
- cross-skill handoffs with explicit eval coverage.

Do not optimize these metrics mechanically. Their purpose is to show whether the loop is still learning.
