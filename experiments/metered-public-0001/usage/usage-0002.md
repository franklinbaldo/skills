---
type: UsageStatement
id: metered-public-0001-usage-0002
skill: okf-agent-skills
skill_ref: "github:franklinbaldo/skills@b64fb52608004ed4a87195edb0b422f1406d3fc1:okf-agent-skills/SKILL.md"
licensee: github:franklinbaldo
license_id: Skill-Use-License-0.1
policy_ref: ../policy.yaml
policy_sha256: "sha256:1ec50793a004226e2480a9eb552fdd9821b3766738eb5f2595cbe1fa9cff6831"
metric: invocation
invocation_id: mp0001-B
usage_total: "1"
productive_execution_started: true
started_at: "2026-08-10T14:57:50Z"
outcome: completed
retry: false
helper: false
subagent: false
counted: true
status: experiment_evidence
---

# Usage 0002 — continuation under one invocation id

Governed by the [Operational License Addendum](../operational-license.md) and frozen [policy](../policy.yaml). The principal procedure remained [`okf-agent-skills`](../../../okf-agent-skills/SKILL.md), under the [metered-public RFC](../../../docs/rfcs/0001-agentic-metered-skill-licensing.md).

## Productive task

Inspect the existing metered-public fixture relation from an `InvoiceRequest` to its predecessor UsageStatement and confirm that the predecessor is represented as an explicit Markdown link.

## Observable continuation

The same logical attempt first searched the repository for `type: InvoiceRequest`, then fetched and inspected [`requests/req-2026-0042.md`](../../../licensing/examples/metered-public/requests/req-2026-0042.md). Those are multiple observable steps/outputs inside `mp0001-B`, not new productive attempts.

## Counting decision

The attempt counts **1 invocation total**. The search step and later file inspection do not add invocations because continuation under the same logical `invocation_id` does not count again.
