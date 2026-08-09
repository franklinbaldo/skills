---
name: meme-image
description: |
  Generate and place image memes in blog posts, essays, and Markdown contexts using recognizable templates, custom backgrounds, self-hosted renders, or original generated visuals. Use when a post needs a visual meme beat or when the user asks to explore several meme-image candidates. Do not use for high-stakes/serious material where meme register would trivialize the subject.
---

# meme-image

Choose and generate image memes as editorial objects. The goal is not to keep reaching for the five templates that are easiest to remember. The skill should balance **fit, surprise, visual variety, and publishing durability**.

## When to use

Use when the user wants:

- a classic image meme with custom text;
- several image-meme candidates for a post;
- comparison, escalation, reaction, choice, confusion, resignation, thesis, or another visual-comedic beat;
- occasional meme-image rhythm inside long non-serious prose;
- exploration of less-obvious templates or alternative meme-generation routes.

Do not use when:

- the visual should primarily explain rather than joke (prefer a diagram/chart/explainer);
- the user wants a photograph rather than a meme format;
- the material is legal, medical, condolence/grief, abuse, suicide, or otherwise serious enough that a meme would trivialize it;
- a text meme or ordinary prose beat clearly does the job better.

## Always-needed editorial contract

1. **Choose by function, not fame.** Identify what the beat must do before final selection.
2. **Exploration must sometimes defeat salience.** In open-ended multi-candidate work, do not let the same famous templates dominate merely because they are easy to recall.
3. **The visual grammar carries meaning.** Do not force text into a template whose native joke structure does not fit.
4. **Keep line text short.** A meme is visual compression, not a paragraph renderer.
5. **Accessibility remains required.** Every embedded meme needs useful alt text.
6. **Do not overpopulate a post.** Image memes are heavier than headings, text memes, diagrams, footnotes, or pull quotes.
7. **Serious/confessional passages get fewer memes.** As emotional weight rises, image memes are usually the first rest type to disappear.
8. **Verify generated assets when publication depends on them.** Do not assume a guessed template ID, background URL, or renderer output works.
9. **Preserve provenance.** Record whether an asset came from a stock template, custom background, local render, or original image generation when that distinction matters.

## Two selection modes

### Editorial mode

Use when the user wants one or a very small number of publishable memes.

Fit dominates. Explore the live catalog, but do not sacrifice the post merely to satisfy novelty. A surprising template is valuable only if its visual grammar improves the joke.

### Exploration mode

Use when the user asks for several candidates, wants more variance, is testing the skill, or asks to discover memes rather than merely render a known one.

Default batch: **5 candidates**.

- **3 sampled slots** — chosen by an actual random draw from the live template catalog. The draw is binding: attempt to make each sampled template work.
- **2 editorial slots** — freely selected as best-fit candidates from the catalog or another generation route.

For another requested batch size `N`, reserve roughly 60% for sampled slots (`ceil(0.6 * N)`) and the remainder for editorial slots.

A sampled template may be rejected only for a concrete reason such as unsafe baggage, incompatible number/layout of text slots, unreadable result, or genuinely nonsensical semantics. Record the rejection briefly and **draw a replacement**. "Another famous template fits better" is not sufficient reason to evade the draw.

The sampled candidates are not required to win publication. Their purpose is to force the search into regions the model would otherwise ignore.

## Diversity constraints for a candidate batch

- no duplicate template in the same batch;
- normally no more than two candidates from the same joke family;
- avoid making all five candidates variants of reject/prefer or reaction-only grammar;
- when prior-use context is available, downweight or exclude templates used very recently unless they are clearly the best editorial fit;
- treat Drake, Two Buttons, Distracted Boyfriend, This Is Fine, Galaxy Brain and other highly salient defaults as ordinary candidates, not privileged fallbacks;
- diversity means different **visual/comedic structures**, not only different template IDs.

Useful batch metrics:

- distinct template ratio;
- distinct family ratio;
- sampled-survival rate;
- recent-template repetition rate;
- subjective quality of sampled vs editorial slots;
- cross-run template overlap for the same prompt/post.

## Visual-rhythm heuristic

For ordinary non-serious long-form prose, aim for some kind of visual/rest beat roughly every 400–500 words when the page would otherwise become a wall of text. That beat does **not** have to be an image meme.

Image memes should normally be only a minority of those rests.

Default density for image memes:

- under ~800 words: usually 0–1;
- 800–1500: usually 1–2;
- 1500–2500: usually 2–3;
- over 2500: usually cap around 3–4 unless the form itself is intentionally meme-heavy.

Avoid placing two image memes back-to-back in the reading rhythm.

## Workflow

1. **Read the surrounding passage/post.** Determine register and whether an image meme deserves the visual weight.
2. **Identify candidate beats.** Comparison, escalation, reaction, choice, confusion, resignation, thesis, etc.
3. **Choose selection mode.** Editorial or exploration.
4. **Discover, and when exploring, actually draw.** Read [`references/template-discovery.md`](references/template-discovery.md). Do not simulate randomness by choosing "random-looking" templates yourself.
5. **Choose a generation route.** Read [`references/generation-routes.md`](references/generation-routes.md) when a stock Memegen template is not obviously the right production route.
6. **Compose compact text.** Prefer a few words per slot; rewrite instead of cramming.
7. **Build and verify the asset.** For Memegen use [`references/api-and-embedding.md`](references/api-and-embedding.md). For other routes preserve the same verification and accessibility requirements.
8. **Judge subjectively.** Evaluate template semantics, joke quality, legibility, freshness, integration with the post, and whether the image earns its space.
9. **Embed accessibly.** Use the publishing system's preferred Markdown/HTML conventions and useful alt text.
10. **Check local rhythm and redundancy.** A good meme can still be the wrong meme if another visual or joke already occupies the beat.
11. **Record exploration evidence when useful.** Keep the sampled IDs, rejections, finalists, and selected route so repeated runs can be audited for variance.

## Resources

- [`references/template-discovery.md`](references/template-discovery.md): live catalog, true random drawing, salience debiasing, cooldown and family diversity.
- [`references/generation-routes.md`](references/generation-routes.md): predefined templates, custom backgrounds/overlays, self-hosted rendering, original generated visuals, optional alternate services.
- [`references/shortlists.md`](references/shortlists.md): non-canonical memory aid; never the complete candidate universe.
- [`references/api-and-embedding.md`](references/api-and-embedding.md): Memegen URL construction, path escaping, query parameters, testing and embedding.

Load references only when the workflow reaches that branch.

## What to deliver

For a single meme request, deliver the ready-to-paste embed plus a short reason for the choice.

For exploration batches, show which candidates were **sampled** and which were **editorial picks**. If a sampled template was rejected, show the replacement and the brief rejection reason. Do not hide a failed draw.

For visual-rhythm work across a long post, place/propose memes at individual insertion points so each can be accepted or rejected independently.

## Definition of Done

The task is complete when:

- template/visual grammar fits the intended beat;
- exploration work used actual randomness rather than model intuition alone;
- sampled slots were attempted rather than silently replaced by familiar defaults;
- the batch has meaningful family/template diversity;
- text renders legibly;
- production route and asset were verified when feasible/relevant;
- embedding includes useful accessibility text;
- meme density fits the local register and surrounding visuals;
- the result can feed the next benchmark cycle with evidence about both quality and variance.