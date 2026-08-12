---
type: UsageStatement
id: metered-public-0001-usage-0004
skill: okf-agent-skills
skill_ref: "github:franklinbaldo/skills@b64fb52608004ed4a87195edb0b422f1406d3fc1:okf-agent-skills/SKILL.md"
licensee: github:franklinbaldo
license_id: Skill-Use-License-0.1
policy_ref: ../policy.yaml
policy_sha256: "sha256:1ec50793a004226e2480a9eb552fdd9821b3766738eb5f2595cbe1fa9cff6831"
metric: invocation
invocation_id: mp0001-D
usage_total: "1"
productive_execution_started: true
started_at: "2026-08-10T14:58:30Z"
outcome: completed
retry: false
helper: true
helper_skill: software-review
subagent: false
counted: true
status: experiment_evidence
---

# Usage 0004 — helper Skill inside the principal attempt

Governed by the [Operational License Addendum](../operational-license.md) and frozen [policy](../policy.yaml). [`okf-agent-skills`](../../../okf-agent-skills/SKILL.md) remained the principal governed procedure under the [metered-public RFC](../../../docs/rfcs/0001-agentic-metered-skill-licensing.md).

## Productive task

Audit the Experiment 0001 corpus structure for unnecessary duplicated infrastructure while preserving `okf-parser` as the generic inspection layer.

## Observable helper use

During the same attempt, [`software-review`](../../../software-review/SKILL.md) was consulted as a helper for its existing invariant to look for native/existing primitives before inventing infrastructure. The experiment README was then inspected against that criterion.

The helper did not receive the governed Skill as its own principal procedure and did not become a second principal task.

## Counting decision

Principal `okf-agent-skills`: **+1 invocation**. Helper `software-review`: **+0 principal invocations** for this meter, because helper use inside the already-running principal attempt does not create an additional principal invocation.
