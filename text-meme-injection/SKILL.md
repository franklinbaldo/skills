---
name: text-meme-injection
description: |
  Inject text memes into blog posts, essays, and other long-form prose to make reading lighter without breaking voice. Use when the user asks to make prose funnier, looser, less academic, or explicitly wants meme/ironic texture. Do not use for legal documents, technical docs, condolences, medical writing, or material marked as serious.
---

# Text meme injection

Add meme-register humor only when it improves the prose. The goal is not maximum meme density; it is a better beat, cleaner register shift, useful compression, or an image that becomes funnier without ceasing to belong to the writer.

## When to use

Use when the user asks to:

- make a draft funnier or looser;
- add irony, meme texture, or mid-text humor;
- reduce stiffness/academic register in a blog or essay;
- review a long-form piece specifically for humorous beats.

Do not use for:

- legal pieces;
- grief, illness, abuse, addiction, suicide, condolences, or medical writing;
- technical documentation where humor would obstruct use;
- text already carrying enough comedy;
- another person's voice without authorization;
- anything explicitly marked serious unless the user clearly asks for the register clash.

## Two modes

### Inline

A small phrase rides inside ordinary prose. The prose still carries the argument; the meme adds texture or compression.

Inline beats are seasoning. If the meme starts doing argumentative work or expands into several sentences, kill it or move to block mode.

### Block

Greentext, dialogic sequences, POV/scenario blocks, escalation lists, alignment-style text, and similar set pieces get their own paragraph/block.

Block memes are rare. They need setup before and a landing afterward so the main prose thread resumes cleanly.

## Always-needed principles

1. **Cut test.** Remove the meme mentally. If the passage is cleaner and loses nothing, do not inject it.
2. **Endogenous humor first.** Before importing a known phrase, try bending an image, contrast, rhythm, analogy, or noun already present in the paragraph. The strongest insertion often feels discovered inside the prose rather than pasted onto it.
3. **Integration test.** If the proposed joke can be detached from the paragraph and posted as a generic reaction with almost no loss, it is probably too external. Prefer edits whose wording depends on the local argument.
4. **Semantic dividend.** Humor should ideally compress, sharpen, expose a contradiction, or make an existing image do more work. A laugh with zero argumentative or rhythmic benefit has a higher bar.
5. **Mode discipline.** Inline is small; block is a set piece. Do not blur them accidentally.
6. **Voice match.** Use a format the writer could plausibly inhabit. Meme register that sounds imported from another subculture is usually worse than no meme.
7. **Do not explain the meme.** The sentence must still function for a reader who misses the reference.
8. **Prefer form over catchphrase.** Reusable syntactic structures age better than canned slogans. Prefer local transformations over catalog catchphrases when both work.
9. **Do not stack.** One meme beat should land before another appears.
10. **No punch-down.** Do not rely on stereotypes, demeaning targets, or imported toxic community baggage.
11. **Seriousness wins.** If humor would trivialize the passage, leave it alone.

## Density

Treat density as a ceiling, not a quota.

- Non-serious long-form: an inline beat roughly every 400–500 words can work when the prose actually has suitable slots.
- Dry essay register: often closer to one every ~800 words.
- Block meme: normally 0–1 per post.
- If the draft is already funny, density should go down rather than up.

Never add a meme merely because the word-count heuristic says one is due.

## Workflow

1. **Read the whole draft first.** Understand its shape and existing humor before proposing insertions.
2. **Identify the register.** Decide how far the text can bend without sounding like a different writer.
3. **Decide whether a block set piece is wanted.** Usually the answer is no.
4. **Find inline slots.** Favor transitions, flat setup sentences, self-aware moments, contradictions, or places where a compact register shift does real work.
5. **Try a local transformation first.** Rework material already in the sentence/paragraph before consulting a meme inventory. Test whether the humor can emerge from the author's own image or argument.
6. **Load a catalog only when it adds something the local prose cannot.** Use [`references/catalog-en.md`](references/catalog-en.md) and/or [`references/catalog-pt-br.md`](references/catalog-pt-br.md) after suitable slots exist and endogenous candidates have been considered.
7. **Calibrate candidates.** Consult [`references/calibration-and-antipatterns.md`](references/calibration-and-antipatterns.md) when freshness, mixed language, subculture fit, or risky register matters.
8. **Choose one recommended candidate per slot by default.** Add a second option only when it represents a real tradeoff in register, intensity, or format rather than a paraphrase.
9. **Run the cut + integration + semantic-dividend tests.** Reject candidates that are detachable reaction tags, add no useful compression, or make the prose feel authored by someone else.
10. **Show proposed changes as a diff-style list.** Let the user accept/reject individual beats.
11. **Stop.** Do not keep searching once the agreed density/rhythm is reached.

## Catalog routing

The concrete meme inventories are conditional references:

- [`references/catalog-en.md`](references/catalog-en.md): English inline and block forms;
- [`references/catalog-pt-br.md`](references/catalog-pt-br.md): PT-BR forms, brasileiro-internet defaults, block structures, and loanword guidance;
- [`references/calibration-and-antipatterns.md`](references/calibration-and-antipatterns.md): stability tiers, register table, mixed-language rules, anti-patterns, and maintenance guidance.

Do not load both catalogs by default if the target language makes one irrelevant. Do not treat a catalog match as evidence that the phrase belongs in the prose.

## What to deliver

Default delivery is a **diff-style list of proposed insertions/replacements**. For each slot, lead with the best edit and one short reason it improves the passage.

Include family/form or freshness/stability metadata only when it materially affects the user's choice. Do not make a simple prose edit feel like an taxonomy report.

Offer alternatives only when they encode a meaningful choice (for example: drier vs louder, inline vs block, evergreen vs deliberately current). Briefly mention rejected candidates only when that teaches a useful boundary.

Provide a full revised version only when the user asks for it or when that is clearly the requested artifact.

## Quality check

Before delivering, score the proposed edit informally on five questions:

- **naturalness** — does it read as part of the paragraph rather than an attachment?
- **voice preservation** — could this writer plausibly have written it?
- **timing/rhythm** — does the beat land where the prose benefits from release or contrast?
- **semantic contribution** — does it sharpen/compress/expose something rather than merely react?
- **freshness/restraint** — is the register appropriate and no louder/more dated than necessary?

If a candidate is weak on two or more dimensions, prefer no meme or find a different slot.

## Definition of Done

The pass is complete when:

- every proposed meme passes the cut, integration, and semantic-dividend tests;
- register remains recognizably the writer's;
- block memes have setup and landing;
- no unsafe/serious-context exclusion was crossed;
- density feels intentional rather than algorithmic;
- concrete catalogs/calibration references were loaded only when needed;
- the delivery does not bury a simple edit under unnecessary meme taxonomy;
- the user can accept/reject changes individually.
