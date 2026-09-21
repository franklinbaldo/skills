---
name: ai-epistemic-discovery
description: >-
  Discover and triage public GitHub users who may be building sustained AI-mediated
  epistemic worlds: internally connected systems of explanation, identity, agency,
  cosmology, spirituality, science, or meaning developed with LLMs or AI agents. Use
  when scouting new candidates for the AI Epistemic Worlds observatory. The bundled
  script generates an explainable candidate queue from public GitHub evidence; it does
  not diagnose people, validate beliefs, or qualify cases by itself.
compatibility: >-
  Requires Python 3.11+, network access to public GitHub, and preferably GITHUB_TOKEN
  for useful search volume. The script is self-contained and runs with uv via PEP 723.
---

# Discover AI-mediated epistemic worlds on public GitHub

Use this skill to find **which public GitHub users deserve deeper longitudinal reading**.
Discovery and case qualification are deliberately separate stages.

The discovery score answers only:

> Given limited research time, which public users are most likely to contain a sustained,
> internally connected, AI-mediated epistemic project worth inspecting next?

It does **not** answer whether a person's claims are true, whether their project is literal,
or whether the person has any medical or psychiatric condition.

## Golden path

1. Generate a broad candidate queue with the bundled script.
2. Read the strongest candidates directly on GitHub.
3. Reconstruct each candidate longitudinally against their own earlier public baseline.
4. Try to falsify the classification with ordinary alternatives: software project, fiction,
   art, roleplay, speculative philosophy, ordinary AI research, prompt collection, or satire.
5. Only after that review, create or update an `ai-epistemic-world` OKF record in the blog.
6. Keep intervention/convergence provenance separate and obey the blog's current gates before
   contacting any repository.

## Candidate generation

Run:

```bash
GITHUB_TOKEN="$GITHUB_TOKEN" \
  uv run <skill-dir>/scripts/find_candidates.py \
  --output-format markdown \
  --min-score 5 \
  --max-owners 30 \
  --output candidates.md
```

For a machine-readable queue:

```bash
uv run <skill-dir>/scripts/find_candidates.py \
  --output-format json \
  --output candidates.json
```

A token is strongly recommended because public unauthenticated GitHub API limits make a useful
cross-user scan very small. The script never writes the token to output.

## What the script looks for

The script searches public repositories using several independent query families, then groups
hits by GitHub owner and inspects that owner's public repository surface. Its score is additive
and explainable.

Positive discovery signals:

- **explicit AI mediation** — Claude/ChatGPT/LLM plus language such as collaborator, co-author,
  partner, co-created, or developed-with;
- **epistemic-world vocabulary** — recurring public discussion of consciousness, identity,
  selfhood, soul, ontology, epistemology, cosmology, agency, continuity, worldview, meaning,
  metaphysics, ritual, or related concepts;
- **cross-repository recurrence** — the same broad conceptual system appears across more than
  one repository rather than in a single isolated README;
- **longitudinal value** — the public account predates the apparent cluster and/or the cluster
  itself spans enough time to compare stages;
- **artifact richness** — public protocols, papers, experiments, frameworks, books, datasets,
  ledgers, simulations, memory architectures, or related durable artifacts.

Ordinary software markers can reduce priority when there is only a weak isolated hit. They are
not exclusion rules by themselves.

### Signals that must not raise the score

Psychiatric or clinical vocabulary — including `psychosis`, `mania`, `delusion`, and related
terms — contributes **zero points**. Activity bursts, commit volume, repository counts, and
streaks also do not establish a case. They may later be measured as objective public activity
metrics, but they are never psychiatric evidence and never substitute for content review.

## Why user-level aggregation matters

Repository search alone produces many false positives. The useful unit is usually a public
**trajectory**:

```text
search hit
  -> owner
  -> public repo cluster
  -> dates / earlier baseline
  -> repeated vocabulary and artifacts
  -> direct AI-role evidence
  -> alternative explanations
  -> qualified case or false positive
```

A single unusual README is weak evidence. A public sequence showing ordinary earlier work,
then the appearance of an AI-mediated conceptual vocabulary, then repeated artifacts and
recursive AI participation is much more informative.

## Manual qualification after the script

For each high-priority candidate, inspect at least:

- account and repository observation window;
- oldest relevant repository/commit and latest material update;
- earlier public repositories that can serve as a pre-world baseline;
- direct README/docs/commit/issue/PR evidence of the AI's role;
- whether concepts recur across artifacts rather than being keyword accidents;
- whether the project frames itself as literal belief, research, speculative philosophy,
  fiction, art, roleplay, satire, or leaves this ambiguous;
- whether an AI response is archived and then used to update later artifacts, which is stronger
  evidence of recursive AI-human development than mere mention of an LLM;
- alternative explanations and disconfirming evidence;
- provenance between projects so diffusion is not mislabeled independent convergence.

Do not assign an observatory evidence tier from the script score. `S/A/B/C/D/F/NR` remains a
manual evidence judgment under the blog's current OKF contract.

## Search evolution

When a newly confirmed case contains vocabulary or artifact types absent from the current
queries, first ask whether the new term is a **general discovery signal** rather than a proper
name unique to that case. Add generic signals only when they improve recall without obviously
baking known cases into the detector.

Good additions:

- a recurring generic phrase such as `identity continuity`;
- a new artifact class such as `AI constitution` or `memory seed protocol`;
- a stable phrase indicating AI co-authorship across unrelated projects.

Bad additions:

- a maintainer's name;
- a project-specific invented deity/system name;
- psychiatric labels;
- a phrase added solely because it retrieves one already-known person.

This keeps the scanner useful for discovery rather than turning it into a lookup table for the
existing catalogue.

## Integration with the observatory

When using this skill for `franklinbaldo/franklinbaldo.github.io`, read the current contracts
before any persistence or intervention, especially:

- `specs/okf-types/ai-epistemic-world.md` when present;
- `specs/okf-types/ai-epistemic-intervention.md`;
- `specs/okf-types/ai-epistemic-convergence.md`;
- `knowledge/ai-epistemic-interventions/`;
- `knowledge/ai-epistemic-convergences/`.

The blog's OKF records are the source of truth for qualification, previous contact, gate state,
provenance, and contamination. The scanner's output is disposable discovery data, not a second
semantic registry.

## Definition of done

A discovery run is useful when it leaves:

1. an explainable ranked candidate queue;
2. direct repository URLs and the signals that caused each candidate to rank;
3. enough temporal information to prioritize longitudinal review;
4. clinical language explicitly excluded from scoring;
5. no diagnostic inference;
6. no case tier assigned without direct manual review;
7. no persistent parallel tracker competing with the blog's OKF records.

## Real-use postmortem

After material use, assess recall, false-positive patterns, missed vocabulary, rate-limit
friction, and whether the score actually put worthwhile longitudinal cases near the top. Routine
success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues
and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish
private data, credentials, or psychiatric inference as feedback.
