---
name: ruff-strict-compliance
description: >-
  Enforces strict, zero-warning compliance with Ruff linting and formatting.
  Use when writing or editing Python in a Ruff-linted project, fixing `ruff check`
  or `ruff format` failures, or when tempted to add `# noqa` / dismiss a warning
  as stylistic or irrelevant.
---

# Ruff strict compliance

Use this skill to finish Python work with **zero enabled Ruff violations and canonical formatting**, without hiding diagnostics.

## Always-needed contract

1. **Treat enabled diagnostics as work, not commentary.** If the project enables a rule and Ruff reports it, fix the underlying code or explicitly determine that the project configuration itself should change.
2. **Do not suppress by reflex.** Do not add `# noqa`, `# type: ignore`, blanket per-file ignores, or equivalent bypasses merely to make CI green.
3. **Rare suppression requires justification.** If a library/framework genuinely requires a construct Ruff cannot express cleanly, explain the conflict and get explicit user approval before adding a narrow suppression.
4. **Respect the repository's configuration.** Read `pyproject.toml`, `ruff.toml`, or `.ruff.toml` before assuming which families are enabled or what Python version is targeted.
5. **Prefer semantics-preserving refactors.** A lint fix must not silently change runtime behavior, public API, error handling, security properties, or supported Python versions.
6. **Verify after editing.** Run the repository's Ruff commands before declaring the task complete.

## Workflow

1. Inspect the project's Ruff configuration and supported Python version.
2. Run the relevant check to obtain the actual diagnostics rather than guessing from memory.
3. Group violations by rule/code and fix the underlying patterns.
4. When a concrete rule needs an implementation recipe, consult [`references/rule-recipes.md`](references/rule-recipes.md). Do not load the entire recipe catalog preemptively.
5. Re-run formatting and linting after edits.
6. If Ruff's auto-fix is used, inspect the resulting diff; `--fix` is a transformation tool, not proof that behavior stayed correct.
7. Run relevant tests/type checks when the refactor can affect behavior.

## Configuration boundary

Ruff's default rule selection is intentionally small; many strict families are opt-in. Never infer that a repository wants `ALL` merely because this skill knows how to fix those diagnostics.

If the repository has no Ruff configuration and the user wants strict enforcement, propose a configuration appropriate to that project. The example families and migration patterns live in [`references/rule-recipes.md`](references/rule-recipes.md).

If an existing configuration intentionally ignores a rule, respect that as repository policy unless the task is specifically to reconsider the lint policy.

## Suppression decision gate

Before any suppression, all of these must be true:

- the diagnostic is produced by the repository's current Ruff configuration;
- a normal refactor is impossible or materially worse for a concrete reason;
- the suppression is as narrow as possible;
- the reason is documented where a future maintainer can understand it;
- the user explicitly approves it.

Otherwise, fix the code.

## Rule-specific guidance

The entry point deliberately does not carry recipes for B008, B006, BLE001, TRY, PTH, RUF012, C4, RET, SIM, UP, A, G, S, ERA and similar families. Those branches are conditional on the diagnostics actually present.

Read [`references/rule-recipes.md`](references/rule-recipes.md) when one of those rules appears, or when configuring strict Ruff from scratch. For unfamiliar or version-sensitive diagnostics, prefer the current Ruff documentation over a memorized recipe.

## Definition of Done

Python work under this skill is complete when:

- the repository's configured Ruff formatter/check commands succeed;
- no new bypass suppression was added without the explicit exception gate above;
- fixes preserve intended behavior and supported Python versions;
- relevant tests/type checks pass when the lint refactor could affect them;
- any proposed lint-policy change is distinguished from ordinary code remediation.

The goal is not to satisfy Ruff cosmetically. It is to leave code that naturally satisfies the repository's chosen static contract.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
