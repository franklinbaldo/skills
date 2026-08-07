---
name: meme-image
description: |
  Generate recognizable image memes for blog posts, essays, and Markdown contexts, primarily via memegen.link. Use when the user asks for a classic meme template populated with custom text or when a long-form post needs an image-meme beat. Do not use for original diagrams, SVG explainers, photographs, or high-stakes/serious material where meme register is inappropriate.
---

# meme-image

Use recognizable image-meme templates when their cultural shorthand carries part of the joke. The skill's job is **editorial selection first, URL mechanics second**.

## When to use

Use when the user wants:

- a classic image meme with custom text;
- a comparison/escalation/reaction/choice meme;
- a galaxy-brain, Drake, Distracted Boyfriend, Two Buttons, Change My Mind, This Is Fine, or equivalent recognizable format;
- occasional image-meme rhythm inside a long, non-serious post.

Do not use when:

- the visual should be an original diagram, SVG, chart, or explainer;
- the user wants a photograph rather than a meme format;
- the material is legal, medical, condolence/grief, abuse, suicide, or otherwise serious enough that the meme would trivialize the subject;
- a text meme or ordinary prose beat would do the job better.

## Always-needed editorial contract

1. **Choose by function, not fame.** Identify what the beat must do before choosing a template.
2. **The template carries meaning.** Do not force text into a recognizable format whose native joke structure does not fit.
3. **Keep line text short.** A meme is visual compression, not a paragraph renderer.
4. **Accessibility remains required.** Deliver useful alt text whenever the meme is embedded.
5. **Do not overpopulate a post.** Image memes are heavier than headers, text memes, diagrams, footnotes, or pull quotes.
6. **Serious/confessional passages get fewer memes.** As emotional weight rises, image memes are usually the first visual-rest type to disappear.
7. **Verify generated assets when publication depends on them.** Do not assume a guessed template ID or URL works.

## Visual-rhythm heuristic

For ordinary non-serious long-form prose, aim for some kind of visual/rest beat roughly every 400–500 words when the page would otherwise become a wall of text. That beat does **not** have to be an image meme.

Image memes should normally be only a minority of those rests. Other options include text memes, diagrams, SVGs, maps, footnotes, pull quotes, and section headings.

Default density for image memes:

- under ~800 words: usually 0–1;
- 800–1500: usually 1–2;
- 1500–2500: usually 2–3;
- over 2500: usually cap around 3–4 unless the form itself is intentionally meme-heavy.

Avoid placing two image memes back-to-back in the reading rhythm. If there is no other visual/rest beat between them, give them substantial prose distance.

## Register

Default to meme-friendly treatment only for clearly non-serious writing. A philosophical or technical post can be irreverent without becoming a meme collage.

For serious register, if an image meme is appropriate at all, keep it exceptional and require a clear editorial reason. Do not use image memes merely to satisfy a density heuristic.

## Workflow

1. **Identify the beat.** Comparison, escalation, reaction, choice, confusion, resignation, thesis, etc.
2. **Choose the template deliberately.** If the user did not explicitly name one, consult [`references/template-discovery.md`](references/template-discovery.md) for live-catalog lookup and debiasing rather than relying on memory.
3. **Compose compact text.** Prefer a few words per slot; rewrite instead of cramming.
4. **Build and verify the asset.** Use [`references/api-and-embedding.md`](references/api-and-embedding.md) for memegen.link URL syntax, encoding, parameters, HTTP verification, and embedding details.
5. **Embed accessibly.** Provide descriptive alt text; use the surrounding publishing system's preferred Markdown/HTML conventions.
6. **Check local rhythm.** Make sure the meme is not crowding another image meme or trivializing a passage that should breathe on its own.
7. **Explain the choice briefly.** The user should know why that template fits the joke better than the obvious alternatives.

## Template selection resources

- [`references/template-discovery.md`](references/template-discovery.md): live catalog, keyword lookup, random draw, function-first selection, fallback when no template fits.
- [`references/shortlists.md`](references/shortlists.md): non-canonical memory aid grouped by useful template families.
- [`references/api-and-embedding.md`](references/api-and-embedding.md): URL construction, path escaping, query parameters, testing, Markdown/HTML embedding, third-party-service boundary.

Load these only when the workflow reaches that branch.

## What to deliver

For a single meme request, deliver:

1. ready-to-paste embeddable Markdown or the publishing format requested;
2. the underlying image URL when useful;
3. one short reason for the template choice.

For multiple candidates, show a small set of meaningfully different options rather than many near-duplicates.

For visual-rhythm work across a long post, propose insertion points individually so the user can accept/reject each beat.

## Definition of Done

The task is complete when:

- the template's native semantics fit the intended beat;
- text is short enough to render cleanly;
- the generated asset is valid when verification is feasible/relevant;
- embedding includes useful accessibility text;
- meme density fits the local register and surrounding visuals;
- conditional API/catalog mechanics were loaded only when needed.