# Real-blog variance round 0002

Date: 2026-08-10

Status: **E2E attempted; canonical stochastic phase blocked by evidence transport. Do not count this as a completed full-catalog benchmark.**

Purpose: run the stricter follow-up to `blog-round-0001.md` against real published material and, crucially, test whether the benchmark itself refuses to turn a partial observation into a canonical result.

## Corpus read and selected

Three published posts were selected after reading their current text:

1. `franklinbaldo/franklinbaldo.github.io/src/content/blog/a-licenca-que-bate-na-porta.md` — technical/software + licensing essay; strong comic beats embedded in explanatory prose.
2. `franklinbaldo/franklinbaldo.github.io/src/content/blog/bibliotecario-do-infinito.mdx` — cultural/music/Borges post; lyrical body followed by composer's notes.
3. `franklinbaldo/franklinbaldo.github.io/src/content/blog/eu-comprei-uma-shitcoin-e-agora.mdx` — short playable-experiment launch post with an already comic voice.

The third post was designated the initial **no-meme control**. The editorial hypothesis is intentionally counterintuitive: being meme-friendly is not the same as needing an image meme. Its prose already carries the jokes and the article is short enough that an inserted reaction image risks becoming the dominant object.

## Live catalog observation

The live Memegen endpoint was queried on 2026-08-10:

`https://api.memegen.link/templates/`

The service documentation identifies that endpoint as the full list of renderable templates, and the response was observed live. A secondary current integration describes the catalog as 170+ templates.

However, this execution environment exposed the response only through a browsing representation. The 93,702-byte JSON response could be viewed, but the environment explicitly refused to materialize `application/json` into the local runtime. Therefore the response could not be handed intact to `secrets.SystemRandom().sample(...)`.

That distinction matters. A model-visible response is **not** equivalent to a machine-bound sampling population.

### Canonical decision

The round therefore records:

- live catalog observed: yes;
- exact machine-counted population: **not established in the RNG runtime**;
- real RNG over the complete live response: **not executed**;
- canonical draws: **none**.

The benchmark must fail closed here. Claiming a canonical draw from model-selected IDs, from a remembered shortlist, or from a search-result subset would reproduce exactly the failure that PR #73 was meant to eliminate.

## Diagnostic fallback — explicitly noncanonical

To test the rest of the loop without laundering the limitation, a search-derived set of 97 current upstream `templates/*/config.yml` IDs was assembled. It is not the complete service catalog and therefore is **not benchmark evidence**.

A system CSPRNG (`secrets.SystemRandom`) produced five independent wider draws of 12 IDs from that 97-ID diagnostic population:

1. `ds, sb, joker, ants, fine, fmr, ski, waygd, cake, light, gears, elmo`
2. `cmm, apcr, 3hd, dbg, xy, wonka, fa, stew, gru, ski, nice, fmr`
3. `slap, ams, yuno, fine, waygd, live, bs, stew, ermg, soa, ive, fmr`
4. `chair, noah, made, apcr, atis, doge, fry, bus, bd, ski, waygd, light`
5. `scc, sf, aag, pool, bihw, xy, leo, stop, buzz, oprah, mb, gru`

Raw template overlap across these wider draws is low, but that number is deliberately not promoted to the canonical variance metric: the population is incomplete and search-derived.

This fallback was useful for one reason: it demonstrates that **RNG provenance alone is insufficient**. A real RNG over the wrong population is still the wrong experiment.

## Editorial and modality inspection

### `A licença que bate na porta`

Strongest insertion beat: the section where a four-record metering protocol nearly expands into an ERP-like architecture of named entities.

The passage already contains the punch line: a tiny licensing problem begins turning into an enterprise system because types acquire PascalCase gravity.

Modalities considered:

- classic template: viable, especially grammars about escalation, overengineering, or confidently constructing too much;
- custom/composition: potentially stronger than a stock reaction because the joke is structural — a tiny four-node protocol visually exploding into an absurd enterprise architecture;
- original visual: also promising for exactly that reason; a generated pseudo-enterprise architecture could express the joke without borrowing a famous face;
- generic witty writing: redundant, because the prose already contains the joke.

Publication judgment: **there is room for one image here, but only after the canonical sampled slots compete with the custom/original route.** No blog edit was made from this incomplete run.

### `Bibliotecário do Infinito`

