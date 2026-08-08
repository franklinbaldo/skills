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

This RFC is stacked on the experiment introduced by [Skill Use License 0.1](../../LICENSE.md), its [machine-readable policy](../../licensing/policy.yaml), and the [license-enforcement skill](../../license-enforcement/SKILL.md).

It does not replace the `quote_required` baseline. It proposes one additional experiment: a deterministic `metered_public` path that an agent can follow without bespoke negotiation.

The human-control rule from the baseline remains unchanged: an agent may investigate and prepare, but publication of an adverse finding, external notice, collection demand, takedown, or legal escalation about a third party requires explicit human approval.

## Summary

Keep the protocol small.

A metered Skill needs only four things:

1. a public policy that says exactly how usage is counted and priced;
2. a `license-compliance` Skill that teaches the Licensee how to comply;
3. a few ordinary OKF Markdown records for usage, invoicing, and payment; and
4. `okf-parser` as the generic parser, validator, graph, schema, and DuckDB projection layer.

No licensing framework, custom ledger service, bespoke database, or domain-specific parser is proposed.

The ordinary path is:

```text
Skill use
  -> UsageStatement
  -> InvoiceRequest
  -> Invoice
  -> payment
  -> Receipt
```

The existing `license-enforcement` path remains the independent verification path. This RFC does not create a second audit framework.

## Use `okf-parser`, do not rebuild it

Protocol records are ordinary `.md` files with OKF frontmatter and Markdown links.

The repository should rely on existing `okf-parser` capabilities:

```bash
okf-parser check .
okf-parser inventory .
okf-parser graph .
okf-parser schema . --format pydantic
okf-parser duckdb . okf.duckdb --overwrite
```

If type specifications become useful, use the existing OKF specification mechanism and `--require-spec` / `--spec-template`. If typed SQL projection becomes useful, use the existing `.schema.sql` support.

The licensing experiment MUST NOT introduce:

- a second schema language;
- a custom graph implementation;
- a custom relational model parallel to the `okf-parser` DuckDB projection;
- a licensing-specific parser inside `okf-parser`; or
- generated application models unless a real consumer needs them.

The first implementation should be inspectable as Markdown and queryable through `okf-parser` before any automation is added.

## The policy is the economic rule

`metered_public` is valid only when two conforming implementations given the same facts can reach the same billing result.

For the first experiment, do not make the metering model configurable in every possible dimension. Choose one concrete rule and publish it.

Illustrative policy:

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

Under this example:

```text
uses 1..1000     free
uses 1001..2000  first paid block
uses 2001..3000  second paid block
```

If cumulative usage reaches `1427`, the Licensee requests one paid block and, once paid and receipted, coverage advances through `2000`.

Use `1428` does not trigger another Invoice. The next uncovered use is `2001`.

This closes the important ambiguity without designing a general billing engine. A future policy may choose a different rule, but that is a future RFC or policy version, not a reason to parameterize everything now.

## Free compliance bootstrap

A `metered_public` policy MUST publish a `license-compliance` Skill.

Using that Skill exclusively to understand and satisfy the license MUST NOT itself create billable usage under the meter it administers.

That includes:

- reading the license and policy;
- learning what counts as one unit;
- maintaining the counter;
- producing a `UsageStatement`;
- producing or submitting an `InvoiceRequest`; and
- checking an Invoice or Receipt.

The license must not charge the Licensee for counting how many times it counted the license.

## Minimal OKF vocabulary

The first experiment needs four public record types.

### `UsageStatement`

A bounded statement by the Licensee about its own measured use.

```md
---
type: UsageStatement
id: usage-2026-0042
skill: ../skills/legal-review.md
licensee: did:key:example
metric: invocation
usage_total: 1427
covered_through: 1000
measured_at: 2026-08-07T23:10:00Z
---

# Usage statement

The Licensee reports cumulative usage of 1,427 invocations.
```

Raw logs may remain private. The statement does not become true merely because it is signed or committed to Git.

### `InvoiceRequest`

A request derived from a `UsageStatement`.

```md
---
type: InvoiceRequest
id: req-2026-0042
usage_statement: ../usage/usage-2026-0042.md
requested_coverage_through: 2000
requested_at: 2026-08-07T23:12:00Z
---

# Invoice request

Please issue the Invoice required by the published metered policy.
```

The Markdown link is the protocol relation. `okf-parser graph` should be able to see it.

### `Invoice`

The Licensor's application of the published price to the requested block.

```md
---
type: Invoice
id: inv-2026-0042
invoice_request: ../requests/req-2026-0042.md
coverage_through: 2000
amount: "0.001"
asset: WLD
status: issued
---

# Invoice

Invoice for the first paid block under the referenced request.
```

An Invoice is not a court finding.

### `Receipt`

The Licensor's statement that a payment satisfied the referenced Invoice and advanced coverage to the stated watermark.

```md
---
type: Receipt
id: receipt-2026-0042
invoice: ../invoices/inv-2026-0042.md
coverage_through: 2000
payment_reference: "0x..."
issued_at: 2026-08-08T00:03:14Z
---

# Receipt

The issuer recognizes the referenced Invoice as paid and coverage through invocation 2,000 as satisfied.
```

