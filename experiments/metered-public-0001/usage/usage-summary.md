---
type: UsageStatement
id: metered-public-0001-usage-summary
skill: okf-agent-skills
skill_ref: "github:franklinbaldo/skills@b64fb52608004ed4a87195edb0b422f1406d3fc1:okf-agent-skills/SKILL.md"
licensee: github:franklinbaldo
license_id: Skill-Use-License-0.1
policy_ref: ../policy.yaml
policy_sha256: "sha256:1ec50793a004226e2480a9eb552fdd9821b3766738eb5f2595cbe1fa9cff6831"
metric: invocation
usage_total: "5"
free_allowance: "3"
receipted_coverage_through: "0"
covered_through: "3"
measured_at: "2026-08-10T14:59:10Z"
status: experiment_summary
---

# Cumulative UsageStatement — Experiment 0001

This statement is governed by the [Operational License Addendum](../operational-license.md), frozen [policy](../policy.yaml), and existing [metered-public RFC](../../../docs/rfcs/0001-agentic-metered-skill-licensing.md).

It covers these five factual invocation records:

1. [Usage 0001 — normal productive execution](usage-0001.md)
2. [Usage 0002 — continuation under one invocation id](usage-0002.md)
3. [Usage 0003 — same-attempt retry](usage-0003.md)
4. [Usage 0004 — helper Skill](usage-0004.md)
5. [Usage 0005 — abort after productive start](usage-0005.md)

The five records contain five distinct governed `invocation_id` values: `mp0001-A` through `mp0001-E`. Continuation steps, the simulated automatic retry, and the helper call stay inside their owning invocation and add no extra principal-Skill count.

Therefore cumulative `usage_total = 5`.

There are no prior economic Receipts in Experiment 0001, so `receipted_coverage_through` is explicitly initialized to **0**, not inferred.
