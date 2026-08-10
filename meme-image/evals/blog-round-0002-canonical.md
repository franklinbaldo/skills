# Real-blog variance round 0002 — canonical completion

Date: 2026-08-10

This document completes the blocked round recorded in `blog-round-0002.md`. The earlier file remains useful evidence because it records the benchmark correctly failing closed at an evidence-transport boundary. This continuation records the later canonical execution rather than rewriting that history.

Publication candidate: `franklinbaldo/franklinbaldo.github.io#1524`

Sampling runner: `franklinbaldo/skills#77`

## Canonical population evidence

GitHub Actions run `31396573396` fetched the exact live response from:

`https://api.memegen.link/templates/`

The runner persisted the raw response and passed the parsed contents of those exact bytes directly to `secrets.SystemRandom`.

Evidence:

- HTTP status: `200`
- content type: `application/json`
- raw bytes: `93,702`
- raw-response SHA-256: `f0c34ea6bef2fbffba5ee3f282292391f0a43e19cd3625479bc7a766016f3627`
- population count: `212` response entries
- population semantics: response entries are the population; duplicates, if present in the live response, are preserved rather than silently deduplicated
- RNG: `secrets.SystemRandom`
- Actions artifact: `meme-image-canonical-sampling`, artifact id `9065850905`
- artifact digest: `sha256:d5456771d1f5ec03f8262f8442384285d13ea2dae37153835250a6b19e388811`

This satisfies the `sampling-population-integrity` gate introduced by round 0002: the population observed, counted, digested, persisted, and sampled is one object rather than several loosely related observations.

## Corpus

The same three published posts from the blocked attempt were retained so the new stochastic evidence tests the same editorial hypotheses:

1. `A licença que bate na porta` / `The License That Knocks`
2. `Bibliotecário do Infinito` / English counterpart
3. `Eu comprei uma shitcoin. Agora preciso descobrir quando o dev vai me roubar.`

The Rug Pull post remains the predeclared no-meme control.

## Post 1 — licensing essay

Target beat: the passage where a four-record Markdown protocol starts accreting enough PascalCase entities to resemble an enterprise system, immediately before the essay asks what `okf-parser` already does.

Canonical wider draw (20):

`spiderman, ggg, center, away, ermg, oprah, bihw, fmr, light, wkh, ptj, feelsgood, remembers, leo, michael-scott, bd, dwight, yallgot, kombucha, sad-bush`

### Sampled slots

1. `spiderman` — **Spider-Man Pointing at Spider-Man**
   - attempted relation: a new licensing framework points at the knowledge/parser framework already carrying much of the same machinery;
   - fit: medium; recognizable, but the native identity/duplication grammar is only adjacent to the overengineering joke.

2. `ggg` — **Good Guy Greg**
   - attempted relation: already having graph/DuckDB/projection machinery and choosing not to build a second enterprise stack;
   - fit: medium-low; the social-credit grammar makes the joke feel generic.

3. `center` — **What is this, a Center for Ants?!**
   - text PT: `O que é isso?` / `Um ERP para quatro arquivos Markdown?`
   - text EN: `What is this?` / `An ERP for four Markdown files?`
   - fit: very high; the template's native joke is absurd mismatch of scale, exactly the local argument.
   - publishability: high.

Sampled survival: `3/3` received genuine compositions; no replacement was needed.

### Editorial slots

4. `gru` — **Gru's Plan**
   - escalation from “meter four records” through more entities to “interplanetary SAP”;
   - semantically strong, but it repeats the paragraph's sequence rather than compressing it.

5. custom composition — `evals/assets/round-0002-license-custom-composition.svg`
   - four small Markdown records feed an absurd architecture of plans, assessments, engines, buses, and an “INTERPLANETARY SAP” box;
   - more passage-specific than any stock template, but slower to parse than `center` and closer to diagram-as-joke than meme language.

### Generic-humor adversary

Plain-text alternative: `Parabéns: quatro arquivos Markdown e você reinventou o ERP.`

It is a competent extra joke but loses because the paragraph already says essentially this. `center` contributes a visual scale grammar rather than another paraphrase.

### Pairwise publication judgment

`center` > custom composition > `gru` > no insertion > `spiderman` > generic witty sentence > `ggg`.

