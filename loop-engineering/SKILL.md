---
name: loop-engineering
description: >-
  Evolve Agent Skills from real-use evidence. Use when production use, a postmortem,
  a feedback issue, a workaround, a routing mistake, a quality regression, or a
  repeated positive surprise reveals something worth preserving or changing. Do not
  replace real-use evidence with synthetic benchmark machinery when the actual users
  and agents can report what happened.
---

# Learn from use, not from a laboratory substitute

The primary loop is:

```text
real skill use
→ mandatory self-postmortem
→ actionable feedback issue when warranted
→ diagnosis
→ smallest justified change
→ regression memory when useful
→ real use again
```

Static evals are useful as regression memory. They are not a substitute for observing what
happened during actual work.

Read [`references/production-feedback-loop.md`](references/production-feedback-loop.md) before
changing a skill from feedback.

## Invariants

1. **Every material use ends with a postmortem.** The agent evaluates whether the skill was the
   right choice and whether it materially improved the work.
2. **Self-report is evidence, not self-congratulation.** Claims such as "worked well" need a
   concrete effect: a decision changed, an error avoided, a useful branch discovered, a bad
   action prevented, or a workaround required.
3. **Issues are gated.** Do not open GitHub issues for routine success, cosmetic preference or
   vague dissatisfaction. Open one when there is actionable learning.
4. **Preserve negative and positive learning.** Failures matter, but so do surprising successful
   behaviors that should be protected from future regressions.
5. **Deduplicate before opening.** Search existing feedback issues and add evidence to a matching
   issue when the same underlying problem is already tracked.
6. **Protect private context.** Never publish secrets, private case facts, credentials, personal
   data or confidential material just to make a feedback report reproducible.
7. **Regression tests follow incidents; they do not manufacture incidents.** Add or strengthen
   evals after diagnosis when they help preserve a learned boundary.
8. **Keep the system small.** Do not build host adapters, synthetic repeated-run ledgers, routing
   simulators or benchmark ontologies merely to approximate evidence available from real use.

## Mandatory postmortem

After a material skill use, assess internally:

- **routing** — was this the right skill, too early/late, unnecessary, or should another skill
  have been used?
- **outcome** — `success`, `partial`, or `failure`;
- **quality delta** — did the skill likely make the result `improved`, `neutral`, `degraded`, or
  is the counterfactual `unknown`?
- **effective instruction** — what concrete part of the skill changed the work?
- **friction** — ambiguity, missing context, unavailable tool, bad handoff, unnecessary step,
  conflicting instruction, host limitation, or other obstacle;
- **workaround** — whether the agent had to bypass or reinterpret the skill to finish;
- **definition of done** — whether the skill actually met its own success criteria;
- **next action** — `none`, `feedback issue`, `regression candidate`, or a concrete capability
  gap worth investigating.

A useful compact mental record is:

```text
skill: <name>
outcome: success | partial | failure
routing: correct | questionable | wrong
quality_delta: improved | neutral | degraded | unknown
friction: none | <concrete friction>
workaround_required: true | false
learning: <concrete evidence>
feedback: none | issue
```

The postmortem itself is ephemeral unless the result is useful to preserve.

## When to open a feedback issue

Open or update an issue when at least one of these is true:

- routing was wrong or materially questionable;
- the skill degraded the result;
- the task ended partial/failure because of the skill contract;
- a workaround was required;
- an instruction was contradictory, ambiguous or materially incomplete;
- a required capability/tool was absent in real use;
- a host-specific behavior materially changed the result;
- the same missing case recurs;
- a surprising positive behavior or method is valuable enough to protect;
- several small postmortems reveal the same pattern.

Classify the issue when useful as one or more of:

- `routing`
- `instruction`
- `tooling`
- `missing-case`
- `workaround`
- `quality`
- `host-specific`
- `positive-learning`

## What an issue should contain

Preserve factual evidence, not a speculative fix:

- skill name;
- agent/host when relevant;
- sanitized summary of the real task;
- what happened;
- what was expected;
- quality delta and why;
- concrete friction/workaround;
- artifact/PR/commit reference when safe and available;
- whether a similar issue already exists.

Diagnosis and remediation can happen later. Do not make the reporter invent a root cause merely
to fill the issue.

## Turning feedback into changes

When enough evidence exists:

1. reconstruct the actual failure or success pattern from the issues;
2. separate routing, instruction, tooling, host and missing-capability causes;
3. choose the smallest change that addresses the evidence;
4. preserve valid old behavior;
5. add a regression case only when it protects a learned contract or failure boundary;
6. re-use the changed skill in real work and inspect the next postmortem.

Do not optimize for issue count, eval count or benchmark accuracy. Optimize for fewer repeated
production failures and more reliably useful skill behavior.

## Lateral evolution

A sibling skill or explicit handoff is justified only when repeated real-use evidence reveals a
distinct job with its own trigger and definition of done. One synthetic collision or one clever
example is not enough.

Possible outcomes are:

```text
A. improve the existing skill
B. add a branch/reference
C. clarify a handoff to an existing sibling
D. create a sibling skill
E. do nothing yet; collect more real-use evidence
```

Prefer the smallest coherent option.

## Relationship to static evals

Keep useful `eval_queries.json` cases as regressions for known boundaries. New cases should most
often trace back to a real incident, a repeated near-miss, or a concrete learning from actual use.
Synthetic adversarial exploration remains optional diagnostic work, never the evidence gate for
improving a skill.

## Definition of done for one learning cycle

A cycle is complete when:

- the triggering real-use evidence is preserved in an issue or other durable artifact when needed;
- the postmortem identifies a concrete quality/routing effect rather than a vague impression;
- duplicate feedback is consolidated;
- the change is the smallest one justified by the evidence;
- a regression is added only when it protects something learned;
- no private material was leaked into feedback;
- the changed skill returns to real use, where the next postmortem can falsify the improvement.

The goal is not a permanently green benchmark. The goal is skills that become more useful because
they remember what actually happened when agents tried to use them.
