# Template discovery and debiasing

Load this reference when choosing among Memegen templates rather than rendering a template explicitly named by the user.

## Live catalog is authoritative

The template catalog changes. Do not rely on a hardcoded shortlist or model memory for open-ended selection.

List the live catalog:

```bash
curl -s https://api.memegen.link/templates/ | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total: {len(data)}')
for t in data:
    print(f\"  {t['id']:25s} | lines={t.get('lines','?')} | {t.get('name','')}\")
"
```

Inspect a template when needed:

```bash
curl -s "https://api.memegen.link/templates/gb"
```

`shortlists.md` is a memory aid, never the candidate universe.

## True random draw

When `meme-image` is in exploration mode, randomness must come from an actual RNG, not from asking the model to "pick something random".

Use the live catalog and a system RNG:

```bash
COUNT=12 curl -s https://api.memegen.link/templates/ | python3 -c "
import json, os, secrets, sys
data = json.load(sys.stdin)
count = min(int(os.environ.get('COUNT', '12')), len(data))
rng = secrets.SystemRandom()
for t in rng.sample(data, count):
    print(f\"{t['id']}\t{t.get('lines','?')}\t{t.get('name','')}\")
"
```

For an exploration batch of five publishable candidates, draw a wider candidate set first (normally 12–20 templates), then produce **three sampled-slot candidates** from that draw plus **two editorial best-fit candidates**.

The wider draw matters: if the first three random entries are impossible for the passage, the model should not silently jump back to Drake. It should inspect the rest of the random draw and record why any sampled template was rejected.

## What may be rejected before attempting a sampled template

Keep pre-filtering intentionally narrow. The purpose of the draw is to make the model solve a joke with visual grammars it would not have selected itself.

A drawn template may be rejected before composition only when there is a concrete constraint such as:

- unsafe or demeaning baggage for the context;
- text-slot count/layout cannot express the beat without unreadable stuffing;
- the template is inherently tied to a meaning that contradicts the passage;
- the asset cannot be generated or verified;
- recent-use cooldown explicitly excludes it and the run is testing novelty.

Do **not** reject merely because a famous template seems easier or more obvious.

When rejecting a sampled candidate, keep a short trace:

```text
sampled: TEMPLATE_ID
rejected: <specific reason>
replacement: TEMPLATE_ID
```

## Family diversity

After sampling, classify finalists loosely by their visual/comedic grammar rather than only their ID. Useful families include:

- reject / prefer;
- impossible choice;
- escalation / staged realization;
- comparison / identity;
- reaction / consequence;
- confusion / misclassification;
- triumph / failure;
- smug disaster / resignation;
- dialogue / social relation;
- single-thesis placard;
- custom-scene / original visual.

A five-candidate exploration batch should normally contain at least three distinct families and no more than two candidates from one family.

This is deliberately a loose editorial taxonomy, not a new ontology that every template must be permanently registered into.

## Cooldown and anti-salience

If recent-use evidence is available, avoid repeating the same template across adjacent posts or repeated runs unless the fit is materially better.

Treat the usual highly salient templates — Drake, Two Buttons, Distracted Boyfriend, This Is Fine, Galaxy Brain and similar defaults — as ordinary candidates. They can win an editorial slot, but they do not bypass the sampled slots.

For repeated benchmark runs, record template IDs so the system can measure cross-run overlap instead of relying on the evaluator's memory.

## Choose finalists by function

Randomness creates hypotheses; it does not decide publication.

For each sampled template that survives technical/safety checks, ask what native relation the picture already communicates and write the shortest text that makes that relation useful to the passage. Then compare it with the editorial slots on:

- semantic fit;
- joke quality;
- legibility;
- freshness;
- integration with the surrounding post;
- visual novelty relative to recent memes.

A sampled candidate can lose. The important constraint is that it received a genuine attempt.

## No good stock template

If the random and editorial candidates reveal that stock-template grammar is the limitation, do not keep searching forever. Read `generation-routes.md` and consider:

1. Memegen custom background/overlay;
2. self-hosted rendering on a project-owned asset;
3. an original generated visual;
4. an optional alternate template service when its catalog materially expands the hypothesis space.

That switch is itself useful evidence: it means the missing diversity is not merely another template ID.
