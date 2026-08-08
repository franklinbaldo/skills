# Behavioral eval loop

Static eval cases state what should happen. Behavioral observations record what a real agent actually did. Keep those two layers separate and iterate from evidence.

## Improvement loop

```text
write/expand static eval cases
  → run a cheap simulated-routing audit against names + descriptions
  → fix only clear contract/eval inconsistencies
  → expose the repository skills through Vercel `skills`
  → run each case repeatedly in fresh agent sessions
  → record factual SkillRoutingObservation rows
  → import with okf-parser
  → inspect routing results in DuckDB
  → change only behavior with observed evidence of failure
  → add regression/near-miss cases
  → run the benchmark again
```

This is intentionally cyclical. A benchmark is not a release ceremony; it is the feedback mechanism by which routing contracts accumulate evidence and improve over time.

Routing accuracy and output quality are different loops. First ask whether the right skill activated. Separately ask whether activating it improved the answer.

## Skill-authoring discipline

When changing a skill or its routing description, follow the current upstream `skill-creator` workflow rather than inventing a local prompt-authoring methodology. In particular:

1. diagnose the existing skill and its trigger boundary before editing;
2. use realistic positive and near-miss negative prompts;
3. change the smallest amount of instruction/description needed to explain the intended boundary;
4. preserve good eval cases instead of changing their expected result merely to make the benchmark green;
5. re-run the affected trigger evals after a change;
6. keep routing evals separate from output-quality evals.

A simulated-routing audit is a cheap diagnostic layer, not host evidence. It may use a capable model to answer “given only this catalog of skill names/descriptions, would this query cause skill X to be selected?” and may compare strict/normal/permissive interpretations to find unstable boundaries. Record such results as simulation findings, never as `SkillRoutingObservation`, and never mix simulated accuracy with Claude Code/Codex runtime accuracy.

The purpose of simulation is to find obvious contradictions, ambiguous descriptions, and valuable near-miss cases before paying for repeated live runs. It does not prove how a real agent host routes.

## Distribution/runtime boundary

Do not build an installer or Agent Skills runtime here. Use Vercel `skills` to expose the authored skills to the real agent.

For the first reference benchmark with Claude Code:

```bash
npx skills add . --agent claude-code -y
```

Do not use `npx skills use --skill <name>` for routing measurement. `skills use` explicitly selects a skill; that is useful for exercising a known skill but it bypasses the implicit-routing question being measured.

## Claude Code reference observation path

Claude Code is the first reference host because its programmatic `stream-json` session exposes the offered skill catalog and Skill tool activity. The repository adapter only translates that host-owned evidence into the tiny observation protocol expected by `routing_runner.py`.

Run one case:

```bash
python okf-agent-skills/scripts/routing_runner.py . \
  --skill revisao-minutas --case-index 1 --repetition 1 \
  --runner claude-code-stream-json -- \
  python okf-agent-skills/scripts/claude_routing_adapter.py
```

Run the full current corpus with the default five repetitions:

```bash
python okf-agent-skills/scripts/routing_runner.py . \
  --runner claude-code-stream-json -- \
  python okf-agent-skills/scripts/claude_routing_adapter.py
```

The adapter runs a fresh non-persistent Claude Code session for every attempt, permits the `Skill` tool, verifies that the target skill was actually offered to the session, and reports only whether that target was invoked. Authentication/model execution remain Claude Code concerns.

A missing target in the offered catalog is an execution/configuration error, not `observed_trigger: false`.

## Import and inspect

The runner writes factual NDJSON to:

```text
.okf/agent-skills-routing-observations.jsonl
```

Project the static corpus, import observations through the generic parser, and rebuild DuckDB:

```bash
python okf-agent-skills/scripts/project.py . .okf/agent-skills

okf-parser import .okf/agent-skills-routing-observations.jsonl .okf/agent-skills \
  --type SkillRoutingObservation --id-column observation_id --write

SPEC='.okf/contracts/{slug}.md'
okf-parser duckdb .okf/agent-skills .okf/agent-skills.duckdb okf \
  --overwrite --spec-template "$SPEC"

python okf-agent-skills/scripts/run_typed_audit.py \
  .okf/agent-skills.duckdb --output .okf/routing-audit.json
```

The audit layer derives planned runs from `SkillEval × routing_repetitions`. Pending is absence of an observation. Failed agent invocations remain failures and are never converted to false negatives.

## Measurement discipline

For the first complete benchmark, do not change skill descriptions while collecting the 5 repetitions. Finish the measurement snapshot first. Then classify each false positive, false negative, and unstable case before editing anything.

After a routing change:

1. add or preserve a static case that protects the corrected boundary;
2. preserve held-out cases where practical;
3. rerun the affected cases repeatedly;
4. periodically rerun the full benchmark to detect cross-skill regressions.

As coverage expands, prioritize skills by operational value and ambiguity rather than by directory order.
