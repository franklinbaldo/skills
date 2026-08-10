---
type: Note
id: metered-public-0001-results
role: experiment_results
---

# Results — Experiment 0001

The experiment is governed by the [Operational License Addendum](operational-license.md), frozen [policy](policy.yaml), and the existing [metered-public RFC](../../docs/rfcs/0001-agentic-metered-skill-licensing.md). The cumulative economic record is the [UsageStatement](usage/usage-summary.md), followed by a simulated [InvoiceRequest](invoice-request.md).

## Uses executed

Five real internal productive attempts were recorded:

| Record | Scenario | Invocation | Count |
| --- | --- | --- | ---: |
| [usage-0001](usage/usage-0001.md) | normal | `mp0001-A` | 1 |
| [usage-0002](usage/usage-0002.md) | continuation | `mp0001-B` | 1 |
| [usage-0003](usage/usage-0003.md) | harness-preserved same-attempt retry | `mp0001-C` | 1 |
| [usage-0004](usage/usage-0004.md) | helper Skill | `mp0001-D` | 1 |
| [usage-0005](usage/usage-0005.md) | abort after productive start | `mp0001-E` | 1 |

No subagent case was added because this execution environment did not provide a distinct subagent surface with evidence clear enough to improve the experiment.

## Adversarial review and correction

A post-experiment adversarial review found that the original `count_usage.py` filtered on `counted: true`. That made `counted` partly self-authenticating: the program consumed a conclusion that it was supposed to verify. The original summary and InvoiceRequest also repeated derived numbers without a committed invariant check tying them back to the evidence and frozen policy.

The review fixes deliberately remain experiment-local:

1. `count_usage.py` now derives each record's economic contribution from `productive_execution_started` under the experiment's governed principal-Skill scope.
2. `counted` and per-record `usage_total` are assertions checked against that derived contribution; neither is an input to the total.
3. productive invocation ids must exist and be unique.
4. the verifier computes the SHA-256 of `policy.yaml` and rejects provenance drift in usage, summary, or InvoiceRequest records.
5. it reads the policy's free allowance and billing unit, derives `covered`, `uncovered`, `blocks`, and `requested_coverage_through`, and rejects any mismatch in `usage-summary.md` or `invoice-request.md`.
6. if no uncovered usage exists, a leftover InvoiceRequest is rejected.

This closes the false-green path identified in review without adding a general licensing parser, billing framework, database, service, or new protocol type.

## Independent count 1 — derived verifier

The committed `count_usage.py` treats the five factual usage records as evidence, derives one economic event for each productive principal attempt, rejects duplicate logical identities, and then checks the authored assertions and downstream economic records against its reconstruction.

For the current corpus the expected output is:

```text
usage-0001.md  mp0001-A  +1
usage-0002.md  mp0001-B  +1
usage-0003.md  mp0001-C  +1
usage-0004.md  mp0001-D  +1
usage-0005.md  mp0001-E  +1
usage_total=5
policy_sha256=sha256:1ec50793a004226e2480a9eb552fdd9821b3766738eb5f2595cbe1fa9cff6831
covered=3
uncovered=2
blocks=1
requested_coverage_through=5
summary_verified=true
invoice_request_verified=true
```

Result: **5**.

## Independent count 2 — record-by-record reconstruction

A separate reconstruction ignores `count_usage.py` and applies the RFC semantics directly to the five records:

1. A is one normal productive attempt: +1.
2. B contains multiple steps under one preserved `invocation_id`: +1 total, not one per step.
3. C preserves one logical attempt across a failed transport and harness-initiated retry: +1 total, not +2.
4. D uses `software-review` as a helper while `okf-agent-skills` remains principal: principal +1; helper +0 under the principal-skill meter.
5. E crossed the productive-start boundary before aborting: +1.

Distinct principal invocation ids are `mp0001-A`, `mp0001-B`, `mp0001-C`, `mp0001-D`, and `mp0001-E`.

Result: **5**.

The two readings agree. No usage evidence was edited to force agreement.

## Runtime identity boundary

Scenario C originally risked overstating what the experiment had proven. The first transport really failed and a retry really occurred, but the experiment harness deliberately preserved `mp0001-C`; the underlying runtime did not autonomously recognize or reconstruct the logical identity.

Experiment 0001 therefore proves the RFC's retry counting rule **given a runtime- or harness-assigned logical invocation identity**. It does not prove that two unrelated runtimes can independently infer the same `invocation_id` from raw traces. That is an observability/runtime question intentionally left open by the RFC and is a candidate for a later experiment, not a reason to mutate the metering semantics here.

## Economic transition

The experiment explicitly initializes `receipted_coverage_through = 0` because no prior economic Receipt exists.

```text
usage_total = 5
free_allowance = 3
billing_unit = 2
receipted_coverage_through = 0

covered = max(3, 0) = 3
uncovered = max(0, 5 - 3) = 2
blocks = ceil(2 / 2) = 1
requested_coverage_through = 3 + 1 * 2 = 5
```

The resulting `InvoiceRequest` is intentionally simulated. The Addendum already authorizes the post-allowance experiment uses and creates no real payment obligation.

## OKF smoke history

The first smoke, GitHub Actions run `31401466334`, failed usefully after the original counter had returned 5. `okf-parser check` reported `OKF001` for `README.md` and `operational-license.md` because they lacked YAML frontmatter. The corpus defect was fixed minimally by making both ordinary `type: Note` OKF documents. No licensing-specific protocol type was added.

The second smoke, run `31401638071`, used `okf-parser` commit `8cf97286868aafd8fbda8e82f7b32bf342324fdd` and exposed only the expected warning that this results document did not yet exist.

The pre-review complete-corpus smoke, GitHub Actions run `31401788036`, passed all requested OKF surfaces with no diagnostics:

```text
check:
  concept_count: 10
  conformant: true
  diagnostics: 0

inventory:
  InvoiceRequest: 1
  Note: 3
  UsageStatement: 6

graph:
  nodes: 10
  edges: 23
  weakly_connected_components: 1
  directed_acyclic: true

duckdb:
  concept_count: 10
  conformant: true
  link_count: 23
  diagnostic_count: 0
```

The adversarial-review fixes require the same OKF surfaces plus the stricter derived verifier to pass again before the PR is considered review-clean.

## Result against success criteria

**PASS, subject to the explicitly bounded runtime-identity limitation above.**

- authorization existed before productive use;
- each attempt has an explicit logical `invocation_id`;
- counting no longer trusts `counted` as an input;
- summary and InvoiceRequest values are mechanically checked against evidence plus frozen policy;
- continuation, helper, and abort behavior remain reconstructible;
- the retry rule is demonstrated when same-attempt identity is preserved, without claiming automatic runtime identity inference;
- two independent counts return `usage_total = 5`;
- grant, license id, policy reference, policy digest, and Skill commit are reconstructible;
- `okf-parser` validates the corpus without a licensing-specific schema or database layer;
- the economic transition is mechanically reconstructible without money or a billing service;
- no RFC or licensing-protocol amendment is required by the review fixes.

Experiment 0001 still supports the minimal architecture, but now with the evidentiary boundary stated precisely and the previously self-authenticating counter removed.
