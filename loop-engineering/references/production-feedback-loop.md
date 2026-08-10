# Production feedback loop

This repository treats real skill use as the primary source of improvement evidence.

## Lifecycle

```text
material skill use
→ self-postmortem
→ no durable record for routine success
  OR
→ deduplicated GitHub feedback issue for actionable learning
→ diagnosis
→ skill/tooling/routing change
→ regression case when useful
→ real use again
```

The postmortem happens after every material use. Persistence is selective.

## Why the postmortem is mandatory

Without an explicit post-use check, agents systematically lose the most useful evidence:
workarounds that succeeded, steps silently ignored, quality degradation that still produced a
finished artifact, routing that was technically plausible but unnecessary, and surprisingly good
methods worth preserving.

The postmortem asks for a counterfactual quality judgment, not a vanity score:

> Did using this skill materially improve the work compared with the agent's likely behavior
> without it?

Allowed answers are `improved`, `neutral`, `degraded`, and `unknown`. The answer should cite a
concrete effect when one exists.

## Persistence gate

Do not open an issue merely because a postmortem exists. Persist only actionable learning.

Strong persistence signals:

- degraded quality;
- wrong/questionable routing;
- partial or failed outcome attributable to the skill contract;
- workaround required;
- ambiguous/contradictory/missing instruction;
- missing real capability/tool;
- host-specific failure or meaningful divergence;
- recurring missing case;
- positive surprise important enough to protect;
- repeated weak signals that form a pattern together.

Routine success with no learning remains ephemeral.

## Deduplication

Before creating a new issue, search open and recently closed skill-feedback issues for the same
underlying problem. Prefer adding a new independent observation to an existing issue. Multiple
real uses on one issue are stronger evidence than multiple near-duplicate issues.

## Privacy boundary

Feedback must be sanitized. Include only the minimum context needed to explain the skill behavior.
Never publish credentials, private legal/process facts, personal data, confidential documents,
private repository material, or full user conversations unless they are already public and needed.
A redacted task summary plus an artifact/commit reference is usually enough.

## Issue content

A useful production feedback issue records facts before proposed fixes:

- skill;
- agent/host when relevant;
- sanitized real task;
- outcome (`success|partial|failure`);
- routing (`correct|questionable|wrong`);
- quality delta (`improved|neutral|degraded|unknown`);
- concrete effect of the skill;
- friction;
- workaround, if any;
- expected behavior;
- safe provenance/reference;
- whether this is a failure, missing capability, host difference, or positive learning.

Root-cause diagnosis is optional at report time.

## From issue to regression

Static evals are memory, not observability. Add an eval after diagnosis when a stable behavioral
boundary deserves protection. Good regressions often originate from production incidents because
they encode a bug the system has actually experienced.

Do not mechanically convert every issue into a test. Tool outages, one-off environment failures,
private task details, and vague quality judgments may be important feedback without becoming a
routing fixture.

## System-level learning

`loop-engineering` may periodically inspect accumulated feedback for cross-skill patterns:

- one host repeatedly lacks a capability assumed by several skills;
- several skills cause the same kind of overengineering;
- a recurring handoff suggests an existing sibling relation should be explicit;
- a repeated positive-learning pattern deserves a reusable reference or sibling capability.

Create new structure only after the real-use evidence shows a stable pattern.