The same model generated/curated and judged these candidates; this is an editorial comparison, not an independent statistical evaluation.

**Winner: sampled `center`.** Applied in the PT/EN pair in blog PR #1524.

## Post 2 — Bibliotecário do Infinito

Target beat: the composer's self-critique that progressive rock and baião sometimes sound like two songs playing in separate rooms because the baião rhythm remained ornamental instead of structurally integrated.

Canonical wider draw (20):

`scc, handshake, touch, ski, awkward-awesome, kermit, made, balloon, gb, patrick, awesome, reveal, older, mouth, keanu, dragon, michael-scott, apcr, bihw, mordor`

### Sampled slots

1. `scc` — **Sudden Clarity Clarence**
   - attempted relation: realization that “fusion” was actually two adjacent arrangements;
   - fit: medium-high; good realization grammar, but visually generic.

2. `handshake` — **Epic Handshake**
   - rejected before final composition: the template natively means successful union/common ground, while the passage's explicit claim is failure to integrate;
   - replacement draw: `ski`.

3. `touch` — **Principal Skinner**
   - attempted relation: “Is the arrangement failing to integrate the genres? No, the genres are wrong.”
   - technically workable, but it contradicts the passage's self-critical voice and therefore scores low on authorial fit.

Replacement `ski` — **Super Cool Ski Instructor**
   - text PT: `Se o baião é só adorno` / `Você vai ter duas músicas em salas separadas`
   - text EN: `If baião is only decoration` / `You're gonna get two songs in separate rooms`
   - fit: high; warning/consequence grammar preserves the craft diagnosis instead of flattening it into a generic comparison.

Initial sampled survival: `2/3`; one concrete semantic mismatch caused one replacement. Final sampled slots: `3/3` composed.

### Editorial / modality slots

4. custom split-room composition — the core relation is two adjacent rehearsal spaces with no actual musical crossing. It is specific but risks merely illustrating the sentence.

5. original visual — `evals/assets/round-0002-librarian-original-visual.svg`
   - procedurally authored original scene: two hexagonal library/rehearsal rooms, prog-rock symbols on one side and baião rhythm on the other, with sound waves stopping at the central wall;
   - provenance: original SVG authored for this E2E, not a stock meme and not a diffusion-model output;
   - specificity: very high;
   - meme-language fidelity: lower than `ski`; it reads as conceptual illustration first and joke second.

This is useful negative evidence for lateral expansion: higher specificity alone does not mean `meme-image` should become `conceptual-illustration`.

### Generic-humor adversary

Plain-text alternative: `A fusão aconteceu; só esqueceram de reservar o mesmo cômodo.`

Funny enough, but redundant with the existing “salas separadas” sentence and weaker than either a real meme grammar or no insertion.

### Pairwise publication judgment

`ski` > original two-room visual > no insertion > `scc` > generic witty sentence > `touch`.

**Winner: sampled replacement `ski`.** Applied in the PT/EN pair in blog PR #1524.

## Post 3 — Rug Pull Simulator launch post

The canonical wider draw was:

`spirit, captain, philosoraptor, aint-got-time, spongebob, panik-kalm-panik, rollsafe, country, bs, spiderman, scc, touch, saltbae, pool, michael-scott, bilbo, yodawg, fmr, disastergirl, light`

### Sampled slots

1. `spirit` — **Fake Spirit Halloween Costume**
   - can turn “EXIT LIQUIDITY” into a costume assembled from “already bought”, “position -7%”, “dev online”, etc.; genuinely funny but visually heavy for a short launch post.

2. `captain` — **I am the Captain Now**
   - strongest sampled line: `Look at me / I am the exit liquidity now`;
   - high immediate recognition, but mostly restates the premise already compressed by the prose.

3. `philosoraptor` — **Philosoraptor**
   - can question whether selling too early turns profit into a different kind of loss;
   - thematically compatible but adds abstraction where the post already moves quickly.

All three sampled slots survived to genuine candidates.

### Editorial slots

4. `rollsafe` — rationalization grammar around selling before the dev can rug you.
5. `panik-kalm-panik` — market down / announcement / wallet movement escalation.

Both fit almost too easily. That is why this is a good negative control.

### No-meme control and generic-humor adversary

