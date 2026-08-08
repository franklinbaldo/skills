# Real-blog variance round 0001

Date: 2026-08-08

Applied in: `franklinbaldo/franklinbaldo.github.io#1510`

Purpose: exercise the exploration idea on real editorial material before treating the new variance rules as settled.

## Provenance and limitation

This first demonstration used a real system RNG over a broad **known-live template pool**, not the complete live Memegen catalog. The pool contained familiar and less-salient templates known to exist in the current service.

That is useful exploratory evidence but it is **not yet the canonical variance benchmark**. The protocol introduced by this branch is stricter: subsequent benchmark runs must sample against the complete live `/templates/` response (subject only to concrete safety/technical exclusions) and preserve the sampled IDs/replacements.

Do not compare this pilot's diversity metrics with future full-catalog runs without stratifying the sampling population.

## Post 1 — A dobra sem vinco existe

Wider draw:

`fry, buzz, tb, bus, cbg, awkward-awesome, atis, fwp, friends, stonks, pooh, interesting`

Second-stage sampled slots:

`tb, atis, fry`

Editorial slots:

`friends, bus`

Published-in-PR candidate: **sampled `atis` (And Then I Said)**

Text:

- `E então eu disse`
- `localmente invertível, então globalmente injetivo`

Subjective judgment:

- semantic fit: high — overconfident remembered claim fits the conjectural intuition;
- novelty: high relative to the project's recent meme defaults;
- legibility: high;
- register fit: medium/high — intentionally more conspicuous than the surrounding mathematical prose;
- editorial cost: acceptable because the post already has a major interactive visual, so only one image meme was used.

Interesting rejected/alternate candidate: `friends` mapped naturally to local inverse vs global injectivity, but adding it as a second image would overweight the post. This is a useful distinction between **good candidate** and **good insertion**.

## Post 2 — Three Hammers Walk Into a Bar

Wider draw:

`awesome-awkward, gb, stonks, kombucha, ackbar, fwp, success, dg, aint-got-time, aag, ants, bihw`

Second-stage sampled slots:

`stonks, ants, ackbar`

Editorial slots:

`3hd, same`

Inserted sampled candidate: **`ants` (Do You Want Ants?)**

Text:

- `Let the agent invent a verb?`
- `Do you want unenumerated powers?`

Subjective judgment:

- semantic fit: high — the template already means “this innocuous act causes the bad condition”;
- novelty: high;
- integration: high at the strict-legality / affordance-enumeration paragraph;
- discovery value: very high — this candidate would probably not have been retrieved from model salience alone.

Inserted editorial candidate: **`3hd` (Three-Headed Dragon)**

Text:

- `Lawyer`
- `Brazilian`
- `Civil servant`

It replaces a pre-existing Drake meme.

Subjective judgment:

- semantic fit: very high — the essay is literally organized around three professional identities inhabiting one person;
- novelty: medium/high compared with the existing blog meme surface;
- integration: very high;
- evidence for mixed strategy: strong. Pure randomness discovered `ants`; the editorial slot found the best title-level visual metaphor. The 3+2 design lets both discoveries coexist.

## What this round learned

1. **Binding exploration works.** A sampled template (`ants`) produced a strong candidate that ordinary salience-based selection was unlikely to surface.
2. **Editorial slots are still necessary.** `3hd` is a near-perfect fit and should not lose merely because it was not randomly sampled.
3. **Variance is not density.** The Jacobian post had several good candidates but only one earned page weight.
4. **Existing memes are useful negative evidence.** Replacing a Drake with a more semantically native template is a concrete anti-salience improvement, not novelty for novelty's sake.
5. **Sampling population must be provenance.** The pilot's known-live pool limitation became visible during the run; future benchmark rounds must use the complete live catalog.

## Next benchmark frontier

Run the same or equivalent posts through at least these experiments:

1. **Full-catalog repeated sampling** — five independent runs per post; measure cross-run overlap, sampled survival, family diversity, and subjective quality.
2. **Cooldown ablation** — compare selection with and without the last-N-used-template exclusion list.
3. **Custom-background route** — use a project-owned screenshot/visual as the meme background and compare with the best stock template.
4. **Self-hosted route** — render one selected meme locally/immutably and compare publishing durability and workflow cost against a Memegen URL.
5. **Original-visual route** — generate an original comedic scene for a beat that stock templates express poorly; compare immediate readability with a recognizable template.
6. **Alternate-catalog route** — when credentials/service boundary are acceptable, compare another template catalog such as Imgflip with Memegen. Keep credentials entirely outside repo/evidence.
7. **Animated route** — test whether a GIF/WebP template earns its extra visual weight on a post where staged timing matters.
8. **Blind subjective judging** — hide sampled/editorial provenance and template fame from the judge until after pairwise ranking.

The next goal is not merely a higher distinct-template count. It is to learn whether broader exploration produces **better surprising candidates without lowering the editorial ceiling**.
