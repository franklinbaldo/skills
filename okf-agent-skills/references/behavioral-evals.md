# Behavioral eval loop

Static eval cases state what should happen. Behavioral observations record what a real agent actually did. Keep those two layers separate and iterate from evidence.

## System invariant: benchmark R&D is part of the product

The evaluation system is responsible not only for diversifying the benchmark, but for **inventing better ways to test skills**. Benchmark design is an active research-and-development concern of the system itself.

Every improvement cycle must ask three separate questions:

1. **What should change in the skill?**
2. **What new or harder cases should enter the benchmark?**
3. **What new evaluation method, axis, adversarial setup, comparison, or measurement could reveal failures the current benchmark cannot see?**

A cycle is incomplete if it only makes the existing corpus greener or merely adds more paraphrases. The system should actively search for previously unmeasured dimensions of failure and create new benchmark forms when useful.

Examples of benchmark innovation include, but are not limited to:

- moving from isolated prompts to multi-turn continuation routing;
- testing competition among several plausible skills instead of one-vs-rest cases;
- measuring whether a skill is loaded too early, too late, or unnecessarily;
- introducing ambiguity gradients rather than only binary easy/hard examples;
- evaluating robustness to compressed, noisy, typo-heavy, multilingual, or code-switched requests;
- generating adversarial prompts from observed false positives/negatives instead of hand-writing only obvious cases;
- testing routing under changing catalog composition, including new neighboring skills;
- measuring calibration/uncertainty when the routing decision is genuinely ambiguous;
- comparing multiple hosts/models as separate behavioral environments;
- inventing quality rubrics, pairwise comparisons, counterfactual no-skill baselines, mutation tests, or other eval forms when routing accuracy is no longer the main uncertainty.

The benchmark system should periodically audit its own blind spots. If all existing metrics are saturated, that is a prompt to invent a better test, not a reason to declare the skill finished.

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
  → strengthen the benchmark with new adversarial/held-out cases
  → invent new benchmark methods when the current ones saturate or miss important behavior
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

## The benchmark must evolve too

Do not optimize skills against a frozen test set. A routing benchmark that stays easy while descriptions are repeatedly tuned becomes a memorized specification, not evidence of generalization.

After each improvement cycle, strengthen the benchmark from the failure modes that were learned without rewriting history. Prefer adding cases over mutating old ones when the old expectation was valid.

Grow the benchmark along several independent axes:

- **new phrasings** — same intent expressed without the nouns/verbs that appear in the skill description;
- **hard negatives** — prompts that mention the domain but ask for a neighboring capability;
- **cross-skill collisions** — prompts plausibly matching two or more skills where only one should win, or where both may legitimately be relevant;
- **continuations** — follow-up prompts whose routing depends on prior work rather than explicit restatement of the task;
- **underspecified prompts** — realistic short requests where the model must infer whether loading a skill is justified;
- **language/register variation** — Portuguese/English, formal/informal, terse/verbose, typo/noisy forms when realistic;
- **adversarial paraphrases** — prompts intentionally avoiding trigger words while preserving the target intent;
- **out-of-domain controls** — clearly unrelated work to detect descriptions that have become too broad.

### Keep a moving frontier, not a moving goalpost

Old cases remain regression tests unless their expected behavior was genuinely wrong. When an expectation changes, document why the contract changed rather than silently relabeling the case.

Newly generated cases should initially be treated as challenge/validation cases. Do not use every new case immediately to tune the description that will be scored against it. Keep some cases held out until after the candidate change is written.

A useful cycle is:

```text
known/train cases
  → candidate description change
  → held-out challenge cases
  → live repeated runs
  → promote useful challenge cases into permanent regression corpus
  → generate a harder held-out frontier
  → propose at least one new evaluation angle when useful
```

The corpus should therefore tend to grow in both **coverage** and **difficulty**, while the benchmark methodology itself grows in **expressiveness**. A lower score on a materially harder or more revealing benchmark may represent progress.

### Measure benchmark quality, not only model accuracy

Track at least:

- number of skills with routing coverage;
- positive/negative balance by skill;
- number of hard-negative and cross-skill cases;
- number of held-out/challenge cases not used for the latest tuning step;
- semantic diversity rather than raw case count alone;
- instability across repeated real-agent runs;
- cases that have become trivial because they nearly quote the skill description;
- number of distinct evaluation modes/axes in active use;
- benchmark blind spots discovered and newly covered;
- whether a newly introduced benchmark method changed what the team learned about a skill.

Do not reward benchmark growth by case count alone. Ten paraphrases of the same obvious trigger are weaker than one realistic collision that exposes an ambiguous boundary; likewise, one new benchmark method that reveals an unseen failure mode can be more valuable than dozens of additional cases in an already-saturated format.

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

1. preserve the old valid regression cases;
2. add new cases that target the learned failure without quoting the fix;
3. keep a held-out frontier where practical;
4. rerun the affected cases repeatedly;
5. periodically rerun the full benchmark to detect cross-skill regressions;
6. generate a harder challenge set before the next optimization cycle;
7. ask whether the current benchmark format itself is now the limiting factor and, if so, invent a better one.

As coverage expands, prioritize skills by operational value and ambiguity rather than by directory order.
