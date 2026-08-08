# Lateral opportunity map 0001

This register is deliberately evidence-led. It records where the current loop sees stable neighboring jobs, handoffs or possible future sibling skills. It is not a wishlist of directories to create.

## Decision rule

For each candidate, choose one state:

- **vertical** — keep improving the existing skill;
- **handoff** — preserve two distinct skills and make sequencing/routing explicit;
- **compose** — both skills may legitimately participate in the same task;
- **candidate sibling** — repeated evidence suggests a distinct reusable job with its own trigger and definition of done;
- **insufficient evidence** — do not create anything yet.

A sibling skill needs more than semantic proximity. Require at least a distinct purpose, trigger boundary and evaluation surface, plus repeated evidence that keeping the job inside the current skill causes routing/workflow ambiguity or repeated duplication.

## Current neighborhoods

### revisao-minutas ↔ notebooklm-processos

**State: handoff / compose.**

The distinction is currently healthy:

- `notebooklm-processos` reconstructs missing evidence from large/incomplete records;
- `revisao-minutas` decides whether an existing forensic/institutional draft is fit to sign/file/send.

The multi-turn frontier now tests both directions. There is no evidence yet for a third skill between them. A future candidate would need a recurring job that is neither evidence reconstruction nor draft readiness review.

### revisao-minutas ↔ legal-argument-lean

**State: handoff / compose.**

Formal argument auditing and institutional draft review remain distinct. A review may discover a structural uncertainty worth formalizing; a Lean audit may later need translation back into a draft. Keep the boundary and test the handoff before inventing an intermediate skill.

### software-review ↔ blank-sheet-redesign

**State: handoff, with deliberate mode switch.**

`software-review` starts from an artifact under review. `blank-sheet-redesign` intentionally suspends the current design and reasons from purpose/constraints. Multi-turn cases now test transitions in both directions.

A sibling skill is not justified merely because both discuss architecture.

### franklin-blog ↔ text-meme-injection

**State: compose / handoff.**

Authorship/voice recovery is different from adding meme-register texture to already-written prose. The current split is useful and the multi-turn frontier tests when the primary job changes.

### loop-engineering ↔ okf-agent-skills

**State: compose.**

`loop-engineering` decides how the improvement system should evolve. `okf-agent-skills` projects and audits the corpus. Keep governance/learning semantics separate from deterministic knowledge materialization.

## Signals that should create a new candidate

Open a sibling-skill candidate only when evidence shows one or more of these repeatedly:

1. the same hard-negative cluster belongs to a coherent neighboring job;
2. multi-turn runs repeatedly switch at the same conceptual step that has no named skill;
3. a workflow branch needs distinct tools/evidence/safety constraints;
4. output-quality experiments show a reusable method that improves several skills but does not belong to any one of them;
5. users repeatedly ask for an intermediate deliverable with its own clear definition of done;
6. a description must become artificially broad merely to absorb that job.

For every candidate, write before implementation:

```text
job:
why existing skills should not own it:
positive trigger boundary:
negative boundary against nearest siblings:
first held-out cases:
expected handoffs/compositions:
evidence that this is recurring rather than incidental:
```

## Current conclusion

The first loop-engineering cycle found strong evidence for **better handoff benchmarks and composition tests**, but not yet for a new domain sibling beyond `loop-engineering` itself. That is a useful negative result: pollination does not mean automatic proliferation.

The next place likely to expose a real lateral candidate is output-quality evaluation (#62) or repeated real-host routing (#60/#61), because those can reveal reusable jobs that static descriptions alone cannot see.
