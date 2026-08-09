---
type: RFC
id: RFC-0001
title: Agentic Metered Skill Licensing Protocol
status: draft
author: Franklin Baldo
created: 2026-08-07
---

# RFC 0001 — Agentic Metered Skill Licensing Protocol

## Status

Draft.

This RFC is stacked on [Skill Use License 0.1](../../LICENSE.md), its [machine-readable policy](../../licensing/policy.yaml), and the [license-enforcement skill](../../license-enforcement/SKILL.md).

The current repository baseline remains `quote_required`. This RFC does not silently grant Operational Use and does not activate `metered_public` merely by describing it.

The human-control rule from the baseline is unchanged: an agent may investigate and prepare, but publication of an adverse finding, external notice, collection demand, takedown, or legal escalation about a third party requires explicit human approval.

## Summary

Keep the protocol small.

A metered Skill needs:

1. a legal instrument that expressly grants Operational Use under a named `metered_public` policy;
2. that policy, with deterministic usage and pricing semantics;
3. a free `license-compliance` Skill that teaches the Licensee how to comply;
4. ordinary OKF Markdown records for usage, invoicing, and payment; and
5. `okf-parser` as the generic validation, graph, schema, and DuckDB projection layer.

No billing framework, custom ledger service, bespoke database, or licensing-specific parser is proposed.

The ordinary flow is conditional:

```text
Skill use
  -> UsageStatement
  -> [still covered: stop]
```

or, when usage is uncovered:

```text
Skill use
  -> UsageStatement
  -> InvoiceRequest
  -> Invoice
  -> payment
  -> Receipt
```

A `UsageStatement` records measured use. It does not itself mean that money is owed.

The existing `license-enforcement` path remains the independent verification path. This RFC does not create a second audit framework.

## Authorization comes before metering

The economic policy is not, by itself, the legal grant.

Skill Use License 0.1 currently says that no Operational Use license is granted by the public License and that Operational Use requires a separate paid license. Therefore a YAML file saying `free_allowance: 1000` cannot, on its own, turn the first 1,000 productive uses into authorized uses.

A `metered_public` policy MUST be treated as inactive unless an applicable legal instrument expressly grants Operational Use under that named policy.

That instrument may be revised license text or a short operational-license addendum. It does not need to become a new protocol record type.

At minimum, the governing instrument must make explicit that:

- Operational Use under the identified policy is permitted subject to its terms;
- uses within the free allowance are licensed, not merely non-billable;
- uses above the allowance are licensed only to the extent covered by the policy's payment/coverage rule; and
- if the legal instrument and economic policy conflict, the legal instrument controls.

Until such an instrument is actually adopted, `metered_public` fixtures and trials in this repository remain demonstrations of protocol mechanics only. They do not create permission, debt, or payment obligations.

## Use `okf-parser`, do not rebuild it

Protocol records are ordinary `.md` files with OKF frontmatter and Markdown links.

Use existing `okf-parser` surfaces:

```bash
okf-parser check .
okf-parser inventory .
okf-parser graph .
okf-parser schema . --format pydantic
okf-parser duckdb . okf.duckdb --overwrite
```

The experiment MUST NOT introduce:

- a second schema language;
- a custom graph implementation;
- a relational model parallel to the `okf-parser` DuckDB projection;
- a licensing-specific parser inside `okf-parser`;
- a custom ledger service; or
- generated application models without a real consumer.

## Freeze the governing policy

Every economic chain must identify the rule that produced it.

A `UsageStatement` MUST record:

- `license_id`; and
- an immutable reference to the governing policy, either by immutable repository reference, content digest, or equivalent.

A mutable path such as `licensing/policy.yaml` without a version/digest is insufficient because later policy changes must not rewrite the meaning of an older Invoice or Receipt.

Downstream records inherit the policy through their predecessor links. They MAY repeat the reference for convenience, but they do not need to duplicate it.

The fixture in `licensing/examples/metered-public/` uses a policy file plus SHA-256 digest. The real non-billable protocol trial points to the exact commit containing the active `quote_required` policy.