A signature or attestation may later strengthen provenance and integrity. It is not required to prove the conceptual model, and it does not convert the signed content into legal truth.

## What `okf-parser` should validate

Start with what already exists.

`okf-parser check` validates the OKF corpus and links. `inventory` shows the record types. `graph` exposes the chain. `duckdb` materializes it for inspection and queries. `schema` can expose the observed contract when a consumer needs generated types.

The first useful test is not a custom validator. It is a tiny real corpus in which:

```text
UsageStatement -> InvoiceRequest -> Invoice -> Receipt
```

is visible to `okf-parser graph` and inspectable in the DuckDB projection.

Only add a `.schema.sql` declaration or a small repository-specific check when a concrete invariant cannot be guarded by the existing OKF validation surface.

Examples of worthwhile invariants, if they become necessary:

- `coverage_through` never moves backwards for the same Licensee + Skill;
- one active Invoice does not duplicate an already receipted block; and
- an Invoice and Receipt link to the records they claim to settle.

Do not build those checks before the first real example demonstrates the need.

## Licensee metering

The Licensee is responsible for maintaining an idoneous counter for the published metric.

The protocol does not prescribe an observability stack.

A counter may come from an agent runtime, application log, workflow ID, database, append-only file, or another reasonable mechanism. The `license-compliance` Skill should tell the agent to use the best authorized measurement surface available in its environment and to avoid collecting unnecessary content.

For the first experiment, the public protocol only needs the aggregate `UsageStatement`.

Per-event `UsageRecord`, `MeteringPlan`, `EnvironmentAssessment`, and similar records MAY exist when useful, but they are not required protocol concepts.

## Independent audit remains #57

This RFC does not redefine the audit architecture.

The existing `license-enforcement` Skill remains responsible for investigating possible unreported use under the baseline safeguards.

The important rule is unchanged:

```text
agent investigates
  -> internal evidence / draft conclusion
  -> HUMAN REVIEW
  -> external publication/contact, if approved
```

A public finding about an identifiable third party and an audit-originated Invoice are adverse external acts. They remain behind explicit human approval.

The agent must also preserve epistemic bounds. Public evidence that establishes `at_least: 17` does not become `exact: 17`, and a signature proves who signed a statement, not that the statement is substantively true.

If audit records are later represented as OKF concepts, they should use the same ordinary Markdown/link model and `okf-parser`. This RFC does not need to specify those types now.

## Payment rails are adapters

The protocol does not depend on Pix, WLD, x402, a blockchain, GitHub Actions, or any other payment or signing infrastructure.

An Invoice states the amount and accepted rail. A Receipt records the payment reference that the Licensor recognized.

The first implementation may be completely manual.

Automation is justified only after the manual OKF path works end to end.

## Suggested repository shape

Keep it boring:

```text
LICENSE.md
license-compliance/
  SKILL.md
license-enforcement/
  SKILL.md
licensing/
  policy.yaml
  usage/
  requests/
  invoices/
  receipts/
```

If type specs become useful later:

```text
licensing/types/
  usage-statement.md
  invoice-request.md
  invoice.md
  receipt.md
```

No additional service is required.

## Implementation

### Phase 0 — RFC

Review this model while #57 remains the active `quote_required` baseline.

### Phase 1 — one OKF fixture

Create one complete example:

```text
UsageStatement -> InvoiceRequest -> Invoice -> Receipt
```

Then require:

```bash
okf-parser check licensing/
okf-parser inventory licensing/
okf-parser graph licensing/
okf-parser duckdb licensing/ /tmp/licensing.duckdb --overwrite
```

The gate is that the corpus is valid, the links resolve, and the intended chain is visible through the existing parser.

### Phase 2 — one real manual transaction

Pick one Skill, one metric, one price, and one Licensee. Run the complete path manually.

Do not add automation merely because automation is imaginable.

### Phase 3 — automate the pain that actually appeared

If manual use reveals repetitive work, automate that specific step. Possible examples are generating an Invoice from an InvoiceRequest or generating a Receipt after verified payment.

Each automation should continue to emit ordinary OKF Markdown and remain inspectable by `okf-parser`.

## Decision requested

Adopt this narrower direction:

1. preserve #57 as the conservative `quote_required` and enforcement baseline;
2. add one concrete `metered_public` policy rather than a general billing framework;
3. make `license-compliance` free for compliance-only bootstrap operations;
4. represent the ordinary economic path with only `UsageStatement`, `InvoiceRequest`, `Invoice`, and `Receipt`;
5. use Markdown links as the relations between those records;
6. use `okf-parser` for validation, inventory, graph, schema projection, and DuckDB materialization;
7. keep raw metering implementation private and unconstrained except for reliability and auditability;
8. leave audit architecture to #57 and preserve its human gate;
9. treat signatures as provenance/integrity mechanisms, not truth machines; and
10. add custom schemas, checks, signatures, workflows, or payment integrations only when a real end-to-end experiment demonstrates the need.

The protocol should first prove that four Markdown files can describe one real licensed transaction cleanly. Everything else can earn its way in later.
