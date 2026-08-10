# Evolution loop

The system evolves from **real skill use**. Benchmarks and static evals are supporting memory, not the primary observability mechanism.

## Primary loop

```text
real use
→ self-postmortem
→ durable feedback only when actionable
→ diagnosis
→ smallest coherent change
→ regression memory when useful
→ real use again
```

The loop should retain both negative and positive learning: failures, workarounds, questionable routing, quality degradation, missing capabilities, and surprising methods that repeatedly improve results.

## Vertical evolution

Improve an existing skill when real-use evidence shows that the same job remains coherent but its trigger, workflow, handoff, tooling assumption, or definition of done needs adjustment.

Examples:

- a production incident shows the skill triggers too broadly;
- several agents need the same workaround;
- a step is repeatedly skipped because it adds no value;
- a host cannot provide a capability the skill assumes;
- a postmortem identifies a concrete instruction that consistently improves quality and should be preserved.

## Lateral evolution

Create or clarify a neighboring capability only when repeated real-use evidence shows a distinct job with its own trigger and success criterion.

Possible outcomes:

```text
A. improve existing skill
B. add a branch/reference
C. clarify a handoff to an existing skill
D. create a sibling skill
E. collect more evidence
```

Prefer the smallest option that makes the behavior clearer.

## Pollination

One skill can teach another without merging responsibilities. Strong evidence includes repeated handoffs, the same missing capability surfacing across skills, or a reusable method discovered through multiple real tasks.

Pollination should become explicit only after the pattern is stable enough to name.

## Static evals as memory

Routing evals remain useful for known contracts and regressions. They should most often be added or strengthened after a real incident or durable learning demonstrates what deserves protection.

Do not require every issue to become an eval. Tool outages, private task context, host limitations, and one-off quality findings may be important without becoming fixtures.

## Evidence strength

Prefer evidence roughly in this order:

1. repeated independent real-use incidents;
2. one well-reproduced real-use incident with strong provenance;
3. a postmortem with a concrete quality effect or workaround;
4. human review of a real artifact;
5. static regression cases derived from prior evidence;
6. synthetic exploration/simulation as optional hypothesis generation.

Never relabel level 6 as level 1.

## System health

Do not optimize for issue count, eval count, benchmark coverage, or a universal accuracy number.

Healthier signals are:

- repeated production failures becoming less frequent;
- fewer workarounds for the same job;
- clearer routing/handoffs in real tasks;
- more postmortems with concrete evidence rather than vague impressions;
- recurring positive learnings being preserved;
- duplicate feedback consolidating into stronger evidence;
- new skills appearing only after stable demand is visible.

The system is learning when actual use produces fewer repeated surprises and better explanations for the surprises that remain.