The post already has: “Não compre shitcoin. / Excelente. Obrigado. Mas e se eu já comprei?”, “Muito mais saudável. Claramente.”, the liar-with-a-GPU line, and the closing poker comparison.

An extra witty line or reaction image adds recognition while subtracting speed. The article is short enough that an image would become a disproportionately large object.

**Winner: no insertion.** Blog PR #1524 deliberately leaves this post unchanged.

## Five repeated full-catalog runs

Five additional independent 20-entry draws were captured for the licensing beat. For the variance metric below, the first three sampled slots of each run are treated as the binding first-pass slots:

1. `waygd, awesome, mw`
2. `jim, right, wddth`
3. `right, because, puffin`
4. `touch, nice, grumpycat`
5. `success, remembers, rollsafe`

Metrics:

- sampled slots observed: `15`
- distinct sampled template IDs: `14`
- distinct-template ratio: `14/15 = 0.933`
- only repeated sampled ID: `right`, appearing in runs 2 and 3
- mean pairwise Jaccard overlap of the five three-template sampled sets: `0.02`
- replacements required at the draw layer: `0` for these first-pass variance measurements
- highly salient default collapse: not observed; no Drake, Two Buttons, Distracted Boyfriend, This Is Fine, or Galaxy Brain appears in these fifteen first-pass slots

Family-level reading is also diverse rather than merely ID-diverse: resignation/reaction, social success, confident assurance, placard/explainer, dialogue expectation, boundary rejection, dialogue twist, thesis placard, self-justifying denial, consolation, negative reaction, triumph, recollection, and rationalization all appear.

The one repeated ID (`right`) is therefore not evidence of family collapse.

## Render verification

Blog PR #1524 used a one-shot GitHub Actions job to apply the paired changes and fetch all four publication URLs from Memegen. Job `93482805454` completed successfully; its `Verify rendered meme assets` step passed for all four images before the workflow removed itself from the branch.

The final PR diff contains four content files only: two PT/EN pairs. The Rug Pull control remains unchanged.

## Modality competition conclusion

This round exercised all three intended modality classes:

A. classic template — `center`, `ski`, and the other sampled/editorial stock candidates;

B. custom composition — the licensing faux-enterprise architecture SVG;

C. original visual — the procedurally authored two-room infinite-library visual.

The important result is not “templates always win.” They won these two publication decisions because their native visual grammar compressed the joke faster. The custom/original routes exposed a neighboring job — conceptual illustration / diagram-as-joke — but did not yet demonstrate that `meme-image` should own it.

## Benchmark / methodology result

The earlier blocked attempt produced the strongest methodological improvement of the cycle: `sampling-population-integrity`. This canonical continuation validates that the gate is practical, not merely theoretical.

Additional evals introduced in round 0002 also received real exercise:

- `no-meme-control`: passed; Rug Pull remains image-free;
- `generic-humor-adversary`: passed; extra witty prose did not win merely for being funny;
- `modality-competition`: exercised with stock, custom composition, original visual, and none;
- `blind-publishability-pairwise`: not claimed as independent because the same model had access to candidate provenance during the session. Future rounds should use a genuinely separate/cross-model judge if independence matters.

This explicit non-result matters: hiding labels in a prompt would not create statistical independence from a judge that already generated the candidates.

## Lateral expansion conclusion

No sibling skill is justified yet.

The repeated neighboring capability is clearer now: `conceptual illustration` / `diagram-as-joke` can outperform templates on passage-specific visual relations, but the two original/composition experiments still do not establish a stable trigger boundary and definition of done independent from existing visual/diagram work.

Keep the current handoff:

`meme-image -> custom composition / conceptual illustration / image generation`

Do not create a new skill until repeated evidence shows a coherent job rather than a route.

## Cycle result

- real E2E: completed
- canonical full-catalog population: recorded and digested
- true RNG: executed against that exact population
- three distinct posts: evaluated
- repeated stochastic runs: 5
- classic template modality: tested
- custom composition modality: tested
- original visual modality: tested
- explicit no-meme control: passed
- generic-humor adversary: tested
- PT/EN publication edits: staged in blog PR #1524
- sampled discoveries published in PR: `center`, `ski`
- new benchmark gate from the failure: validated
- new sibling skill: not justified

Failures and rejections remain evidence rather than being erased from the successful continuation.
