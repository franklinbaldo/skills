---
name: text-meme-injection
description: |
  Inject text memes into blog posts, essays, and other long-form prose to make reading lighter without breaking voice. Use when the user asks to make prose funnier, looser, less academic, or explicitly wants meme/ironic texture. Do not use for legal documents, technical docs, condolences, medical writing, or material marked as serious.
---

# Text meme injection

Add meme-register humor only when it improves the prose. The goal is not maximum meme density; it is a better beat, cleaner register shift, or useful compression.

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
2. **Mode discipline.** Inline is small; block is a set piece. Do not blur them accidentally.
3. **Voice match.** Use a format the writer could plausibly inhabit. Meme register that sounds imported from another subculture is usually worse than no meme.
4. **Do not explain the meme.** The sentence must still function for a reader who misses the reference.
5. **Prefer form over catchphrase.** Reusable syntactic structures age better than canned slogans.
6. **Do not stack.** One meme beat should land before another appears.
7. **No punch-down.** Do not rely on stereotypes, demeaning targets, or imported toxic community baggage.
8. **Seriousness wins.** If humor would trivialize the passage, leave it alone.

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
4. **Find inline slots.** Favor transitions, flat setup sentences, self-aware moments, or places where a compact register shift does real work.
5. **Load the target-language catalog.** Use [`references/catalog-en.md`](references/catalog-en.md) and/or [`references/catalog-pt-br.md`](references/catalog-pt-br.md) only after suitable slots exist.
6. **Calibrate candidates.** Consult [`references/calibration-and-antipatterns.md`](references/calibration-and-antipatterns.md) when freshness, mixed language, subculture fit, or risky register matters.
7. **Offer a small number of candidates per slot.** Make them meaningfully different, not paraphrases of the same joke.
8. **Run the cut test.** Reject candidates that do not improve the passage.
9. **Show proposed changes as a diff-style list.** Let the user accept/reject individual beats.
10. **Stop.** Do not keep searching once the agreed density/rhythm is reached.

## Catalog routing

The concrete meme inventories are conditional references:

- [`references/catalog-en.md`](references/catalog-en.md): English inline and block forms;
- [`references/catalog-pt-br.md`](references/catalog-pt-br.md): PT-BR forms, brasileiro-internet defaults, block structures, and loanword guidance;
- [`references/calibration-and-antipatterns.md`](references/calibration-and-antipatterns.md): stability tiers, register table, mixed-language rules, anti-patterns, and maintenance guidance.

Do not load both catalogs by default if the target language makes one irrelevant.

## What to deliver

Default delivery is a **diff-style list of proposed insertions/replacements**, each with:

- location;
- inline vs block;
- candidate text/structure;
- family or form;
- freshness/stability note when relevant;
- one short reason it improves the passage.

Briefly mention strong candidates considered and rejected when that helps calibrate future passes.

Provide a full revised version only when the user asks for it or when that is clearly the requested artifact.

## Definition of Done

The pass is complete when:

- every proposed meme passes the cut test;
- register remains recognizably the writer's;
- block memes have setup and landing;
- no unsafe/serious-context exclusion was crossed;
- density feels intentional rather than algorithmic;
- concrete catalogs/calibration references were loaded only when needed;
- the user can accept/reject changes individually.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
