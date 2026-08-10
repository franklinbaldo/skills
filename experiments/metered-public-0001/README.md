# Experiment 0001 — deterministic invocation metering

This corpus dogfoods the minimal `metered_public` protocol merged in #58 against real internal productive use of [`okf-agent-skills`](../../okf-agent-skills/SKILL.md).

The legal authorization is the [Operational License Addendum](operational-license.md). The economic rule is the frozen [experimental policy](policy.yaml). The policy does **not** grant Operational Use by itself.

## Question

Can the merged minimal architecture survive at least five real productive uses while producing a deterministic invocation count and auditable OKF records without a billing engine, API, custom ledger, database, daemon, new DSL, or external counterparty?

## Governed Skill

`okf-agent-skills` was selected because it is simple to observe, already participated in the RFC dogfood, separates authored facts from derived facts, and has deterministic repository-inspection surfaces. The experiment treats it as the governed principal Skill.

## Existing normative semantics under test

This experiment does not redefine `invocation`. It tests the rules already merged in the [metered-public RFC](../../docs/rfcs/0001-agentic-metered-skill-licensing.md): one productive principal-Skill attempt counts once; continuations and automatic retries under the same logical `invocation_id` do not add counts; helpers do not become principal invocations; a governed Skill given to a subagent as its own principal procedure counts separately; pre-execution routing does not count; a productive attempt that later fails or aborts counts once.

## Scenarios

The factual usage records are committed under [`usage/`](usage/):

- A — normal productive execution;
- B — continuation with multiple observable steps under one `invocation_id`;
- C — same-attempt automatic retry;
- D — helper use inside the principal attempt;
- E — productive start followed by failure/abort;
- F — optional subagent only if evidence can be made unambiguous.

Each record must preserve observable facts only: Skill/version, `invocation_id`, start time, task, retry/helper/subagent facts, outcome, the applicable RFC rule, `license_id`, and immutable policy provenance. Chain-of-thought is excluded.

## Counting

The policy uses cumulative `principal_skill` invocations with free allowance `3` and billing unit `2`.

After execution, two independent reconstructions must compute the total from the committed evidence. A disagreement is preserved as a failure result rather than edited away.

For the economic transition, the experiment explicitly starts with `receipted_coverage_through = 0` because there are no prior economic Receipts. Coverage is then calculated only with the RFC formula.

## Validation

The final corpus is checked with:

```bash
okf-parser check experiments/metered-public-0001
okf-parser inventory experiments/metered-public-0001
okf-parser graph experiments/metered-public-0001
okf-parser duckdb experiments/metered-public-0001 /tmp/metered-public-0001.duckdb --overwrite
```

Results, including any inability to run a command in the execution environment, belong in [`results.md`](results.md) and must distinguish observed output from later reconstruction.
