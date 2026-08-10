---
name: loop-engineering
description: >-
  Design and evolve self-improving loops for Agent Skills, evals and benchmark systems.
  Use when a skill, benchmark, routing system or quality-eval process should improve
  continuously through evidence, harder tests, methodological innovation, lateral
  decomposition into new skills, or routing/pollination between neighboring skills.
  Do not use for one-off prompt polishing or for changing a skill without a measurable
  feedback loop.
---

# Engineer the loop, not only the current answer

The object of improvement is the **whole learning loop**:

```text
skill behavior
→ evidence
→ diagnosis
→ skill change
→ stronger benchmark
→ new evaluation method
→ broader/lateral opportunities
→ repeat
```

A successful cycle must improve more than the current score. It should leave behind a system
that can discover the next failure, including failures nobody thought to encode before.

## Invariants

1. **Evidence before tuning.** Do not rewrite a skill merely because a change sounds better.
2. **The benchmark evolves too.** Preserve valid regressions while continuously increasing
   coverage, difficulty, diversity and methodological power.
3. **No benchmark teaching.** Do not rewrite expected outcomes or descriptions merely to make
   known cases green.
4. **Innovation is required.** When current metrics saturate, invent or try a more revealing
   evaluation method instead of declaring completion.
5. **Vertical and lateral evolution are both valid.** Improve an existing skill when the same
   capability remains coherent; split or create a sibling skill when a newly discovered
   capability has a distinct purpose, trigger boundary or evaluation surface.
6. **Skills may pollinate each other.** A skill can route to, recommend, sequence with or help
   produce another skill when evidence shows a stable neighboring capability.
7. **Coverage can expand sideways.** Saturation in one axis is a prompt to inspect adjacent
   unmet intents, recurring handoffs and capabilities hiding in failure/near-miss cases.
8. **Keep provenance.** Simulation, real host observations, quality judgments and human
   decisions remain distinguishable.

## Per-cycle protocol

For each cycle answer all five questions:

1. **What did we learn?** Identify observed failures, unstable boundaries, blind spots or
   newly solved capabilities.
2. **What should change in the skill?** Make the smallest justified behavioral change.
3. **How should the benchmark become harder?** Add regressions, held-out challenges,
   collisions, adversarial paraphrases, continuations or another useful frontier.
4. **What new evaluation method should we try?** Consider catalog perturbation, mutation
   testing, multi-turn routing, counterfactual skill/no-skill, cross-host/model comparisons,
   calibration, blind pairwise judging or a new design suggested by the current uncertainty.
5. **Is there a lateral opportunity?** Ask whether an observed recurring capability should:
   - remain inside the skill;
   - become a reference/workflow branch;
   - become a sibling skill;
   - become a routing/handoff relation between skills;
   - be discarded as incidental.

Read [`references/evolution-loop.md`](references/evolution-loop.md) before designing a new
benchmark method or deciding whether to split/create a skill. Consult
[`references/lateral-opportunities-0001.md`](references/lateral-opportunities-0001.md) for the
current evidence-backed opportunity map; update that map rather than creating sibling skills
from intuition alone.

## Vertical improvement

Use vertical improvement when the same skill purpose remains stable and the new evidence
clarifies its trigger, workflow or output contract.

Typical actions:

- tighten or widen a routing description based on evidence;
- add a missing branch/reference;
- improve instructions for a recurring failure;
- add regression and held-out evals;
- add a new quality rubric dimension;
- reduce ambiguity with neighboring skills.

Do not create a new skill merely because a section is getting long.

## Lateral evolution and pollination

Look for lateral evolution when repeated evidence reveals a **distinct job** rather than a
mere edge case.

Signals include:

- the same near-miss repeatedly appears but should not trigger the current skill;
- users repeatedly need a neighboring step before/after the current skill;
- one branch has different evidence, tools, safety constraints or definition of done;
- two skills repeatedly co-activate or hand work to each other;
- a benchmark collision reveals an unnamed intermediate capability;
- output-quality gains depend on a reusable method that benefits multiple skills.

Before splitting, state the candidate new skill's purpose and trigger boundary in one
sentence. If that cannot be done cleanly, keep learning before creating it.

When a sibling skill is justified, add explicit evals for:

- when the parent should trigger but the sibling should not;
- when the sibling should trigger but the parent should not;
- legitimate handoff/composition cases;
- out-of-domain controls.

## Benchmark R&D

Treat benchmark design as research, not fixture maintenance. The benchmark should continually
try to expose behavior the current test suite cannot see.

Do not measure progress only by accuracy. Also track whether the evaluation surface gained:

- new covered skills/intents;
- harder semantic boundaries;
- held-out frontier size;
- mutation kill rate;
- stability under irrelevant catalog changes;
- useful cross-skill collisions;
- multi-turn coverage;
- new evaluation modes;
- newly discovered blind spots.

A score can fall while the system improves if the benchmark became materially more revealing.

## Relationship to other skills

Use [`../okf-agent-skills/SKILL.md`](../okf-agent-skills/SKILL.md) for deterministic projection,
observation ingestion and relational inspection of the skills corpus.

Use [`../software-review/SKILL.md`](../software-review/SKILL.md) when reviewing the correctness
of an implementation/PR/RFC produced by the loop.

When authoring or changing a skill, follow the current upstream skill-creation guidance and
preserve realistic trigger evals; this skill governs the **evolution loop**, not a competing
skill format or runtime.

## Definition of done for one cycle

A loop cycle is complete only when:

- evidence and provenance are recorded;
- the chosen skill change is justified by that evidence;
- valid old evals remain regressions;
- the benchmark gained a harder or broader frontier;
- at least one benchmark-method innovation was considered, and used when it can answer an
  unresolved question better than existing metrics;
- lateral opportunities were explicitly assessed;
- any new/split skill has its own trigger boundary and evals;
- the next cycle has a frontier capable of finding something the current cycle could not.

The goal is not a permanently green benchmark. The goal is a system that keeps becoming
better at discovering how it is still wrong, incomplete or too narrow.