Strongest possible beat: the composer's note describing progressive rock and baião as sometimes sounding like "duas músicas tocando em salas separadas" while trying to organize chaos with noise and meter.

Modalities considered:

- classic template: possible but likely to flatten the very specific musical joke into generic comparison grammar;
- custom/composition: strong candidate — two adjacent rehearsal rooms, one prog and one baião, with the library acting as the impossible score;
- original visual: strongest hypothesis because the source image can carry Borges/library/music specificity;
- generic witty writing: again weaker than the existing line.

Publication judgment: **custom/original deserves to compete, stock template is not obviously the right medium.** No image was published from the blocked stochastic phase.

### `Eu comprei uma shitcoin. Agora preciso descobrir quando o dev vai me roubar.`

This post already contains several meme-shaped lines in prose: "Não compre shitcoin. / Excelente. Obrigado. Mas e se eu já comprei?", "Muito mais saudável. Claramente.", the liar-with-a-GPU line, and the final poker comparison.

A stock reaction image can be made to fit almost trivially. That is precisely why this is a useful negative control.

Publication judgment: **no meme**. Any candidate must beat not an empty slot but already effective comic pacing. The likely outcome is that the image adds recognition while subtracting speed. The control therefore survives editorial review.

## Generic-humor adversary

The round explicitly tested the idea of adding another witty sentence rather than an image. In all three posts that route was weak evidence for `meme-image`:

- the licensing post already has the ERP/SAP-style prose joke;
- the Borges/music post already has the "two rooms" line;
- the Rug Pull post is saturated with dry punch lines.

This exposes a useful boundary: `meme-image` should not reward an evaluator merely for producing another funny sentence. The visual must contribute a visual/comedic relation that the prose does not already provide.

## Subjective judging

The same model performed generation-side ideation and judging in this round; there is no claim of independent judgment.

For the three editorial decisions above, the decisive dimension was **willingness to publish at that exact location**, not whether a plausible joke could be generated.

Current ranking:

1. licensing ERP beat — image likely useful, modality undecided;
2. Borges two-rooms beat — image may be useful, custom/original likely beats stock;
3. Rug Pull — no image wins.

## What failed, and why it is useful

The important failure is not "network unavailable". The live catalog was available to the browsing layer.

The failure is an **evidence-transport boundary**: the benchmark says "sample the live catalog with real RNG", but it did not previously require evidence that the exact catalog object counted and reported is the same object passed to the RNG.

Without that invariant, an agent can accidentally produce convincing-but-false evidence by:

1. browsing the full catalog;
2. separately obtaining a convenient subset;
3. using a real RNG on the subset;
4. writing "real RNG + live catalog" in the report.

This round refused that equivalence.

## Benchmark improvement proposed by this round

Add a **sampling-population integrity gate** to stochastic evals.

A canonical run must preserve, in one evidence record:

- catalog endpoint;
- retrieval timestamp;
- exact population count;
- stable digest of the serialized ID population (or the serialized population itself when practical);
- RNG method;
- draws and replacements;
- an assertion that draws were sampled from that exact digested population.

If those cannot be established, status is `diagnostic_noncanonical`, not `canonical`.

This is more valuable than another easy prompt: it detects a class of fake rigor that the existing `randomness-audit` case does not.

## Variance metrics

Canonical metrics are intentionally **not reported** because the population-integrity precondition failed.

Diagnostic five-run observations from the 97-ID fallback may be retained for debugging, but must not be compared against future full-catalog results.

## Lateral expansion conclusion

No new sister skill is justified yet.

There is a real recurring handoff boundary around `conceptual illustration` / `generated visual satire`: the Borges and licensing beats both suggest that a visual relation can matter more than recognizable-template grammar. But two examples are not enough to establish an independent trigger boundary and definition of done.

For now this remains a route/handoff inside `meme-image`:

`meme-image -> custom composition / image generation`

## Publication / PR decision

No blog PR was opened from this round because the canonical sampled candidates never existed. Publishing an editorial-only winner would defeat the central experimental question of the session.

This is a deliberate negative result, not a plan for future work: the E2E exercised the live-catalog boundary, the benchmark rejected invalid evidence, three real posts were editorially judged, a no-meme control was resolved, modality boundaries were inspected, and a concrete benchmark defect was found.

The next canonical run should start only when the catalog response can be materialized into the same runtime that performs the RNG. At that point the already-selected corpus can be reused, but the sampled draws must be new.