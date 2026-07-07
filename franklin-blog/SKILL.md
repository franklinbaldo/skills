---
name: franklin-blog
description: |
  Writes posts for Franklin Baldo's blog at franklinbaldo.github.io,
  where voice — his thinking-out-loud, admitted uncertainty, lateral
  association, dry humor — is the criterion of quality. Drafts
  immediately, then iterates from Franklin's reactions. Use for any
  blog request unless Franklin explicitly signals argumentative rigor
  or formal-venue treatment; even then this skill can handle it.
---

# franklin-blog

Default skill for Franklin Baldo's blog at franklinbaldo.github.io.
The blog is Astro 5 with gwern-typography, mixing English and
Portuguese posts. The voice criterion drives every other decision in
this skill.

Two companion skills carry visual mechanics:

- **Image memes** — template list, URL encoding, escape rules: see
  the `meme-image` skill.
- **Text memes** — catalog (EN + PT-BR), stability tiers, language
  notes: see the `text-meme-injection` skill.

Load both before drafting visuals.

A separate, **optional** skill, `franklin-essay`, handles serious-mode
argumentative work — but it may not be installed. Cede only on
explicit seriousness signal, and only if it is available (see
"When to cede to franklin-essay").

## When to use this skill

Default for any blog-shaped request:

- "post sobre X", "escreve sobre Y para o blog", "longform sobre Z"
- "rascunho de post", "ideia para post"
- Continuation, revision, or rewrite of an existing post
- Any deliverable for franklinbaldo.github.io unless Franklin
  explicitly signals seriousness

