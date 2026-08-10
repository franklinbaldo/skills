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
| [usage-0003](usage/usage-0003.md) | same-attempt retry | `mp0001-C` | 1 |
| [usage-0004](usage/usage-0004.md) | helper Skill | `mp0001-D` | 1 |
| [usage-0005](usage/usage-0005.md) | abort after productive start | `mp0001-E` | 1 |

No subagent case was added because this execution environment did not provide a distinct subagent surface with evidence clear enough to improve the experiment.

## Independent count 1 — deterministic counter

The committed `count_usage.py` reads only factual `status: experiment_evidence` records for the governed Skill, requires productive execution to have started, requires `counted: true`, rejects duplicate `invocation_id` values, and counts unique logical invocations.

GitHub Actions executed it against the committed corpus and printed:

```text
usage-0001.md  mp0001-A  +1
usage-0002.md  mp0001-B  +1
usage-0003.md  mp0001-C  +1
usage-0004.md  mp0001-D  +1
usage-0005.md  mp0001-E  +1
usage_total=5
```

Result: **5**.

## Independent count 2 — record-by-record reconstruction

A separate reconstruction ignores `count_usage.py` and applies the RFC semantics directly to the five records:

1. A is one normal productive attempt: +1.
2. B contains multiple steps under one `invocation_id`: +1 total, not one per step.
3. C preserves one logical attempt across a failed transport and simulated automatic same-attempt retry: +1 total, not +2.
4. D uses `software-review` as a helper while `okf-agent-skills` remains principal: principal +1; helper +0 under the principal-skill meter.
5. E crossed the productive-start boundary before aborting: +1.

Distinct principal invocation ids are `mp0001-A`, `mp0001-B`, `mp0001-C`, `mp0001-D`, and `mp0001-E`.

Result: **5**.

The two independent readings agree. No evidence was edited to force agreement.

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

The first smoke, GitHub Actions run `31401466334`, failed usefully after the deterministic counter had already returned 5. `okf-parser check` reported `OKF001` for `README.md` and `operational-license.md` because they lacked YAML frontmatter. The evidence was not rewritten; the corpus defect was fixed minimally by making both ordinary `type: Note` OKF documents. No licensing-specific protocol type was added.

The second smoke, run `31401638071`, used `okf-parser` commit `8cf97286868aafd8fbda8e82f7b32bf342324fdd` and exposed only the expected warning that this results document did not yet exist.

The final smoke, GitHub Actions run `31401788036`, executed the now-complete corpus and passed all requested surfaces with no diagnostics:

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

Recording these final smoke outputs changes no concept identity or Markdown relation in the validated corpus.

## Result against success criteria

**PASS.**

- authorization existed before productive use;
- each attempt has a reconstructible `invocation_id`;
- continuation, retry, helper, and abort behavior produced deterministic classifications;
- two independent counts both return `usage_total = 5`;
- grant, license id, policy reference, policy digest, and Skill commit are reconstructible;
- `okf-parser` validates the complete corpus with zero diagnostics;
- the graph contains one connected DAG with the expected explicit Markdown relations;
- DuckDB materializes the concepts and links without a licensing-specific database or schema layer;
- the economic transition is mechanically reconstructible without money or a billing service;
- no RFC or licensing-protocol change was required;
- the only defect discovered was generic OKF corpus conformance, fixed with the smallest possible frontmatter addition.

Experiment 0001 therefore supports the minimal architecture as written. No special licensing infrastructure is needed for this scope.
