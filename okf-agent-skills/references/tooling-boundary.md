# Tooling boundary: Vercel skills, this repository, and okf-parser

This repository deliberately does **not** own a general Agent Skills runtime.

## Canonical responsibility split

```text
Vercel `skills` CLI
  → discovery / selection / installation / agent integration / ephemeral use

franklinbaldo/skills
  → authored SKILL.md content / bundled resources / routing and quality eval corpora
  → Agent-Skills-specific benchmark semantics

franklinbaldo/okf-parser
  → generic OKF import / validation / typed schema / DuckDB / graph / bounded writes
```

### Vercel `skills` owns distribution and agent integration

Use `npx skills` rather than adding local equivalents for:

- discovering skills in a repository;
- selecting one or more skills;
- installing skills globally or per project;
- mapping skills to supported agents and their installation paths;
- symlink/copy installation behavior;
- using a skill without permanent installation;
- listing, updating, or removing installed skills.

Representative commands:

```bash
npx skills add franklinbaldo/skills
npx skills add franklinbaldo/skills --skill software-review --agent claude-code
npx skills use franklinbaldo/skills --skill software-review --agent claude-code
```

Do not introduce a repository-specific agent registry, installer framework, compatibility matrix, temporary-skill materializer, or runtime abstraction unless a concrete requirement cannot be expressed through the upstream CLI.

There is intentionally no repository-local installer fallback. A duplicated installer/runtime is maintenance surface with no domain value; if an upstream gap appears, document the concrete gap before adding any local adapter.

### This repository owns skill semantics

Keep here what is specific to the authored skills themselves:

- `SKILL.md` instructions and descriptions;
- references, scripts, assets, and examples bundled with a skill;
- routing eval queries and expected activation boundaries;
- output-quality eval cases and rubrics;
- deterministic Agent-Skills-specific projection helpers when needed for inspection;
- a thin behavioral harness only when it measures repository-specific facts rather than replacing upstream distribution/runtime behavior.

For behavioral routing evaluation, the installed/used skill environment should be provided through `npx skills` wherever practical. The benchmark layer should observe behavior; it should not reimplement skill installation.

### okf-parser owns generic knowledge representation

Use `okf-parser` rather than local equivalents for:

- importing tabular/NDJSON observations as OKF concepts;
- structural validation;
- schema/type compilation;
- DuckDB materialization;
- graph inspection;
- bounded relational writes where applicable.

The skills repository may define domain-specific concept schemas and SQL audit views, but it should not grow a second generic importer, parser, type system, or persistence layer.

## Decision test before adding infrastructure

Before adding a helper, ask in this order:

1. Does `npx skills` already own this distribution/runtime behavior?
2. Does `okf-parser` already own this data/knowledge-representation behavior?
3. Is the remaining behavior genuinely specific to this skills corpus?
4. If yes, can it be a small deterministic helper or query instead of a framework?

If the answer to 1 or 2 is yes, reuse the existing primitive.

## Consequence for behavioral evals

The intended path is:

```text
routing eval case
  → skill made available through Vercel `skills`
  → real supported agent executes the query
  → repository benchmark records one factual observation
  → okf-parser imports the observation
  → DuckDB/audit SQL compares observations with static expectations
```

The benchmark does not need to prove that `npx skills` can install or use a skill; that is upstream behavior. Our evidence target is whether the intended skill actually activates for the repository's routing cases and whether using it improves output quality when that question is evaluated separately.