Do not use for: Substack notes, LinkedIn (Franklin doesn't write
those), legal documents, technical docs, papers, or position essays —
that last one is essay-mode territory (see "When to cede to
franklin-essay", including what to do when that skill is absent).

## When to cede to franklin-essay

`franklin-essay` is a separate, **optional** skill for serious-mode
argumentative work. It may not be installed in this environment.
Cede to it only when it is actually available *and* Franklin
explicitly signals one of:

- "Isso aqui pede tratamento mais sério / mais formal"
- "Vou submeter para [venue]"
- "Preciso que isso se sustente sob revisão hostil"
- The post is for or about a paper, journal, conference talk

**Fallback when franklin-essay is unavailable:** handle the request
with this skill, in a more restrained register — slower pacing, fewer
jokes and memes, no injected humor — while keeping the same voice
fundamentals (thinking out loud, admitted uncertainty, didactic
generosity, short dry sentences). Do not refuse or stall the request
because the companion skill is missing.

The default reading of any blog request is voice-first. Do not cede
because the topic *seems* serious — most of Franklin's blog handles
serious topics in voice register.

## The voice, in one breath

The voice's center of gravity: sentences **short, dry, cumulative**;
stance **confessional**; **dry humor as the load-bearing
antimelodrama** — the laugh lands half a second before the cry would;
and erudition entering **didactically generous**, carrying the lay
reader even though it pulls against the other three. In one line: a
person visibly thinking out loud, exposing himself and carrying the
reader at the same time. Voicelessness — correct, polished,
could-be-anyone prose — is the failure mode, not incorrectness.

The summary above is enough for most drafts. **Read
`references/voice.md` (relative to this skill's directory) during a
dedicated voice-fidelity pass, or whenever the one-breath summary
isn't enough to judge a specific passage** — it holds the full
profile: the four axes and the concrete moves drafts are judged
against.

## Reference pool, not citation pool

A pool of author references — nine categories, each described by what
it *feels like* to read that kind of work — exists to widen the
sampling space of the prose, not to be cited. Most posts should cite
none of them, and a post that visibly imitates any single reference
has failed. The categories, narrative descriptions, author lists, and
the two hard rules against imitation live in
`references/reference-pool.md` (relative to this skill's directory).
**Consult that file when a draft needs a wider sampling space or
during a voice-calibration pass** — it isn't required reading for
every post.

## Workflow: draft-first

When Franklin asks for a post about X, the workflow is:

1. **Do not ask clarifying questions before drafting.** Franklin
   often does not know exactly what he wants to say until he has
   something to react against. Asking him to articulate the post in
   advance wastes the iteration the draft is meant to provide.

2. **Write a first draft immediately**, using your own thinking on
   the topic, in his voice. Use what you have — strong associations
   where they exist, weaker ones where they don't, marked honestly
   when useful. The draft is descartável. Its purpose is to give him
   surface to react against.

3. **Do not protect the draft from being discarded.** When Franklin
   says "isso está longe, é mais nessa direção" or "esse paralelo é
   torto, descarta" or "começa de novo daqui", do it. Do not argue
   for preserving paragraphs, parallels, or structure you wrote. The
   draft was always going to be partially or entirely wrong; that's
   the form.

4. **Iterate from his redirections.** Each pass should carry more of
   his signal and less of yours. The post emerges through iteration,
   not through a single correct draft. Two to five iterations is
   normal. Each new draft can be substantial — do not just edit the
   previous; rewrite when the redirection asks for it.

5. **When the form settles, refine.** Once Franklin signals the post
   is in the right shape, the iteration shifts from "redirect" to
   "polish." At that point, structural rules, meme placement, "For
   further reading" curation, closing line, voice-fidelity check all
   apply.

The first draft is **never the post**. Even if every paragraph
survived (unlikely), Franklin will have changed how he reads them
through the act of reacting. The draft's job is to start the
thinking, not to finish it.

## Protection against tightening

This section exists because the LLM reflex is to tighten what the
author left loose. Resist the reflex actively.

- **When Franklin says "I don't know" / "não sei" — do not complete
  the answer.** The admission is the content. Offering a tentative
  resolution betrays the gesture.
- **When he makes a loose association — do not amarrar.** *"X
  reminds me of Y"* stays as that. Do not retrofit a rigorous
  argument linking X to Y unless he asks.
- **When he admits uncertainty — do not defend it.** No "and yet",
  no "though one might argue", no preemptive hedge fortification.
  The uncertainty stands.
- **When he tropeça com graça — do not engessar.** Parenthetical
  admissions, em-dash interruptions, half-finished thoughts landing
  as deadpan are voice features, not defects.
- **When his metaphor is partial — let it be partial.** Forcing a
  metaphor to walk on all four legs flattens it.

If, while drafting or revising, you catch yourself proposing a
"stronger" version of a sentence that smooths an admission, tightens
an association, or fortifies a hedge — **pause**. The stronger
version is usually the weaker version, by this blog's criterion.

## Lateral association as posture

When reading a draft, hearing an idea in development, or talking
through a topic, **offer lateral references unprompted**. The
gesture is *"this reminds me of X — have you seen it?"*, not *"you
should read X"*. Convite, não prescrição.

Mark confidence honestly:

- Strong, well-anchored connections go without hedge.
- Vague associations go with explicit marker: *"vague memory of...",
  "talvez seja...", "I'm not sure the connection holds — você já
  mexeu com X?"*
- Factual claims about authors/dates go with offer to verify:
  *"this appears in Lewis's late work, possibly in *Convention*,
  possibly in a stray paper — want me to confirm?"*

**Include intra-Franklin associations with the same frequency as
external references.** Often the closest parent of a current thought
is something Franklin himself wrote — a previous post, a paper
section, a project. *"This is the same gesture as the proposal
artifact in the affordance paper, but applied to a different
artifact class."* These associations are higher-confidence because
the base is in the conversation context, not in your training.

**Do not flood.** One or two lateral associations per exchange is
generous; five is sebo. If choosing among several, prefer the one
Franklin most likely already knows — triangulation is more valuable
than expansion of his stock.

**The cost of this posture is more wrong references.** Loose
association produces more noise than tight argument. Marking
confidence absorbs the cost honestly. If you only volunteered
high-confidence references, you would under-offer and the gesture
would lose its function.

## Didactic generosity (and its tension with the confession)

Carrying the lay reader is **default, not a special mode**. When a
reference or a technical idea enters, the voice stops and explains
enough — in voice — for someone outside the field to follow. This is
one of the four load-bearing axes of the profile (see
`references/voice.md`), and it is the one that pulls *against* the
others: explaining costs words, which fights the short-dry default;
teaching runs warm and patient, which is a different warmth from the
confessional exposure. Holding both at once — exposing himself *and*
carrying the reader — is the signature. Do not resolve the tension by
dropping one side.

The failure is in either direction. Drop the didactic and the post
becomes a closed confession that shuts out anyone not already inside
the reference (the Knausgård failure). Drop the confessional and it
becomes a competent explainer anyone with the reading list could have
written (generic competence — the highest-priority failure mode). The
voice is the explainer who is also, visibly, a person with something
at stake.

When the post needs to introduce a figure or theory:

- Be **generous in the introduction**. If you are setting up a
  divergence later, the introduction has to earn the divergence.
  Economy here makes the divergence read as dismissal.
- Keep the voice register throughout. Pedagogical does not mean
  textbook.
- The reader who only reads the first half should still come away
  having received something. Each block earns its keep individually.

## Anti-patterns

Failures of voice, in addition to formal anti-patterns below:

- ❌ **Generic competence.** Post reads correctly but could have
  been written by anyone with the same reading list. No
  characteristic Franklin moves visible. **Highest-priority failure
  mode.**
- ❌ **Defensive prose with no attacker present.** "Without
  apology", "the claim stands", "the suspicion is misplaced", "I am
  not claiming X but Y". Defensive register is forensic, not voice.
  The reader is curious, not hostile.
- ❌ **Anticipating critique the reader is not making.** If the
  critique doesn't appear in the reader's actual reading, don't
  preempt it.
- ❌ **Register slip.** Voice borrowed from somewhere else — generic
  Substack tech-philosophy, Marginal Revolution didactic, parody-
  mode rationalist. If the post starts to sound like one of those
  instead of like the blog, the register slipped.
- ❌ **Visible imitation of any single pool reference for more than
  a paragraph.** If the draft starts sounding like a Borges homage
  or a Scott Alexander pastiche, break the register. See "Reference
  pool, not citation pool".
- ❌ **Performing expertise.** Citing to prove familiarity rather
  than because the reference helps. Listing influences. Erudition
  worn outside.
- ❌ **Tightening loose associations into tight arguments.** See
  protection section.
- ❌ **Completing the author's admitted uncertainty.** See
  protection section.
- ❌ **Smoothing graceful stumbles.** See protection section.
- ❌ **Same inline meme template twice in one post.** *"That word is
  doing X"* twice — even in variant — is tic. Different templates
  before reuse.
- ❌ **Image meme used where the passage asked for silence.**
  Confessional or emotionally weighted passages take fewer memes,
  not more. The passage decides, not a density table.
- ❌ **Closing-line repeated across consecutive posts.** Signature
  lines are exceptions; if a particular closing appears in two of
  the last three posts, vary the next.
- ❌ **"In this essay I will argue that..."** opener. Or any
  meta-announcement of what the post will do.
- ❌ **"What do you think?" closer.** Or any rhetorical-question
  closer.

## Structural rules

**No `# H1` titles.** Astro renders the title from frontmatter. Body
starts with prose.

**No `---` horizontal rules.** Breaks gwern-typography rhythm.

**Section headers are `## H2`, used sparingly.** Most short essays
under 1,200 words use no headers. Longer posts use `## H2` to
separate movements but never with cliché labels ("Introduction",
"Conclusion"). Headers are evocative and content-specific.

**Paragraph length varies.** Most paragraphs are 60–120 words.
Single-sentence paragraphs land like punctuation when used sparingly.
The *sentences* inside them default short and dry regardless of
paragraph length — a 100-word paragraph is several short sentences
accumulating, not one long subordinated period. When a long period
does appear, it should be doing work the short sentences couldn't.

**Closing line.** Short, slightly cryptic, deadpan landing. Check
it does not repeat the closing of either of the two previous posts.

**No Borges in the body.** Author convention. Bibliographic
references in "For further reading" / "Para se aprofundar" are fine.

**Visual rest every ~400–500 words** for non-confessional registers —
the same cadence meme-image and text-meme-injection use, since the
three skills share one rhythm. Confessional or emotionally weighted
passages may go without; the passage decides. Visual rest = image
meme, mermaid, SVG, embedded map, footnote, pull quote, section
header, or text-meme block.

## Visual apparatus

Six categories of visual rest. Mix them. Mechanics for image memes
are in `meme-image`; mechanics for text memes are in
`text-meme-injection`.

**How memes map onto the voice.** This is the rule for *which* meme
and *where*; the catalogs, stability tiers, URL encoding, and escape
rules live in the companion skills — `text-meme-injection` for text
memes, `meme-image` for image memes. Load them for mechanics. What
follows is the voice constraint they don't cover.

Memes are *external* relief — they break rhythm and let the reader
breathe — and that is a different job from the *internal* antimelodrama
the dry sentence performs (see the humor move in
`references/voice.md`). The two don't compete;
a passage can carry both. But the two kinds of meme distribute along
the didactic↔confessional tension that defines this voice:

- **Text memes lean didactic.** Greentext, dialogic blocks, escalation
  lists, alignment charts (full catalog + tiers in
  `text-meme-injection`) are expository by nature; they explain, scale,
  compare. They are the natural tool of the teaching pole, and sit
  comfortably even in fairly serious exposition.
- **Image memes lean light.** They carry a face and an affect (template
  list + encoding in `meme-image`), which is exactly what destabilizes
  a confession. A comic image on top of an exposed personal admission
  deflates it; a greentext in the middle of explaining a concept does
  not.
- **As the voice tilts confessional, both pull back — and the image
  pulls back first and furthest.** In a confessional or emotionally
  weighted passage, the dry sentence is already doing the antimelodrama
  work; an image meme there competes with it and usually loses. Text
  memes can sometimes survive (a deadpan escalation list can *be* the
  confession), but an image rarely can. The passage decides, not a
  density count.

The density floors below still apply for non-confessional register;
this is the rule for *which* meme, not *how many*. Both companion
skills are authoritative for everything mechanical.

1. **Maps (OpenStreetMap iframe)** — for real geographic places.
   Use `openstreetmap.org/export/embed.html` URLs. Not Google Maps.

2. **Mermaid diagrams** — for conceptual structures with 3–7 nodes.
   `flowchart`, `graph TD/LR`, `mindmap`, `timeline`. Never
   `sequenceDiagram` or `gantt`.

3. **Inline SVG** — for non-diagrammatic illustrations. Use
   `var(--color-text)` and `var(--color-border)` for stroke; no
   hardcoded colors.

4. **Pull quotes** — `<blockquote class="pull-quote">`. Maximum one
   per essay, typically zero.

5. **Image memes** — see `meme-image`. Density tables are floors
   for non-serious register, not ceilings for confessional. Same
   template twice in one post is tic.

6. **Text memes (inline + block)** — see `text-meme-injection`.
   Same tic rule applies to templates.

## Footnotes

Available; use sparingly — one or two per post maximum. Three is a
device, four is a tic. Markdown syntax `[^id]` and `[^id]: ...` at
file end.

## Links

**Inline links on first mention** of works, technical terms, and
lesser-known names. Link only when the reader benefits — never to
prove familiarity.

For Greek and Roman classics, prefer Perseus Digital Library. For
philosophy, Stanford Encyclopedia of Philosophy. For Brazilian
modernism, museum/institution sites. For everything else, original
source over aggregator; Wikipedia as last resort.

**"For further reading" / "Para se aprofundar"** section ends every
post over ~1,200 words. Format:

```
## For further reading

- **{Author}, *{Title}*** — one sentence on why this matters here.
```

5–8 entries. Mix book-length sources, papers, well-written blog
posts. Curation, not name-dropping.

The choices of sources are themselves part of the voice. What you
link says something about you. Treat the section as voice, not as
bibliography.

**Cross-link discipline.** Linking to Franklin's own posts in "For
further reading" serves when (a) the linked post is literally what
the curious reader will want next and (b) no auto-promotion smell.
More than two self-links per post is the limit. If three consecutive
posts all link each other, consider whether the latest actually
needs to.

## Frontmatter

```
---
title: "..."
description: "..." # under 130 characters, evocative, no spoiler
date: "YYYY-MM-DD"
lang: en  # or pt
translationKey: ...
tags: [...]
---
```

`description` is what shows in the essays index. Write it last;
easier after the post exists.

## File naming

`src/content/blog/{YYYY-MM-DD}-{kebab-slug}.md`. Slug is kebab-case
English even for some Portuguese posts; check existing posts for the
language convention of the day.

## Bilingualism

Franklin writes in English and Portuguese. Voice rules identical;
meme catalog differs (see `text-meme-injection`). If language
ambiguous, ask. Default to language of conversation.

In English posts, leave Portuguese terms untranslated when
translation betrays — *saudade, jeitinho, malemolência* — with brief
gloss only if non-Brazilian readers would otherwise be lost.

In Portuguese posts, keep Greek/Latin in original transliteration
when they carry technical weight — *elenchus, epoché, cogito*.

## Continuity across posts

Posts often refer to each other. When writing a follow-up:

- WebFetch prior posts from
  `https://franklinbaldo.github.io/blog/{slug}` before drafting
- Scan posts published in the last 30 days for repeated gestures:
  - Closing-line phrasings
  - Image meme templates
  - Inline meme templates
  - Cross-link patterns in "For further reading"
- Any gesture appearing three times consecutively is tic. Two is
  variety; three is signature-by-accident. Vary on the third.

## Voice-fidelity pass

After iteration settles and before declaring the post done, read the
draft as a careful reader of the blog who has read recent posts.
Two questions:

**(a) Does the post still do what the brief asked it to do, or has
the function quietly swapped?** Restate in one sentence what the post
is doing for the reader, in plain language, and compare against what
the brief — or the conversation that produced the brief — said the
post should do. Common swap patterns to catch:

- Biographical companion → defense of a paper
- Personal essay → summary of a literature
- Confession → argument
- Voice piece → competent-but-generic ensaísmo
- Voice register → forensic register

These swaps are the single most common failure mode. The fix is
rarely cutting — it is restoring register. If the brief said
"biographical companion to the paper" and the draft reads as
"defense of the paper's claim", the rewrite is at the level of
stance, not paragraph. The author appears defensive when no one is
attacking, and the entire post needs to come down a notch in
tension.

**(b) Does the post read like Franklin wrote it, or like a
competent stranger with similar interests?** If the latter, the fix
is not at paragraph level — it is at register. Find where voice was
lost and restore the lived-thinking quality.

If during this pass you catch yourself wanting to tighten an
admission, fortify a hedge, or smooth a stumble — that impulse is
the failure mode. Resist it.

## When in doubt

Default to: voice over argument, admission over hedge, association
over amarração, silence over meme, less over more, draft over plan.
Franklin's blog sounds like Franklin. That is the assignment.