## Deterministic metric semantics

`metered_public` is valid only when two conforming implementations given the same facts reach the same billing result.

For the initial experiment, `metric: invocation` and `scope: principal_skill` mean:

1. **Invocation.** One invocation is one productive execution attempt of the governed principal Skill. A runtime assigns or preserves one logical `invocation_id` for that attempt.
2. **Continuation.** Additional turns, tool calls, or outputs inside the same logical `invocation_id` do not create another invocation.
3. **Retry.** An automatic retry of the same attempt after a transient failure, using the same logical `invocation_id`, does not count again. A new productive attempt with a new logical `invocation_id` does.
4. **Principal Skill.** The principal Skill is the governed Skill intentionally selected as the primary procedure for the task. Helper/dependency Skills called inside it are not additional principal invocations merely because they were consulted.
5. **Subagents.** A subagent assigned the governed Skill as its own principal procedure performs a separate invocation. A subagent that merely assists the already-running principal invocation without taking that Skill as its principal procedure does not.
6. **Abort.** Routing, eligibility checks, or evaluation before productive execution begins do not count. If productive execution begins and later aborts or fails, the attempt counts once.
7. **Multiple outputs.** Producing several outputs within the same logical attempt still counts once.

These rules define the economic event. The protocol still does not prescribe how a runtime stores logs or observability data.

## Initial economic rule

The first experiment chooses one concrete policy rather than a general billing DSL:

```yaml
commercial_terms:
  pricing_model: metered_public

metering:
  metric: invocation
  scope: principal_skill
  counter: cumulative
  free_allowance: 1000
  allowance_reset: never
  billing_unit: 1000
  rounding: ceiling
  coverage: paid_block_watermark

pricing:
  amount: "0.001"
  asset: WLD
  per_billing_unit: 1
```

The fixture policy also carries the metric semantics above in machine-readable form.

Coverage is calculated mechanically:

```text
covered = max(free_allowance, receipted_coverage_through)
uncovered = max(0, usage_total - covered)
blocks = ceil(uncovered / billing_unit)
requested_coverage_through = covered + blocks * billing_unit
```

Therefore:

```text
uses 1..1000     licensed free allowance, but only after a governing grant activates the policy
uses 1001..2000  first paid block
uses 2001..3000  second paid block
```

If cumulative usage reaches `1427` and coverage currently reaches `1000`, one block is requested. Once paid and receipted, coverage advances through `2000`. Use `1428` is already covered; the next uncovered use is `2001`.

## Free compliance bootstrap

An activated `metered_public` regime MUST publish a `license-compliance` Skill.

Using that Skill exclusively to understand and satisfy the license MUST NOT create billable usage under the meter it administers.

That includes:

- reading the license and policy;
- determining whether the policy is legally active for the Licensee and Skill;
- learning what counts as an invocation;
- maintaining the counter;
- producing a `UsageStatement`;
- producing or submitting an `InvoiceRequest`; and
- checking an Invoice or Receipt.

The license must not charge the Licensee for counting how many times it counted the license.

## Minimal OKF vocabulary

The public economic path needs four record types. The policy is a referenced rule, not another workflow engine.

### `UsageStatement`

A bounded statement by the Licensee about its own measured use.

```md
---
type: UsageStatement
id: usage-2026-0042
skill: legal-review
licensee: did:key:example
license_id: Skill-Use-License-0.1
policy: ../policy.yaml
policy_sha256: "sha256:..."
metric: invocation
usage_total: "1427"
covered_through: "1000"
measured_at: "2026-08-07T23:10:00Z"
---
```

Raw logs may remain private. The statement does not become true merely because it is signed or committed to Git.

### `InvoiceRequest`

A request derived from a `UsageStatement`:

```md
---
type: InvoiceRequest
id: req-2026-0042
usage_statement: ../usage/usage-2026-0042.md
requested_coverage_through: "2000"
requested_at: "2026-08-07T23:12:00Z"
---
```

The predecessor link carries the governing policy provenance forward.

### `Invoice`

