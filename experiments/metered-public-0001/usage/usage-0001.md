---
type: UsageStatement
id: metered-public-0001-usage-0001
skill: okf-agent-skills
skill_ref: "github:franklinbaldo/skills@b64fb52608004ed4a87195edb0b422f1406d3fc1:okf-agent-skills/SKILL.md"
licensee: github:franklinbaldo
license_id: Skill-Use-License-0.1
policy_ref: ../policy.yaml
policy_sha256: "sha256:1ec50793a004226e2480a9eb552fdd9821b3766738eb5f2595cbe1fa9cff6831"
metric: invocation
invocation_id: mp0001-A
usage_total: "1"
productive_execution_started: true
started_at: "2026-08-10T14:57:30Z"
outcome: completed
retry: false
helper: false
subagent: false
counted: true
status: experiment_evidence
---

# Usage 0001 — normal productive execution

Governed by the [Operational License Addendum](../operational-license.md) and frozen [policy](../policy.yaml). The governed procedure is [`okf-agent-skills`](../../../okf-agent-skills/SKILL.md), using the invocation semantics already fixed by the [metered-public RFC](../../../docs/rfcs/0001-agentic-metered-skill-licensing.md).

## Productive task

Inspect the pre-existing `okf-agent-skills` protocol-trial UsageStatement to verify whether it preserves an immutable policy reference and correctly avoids treating the illustrative `metered_public` policy as active.

## Observable evidence

The inspected trial is [`licensing/examples/metered-public/trials/usage-okf-agent-skills-2026-08-07.md`](../../../licensing/examples/metered-public/trials/usage-okf-agent-skills-2026-08-07.md). It records the exact `quote_required` policy commit and explicitly says the illustrative metered policy is inactive.

## Counting decision

This was one productive execution attempt with one principal governed Skill and one logical `invocation_id`. It counts **1 invocation** under the RFC's base invocation rule.
