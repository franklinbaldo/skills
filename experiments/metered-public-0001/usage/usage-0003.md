---
type: UsageStatement
id: metered-public-0001-usage-0003
skill: okf-agent-skills
skill_ref: "github:franklinbaldo/skills@b64fb52608004ed4a87195edb0b422f1406d3fc1:okf-agent-skills/SKILL.md"
licensee: github:franklinbaldo
license_id: Skill-Use-License-0.1
policy_ref: ../policy.yaml
policy_sha256: "sha256:1ec50793a004226e2480a9eb552fdd9821b3766738eb5f2595cbe1fa9cff6831"
metric: invocation
invocation_id: mp0001-C
usage_total: "1"
productive_execution_started: true
started_at: "2026-08-10T14:58:10Z"
outcome: completed_after_retry
retry: true
retry_mode: harness_preserved_same_attempt
helper: false
subagent: false
counted: true
status: experiment_evidence
---

# Usage 0003 — harness-preserved retry of the same productive attempt

Governed by the [Operational License Addendum](../operational-license.md), frozen [policy](../policy.yaml), and existing [metered-public RFC](../../../docs/rfcs/0001-agentic-metered-skill-licensing.md). The principal procedure was [`okf-agent-skills`](../../../okf-agent-skills/SKILL.md).

## Productive task

Read the `okf-agent-skills` reference index as part of a repository inspection.

## Observable retry

The harness first attempted to obtain the repository with `git clone` and read the reference file locally. That transport failed with `Could not resolve host: github.com`. Without changing the productive task, the harness preserved logical `invocation_id` `mp0001-C`, retried through the connected GitHub file surface, and successfully read [`okf-agent-skills/references/README.md`](../../../okf-agent-skills/references/README.md).

The retry was initiated by the experiment harness, not autonomously recognized by the underlying runtime. This scenario therefore tests the RFC rule **given a preserved same-attempt identity**. It does not prove that two independent runtimes can infer the same `invocation_id` from raw execution traces.

## Counting decision

Given the preserved logical identity, this counts **1 invocation total**, not 2: the transient transport failure and retry belong to `mp0001-C`.

## Experiment boundary

Automatic cross-runtime derivation of logical invocation identity remains intentionally outside Experiment 0001. A later experiment may test runtime-issued or independently reconstructed identity without changing the metering semantics proven here.