The Licensor's application of the referenced policy to the requested block:

```md
---
type: Invoice
id: inv-2026-0042
invoice_request: ../requests/req-2026-0042.md
coverage_through: "2000"
amount: "0.001"
asset: WLD
status: issued
---
```

An Invoice is not a court finding and must not be created merely because an auditor suspects unlicensed use.

### `Receipt`

The Licensor's statement that payment satisfied the referenced Invoice and advanced coverage:

```md
---
type: Receipt
id: receipt-2026-0042
invoice: ../invoices/inv-2026-0042.md
coverage_through: "2000"
payment_reference: "0x..."
issued_at: "2026-08-08T00:03:14Z"
---
```

A signature may later strengthen provenance and integrity. It is not required by the initial protocol and does not transform the signed content into material truth.

## Licensee metering

The Licensee maintains an idoneous cumulative counter for the published metric.

The protocol does not prescribe an observability stack. A counter may come from an agent runtime, application log, workflow ID, database, append-only file, or another reasonable authorized mechanism.

For the public protocol, the aggregate `UsageStatement` is sufficient.

Per-event `UsageRecord`, `MeteringPlan`, `EnvironmentAssessment`, and similar records MAY exist if a real use case later requires them. They are not required concepts here.

## Independent audit remains #57

The existing `license-enforcement` Skill remains responsible for investigating possible unreported use under the baseline safeguards.

```text
agent investigates
  -> internal evidence / draft conclusion
  -> HUMAN REVIEW
  -> external publication/contact, if approved
```

A public finding about an identifiable third party and an audit-originated Invoice are adverse external acts. They remain behind explicit human approval.

Public evidence establishing `at_least: 17` does not become `exact: 17`. Authentication proves who asserted what and record integrity, not substantive truth.

## Payment rails are adapters

The protocol does not depend on Pix, WLD, x402, a blockchain, GitHub Actions, or any signing infrastructure.

An Invoice states amount/asset. A Receipt records the payment reference recognized by the Licensor.

The first real transaction may be completely manual.

## Implementation discipline

### Phase 0 — RFC and fixtures

While #57 remains `quote_required`, the metered example is illustrative only.

Require the fixture to survive:

```bash
okf-parser check licensing/examples/metered-public
okf-parser inventory licensing/examples/metered-public
okf-parser graph licensing/examples/metered-public
okf-parser duckdb licensing/examples/metered-public /tmp/licensing.duckdb --overwrite
```

### Phase 1 — activate a legal grant

Before any real external Licensee relies on the free allowance or paid blocks, publish or execute an Operational License/addendum that expressly activates the named policy.

No new protocol type is required for this step.

### Phase 2 — one real manual transaction

Pick one Skill, one Licensee, and the activated policy. Record actual usage. If still covered, stop at `UsageStatement`. If uncovered, run the complete request/invoice/payment/receipt path manually.

Do not fabricate a Licensee, debt, payment, or Receipt merely to make the graph look complete.

### Phase 3 — automate only observed pain

If manual use exposes repetitive work, automate that specific step while continuing to emit ordinary OKF Markdown.

## Decision requested

Adopt this narrow direction:

1. preserve #57 as the current conservative `quote_required` and enforcement baseline;
2. require an explicit legal grant before any `metered_public` policy can authorize Operational Use;
3. define the initial `invocation` event, `principal_skill`, retries, subagents, aborts, continuations, and outputs deterministically;
4. freeze `license_id` and an immutable policy reference in every `UsageStatement`;
5. make `license-compliance` free for compliance-only bootstrap operations;
6. keep only `UsageStatement`, `InvoiceRequest`, `Invoice`, and `Receipt` as required economic record types;
7. use Markdown links for predecessor relations and `okf-parser` for validation/graph/DuckDB;
8. leave audit architecture to #57 and preserve its human gate; and
9. add no blockchain, billing engine, signature system, custom database, or new ontology until a real transaction demonstrates the need.

The protocol is closed when it answers three questions without ambiguity: **what instrument granted the use, what event counted as use, and what immutable policy governed the transaction.**
