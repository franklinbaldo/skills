---
type: InvoiceRequest
id: metered-public-0001-invoice-request
usage_statement: "[metered-public-0001-usage-summary](usage/usage-summary.md)"
license_id: Skill-Use-License-0.1
policy_ref: policy.yaml
policy_sha256: "sha256:1ec50793a004226e2480a9eb552fdd9821b3766738eb5f2595cbe1fa9cff6831"
covered: "3"
uncovered: "2"
blocks: "1"
requested_coverage_through: "5"
requested_at: "2026-08-10T14:59:20Z"
status: simulated_experiment
---

# Simulated InvoiceRequest — Experiment 0001

Predecessor: [cumulative UsageStatement](usage/usage-summary.md).

The governing [Operational License Addendum](operational-license.md) expressly authorizes all Experiment 0001 uses and creates no real payment obligation. The frozen [policy](policy.yaml) is used only to test the economic transition.

Inputs:

```text
usage_total = 5
free_allowance = 3
receipted_coverage_through = 0
billing_unit = 2
```

RFC formula:

```text
covered = max(3, 0) = 3
uncovered = max(0, 5 - 3) = 2
blocks = ceil(2 / 2) = 1
requested_coverage_through = 3 + 1 * 2 = 5
```

This is a simulated protocol record. It is not an Invoice, debt, collection demand, payment request to an external counterparty, or economic Receipt.
