# Upstream rules and current-practice audits

Agent Skills and Claude Code evolve. This file records how to reason about upstream rules;
it is not a frozen copy of their documentation.

Before a current-best-practice audit, verify the current sources:

- Agent Skills specification: <https://agentskills.io/specification>
- Claude Code skills documentation: <https://code.claude.com/docs/pt/skills>

Use the English documentation if a translated page appears stale or ambiguous.

## Keep the standards layers separate

### Portable Agent Skills

Treat the open Agent Skills specification as the portability baseline. A field or constraint
that belongs only to Claude Code must not be described as universally required by Agent
Skills.

### Claude Code extensions

Claude Code adds invocation, execution, dynamic-context, tool, agent, hook, and related
features beyond the portable core. Inspect them when the target corpus is for Claude Code,
but label them as implementation-specific.

### Repository policy

A repository may impose stricter rules. Those are legitimate, but must be reported as local
policy rather than upstream conformance.

## High-value audit dimensions

### Discovery metadata

Check whether `description` states both capability and intended use clearly enough for model
routing. Where current Claude Code exposes `when_to_use`, inspect the pair rather than one
field in isolation.

Do not use keyword counting as a quality proxy. Behavioral trigger/no-trigger evals are the
stronger test.

### Progressive disclosure

The entry point should remain focused and supporting material should load only when needed.
Use current upstream guidance for numeric recommendations such as line-count thresholds; do
not hard-code a recommendation as a permanent conformance limit.

Useful relational observations include:

- `SKILL.md` line count;
- supporting-reference count;
- maximum link depth from the entry point;
- large entry points with no supporting references;
- references not reachable from `SKILL.md`.

These are review signals, not automatic proof of bad design.

### Supporting files

A bundled file is most useful when the entry point tells the agent what it is and when to
read or run it. Flag unreferenced scripts/references as candidates, not defects: some runtimes
or workflows may discover them through another mechanism.

### Deterministic work

Repeated fragile transformations are better candidates for scripts than for regenerated
one-off code. The presence of a script alone does not prove the skill is well designed;
inspect whether the procedural boundary makes sense.

### Invocation and side effects

When a skill performs consequential actions, inspect current invocation controls, tool
restrictions, confirmation behavior, and isolation features supported by the target runtime.
Do not infer a security violation solely from the presence of `allowed-tools`, hooks, or a
script.

### Context isolation

Where Claude Code supports forked/subagent execution, consider whether isolation matches the
workflow. A reasoning/reference skill may need conversation context; an independent research
or anti-anchoring task may benefit from a fresh context.

### Behavioral evals

Static analysis can find malformed metadata and structural smells; it cannot prove correct
routing or instruction following. Prefer real eval cases for:

- should trigger;
- should not trigger;
- expected output/behavior;
- representative difficult cases.

Project those cases into OKF when useful for inventory and coverage analysis, but keep model
execution and scoring as a separate step.

## Rule authority in reports

Every reported item should carry one of these labels:

| Class                   | Meaning                                        | Default severity             |
| ----------------------- | ---------------------------------------------- | ---------------------------- |
| Upstream requirement    | Required by the targeted specification/runtime | Error when verified          |
| Upstream recommendation | Published guidance, not conformance            | Advisory                     |
| Repository policy       | Locally chosen requirement                     | Depends on repository policy |
| Observation             | Structure/metric with no rule attached         | Informational                |

If documentation is unclear or changed recently, downgrade the claim until verified. Never
launder a remembered recommendation into a normative rule.
