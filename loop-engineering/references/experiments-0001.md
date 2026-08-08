# Benchmark R&D experiments 0001

This is the first explicit benchmark-research frontier for the skill ecosystem. It is not a permanent canon; successful experiments should either become repeatable benchmark modes or be replaced by more revealing methods.

## Experiment A — description mutation testing

### Question

Can the current routing benchmark detect when a skill description is deliberately made worse?

### Mutations

For a target skill, create temporary variants without committing them as the candidate skill:

1. **remove-negative-boundary** — delete one important `Do not use`/negative boundary;
2. **broaden-domain-noun** — replace a narrow domain term with a broader neighbor;
3. **remove-continuation** — remove wording that supports follow-up/continuation routing;
4. **trigger-word-only** — reduce the description toward obvious lexical trigger words while preserving superficial plausibility;
5. **neighbor-bleed** — add one sentence that makes the description overlap a sibling skill.

### Measurement

Run the regression + challenge corpus against the original and each mutation. A mutation is *killed* when the benchmark detects a meaningful degradation in the expected boundary.

Track:

```text
mutation_kill_rate = killed_mutations / valid_mutations
```

Also record which cases killed each mutation. A high score from one duplicated lexical case is weaker evidence than kills from several independent semantic cases.

### Failure interpretation

If a mutation that clearly weakens the routing contract survives, do not immediately change the skill. First ask what class of test is missing from the benchmark.

The benchmark is the object under test here.

## Experiment B — catalog perturbation

### Question

Is routing stable when irrelevant skills enter or leave the catalog, and does it change explainably when a legitimate competitor appears?

### Conditions

For each selected prompt, compare at least:

1. target skill only;
2. target + clearly irrelevant skills;
3. target + one plausible neighboring skill;
4. target + several plausible neighboring skills;
5. full repository catalog.

### Expected behavior

- adding irrelevant skills should not materially change the routing decision;
- adding a real competitor may change the routing outcome, but the change should correspond to the semantic boundary being tested;
- removing the best skill should expose a meaningful fallback or abstention behavior rather than fabricate equivalence.

### Measurements

Track:

- invariance under irrelevant additions;
- decision changes under legitimate competitors;
- unexpected cross-skill substitutions;
- no-suitable-skill/fallback behavior when the target is absent;
- instability across repeated real-host runs separately by host/model.

Do not collapse these into one opaque score at first. The pattern of changes is more informative than a headline number.

## Initial targets

Start where the existing corpus already exposed useful boundaries:

- `revisao-minutas` × `legal-argument-lean` × `notebooklm-processos`;
- `software-review` × `blank-sheet-redesign`;
- `franklin-blog` × `text-meme-injection`.

These neighborhoods combine clear composition opportunities with plausible collisions.

## Promotion criteria

Promote an experiment into a stable benchmark mode when:

- it reveals a failure or distinction not captured by ordinary one-prompt routing accuracy;
- the result is reproducible enough to compare cycles;
- its setup does not require a new competing skills runtime;
- the measurement can preserve host/model/provenance distinctions;
- its maintenance cost is justified by information gained.

Discard or redesign an experiment when it mostly duplicates an existing metric, produces uninterpretable noise, or encourages optimizing to an artificial setup.

## Next innovation question

After running these two methods, the next cycle must ask what they still cannot see. Candidates include multi-turn routing, split-vs-composed-skill experiments, ambiguity gradients, skill/no-skill output-quality counterfactuals, and automated coverage mining from real user tasks.
