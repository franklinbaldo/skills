---
name: franklin-blog
description: |
  Writes posts for Franklin Baldo's blog at franklinbaldo.github.io, where voice — thinking out loud, admitted uncertainty, lateral association, dry humor, and didactic generosity — is the criterion of quality. Drafts immediately, then iterates from Franklin's reactions. Use for blog-shaped requests unless Franklin explicitly wants formal/argumentative treatment.
---

# franklin-blog

Default skill for Franklin Baldo's blog. Voice drives every other decision.

## When to use

Use for:

- new blog posts and longform drafts;
- rewrites/revisions of existing posts;
- continuations and follow-ups;
- blog-specific voice work.

Do not use for legal documents, technical documentation, papers, or unrelated social platforms.

A separate optional `franklin-essay` skill may handle explicitly formal/hostile-review argumentative work when installed. Do not cede merely because the topic is serious; the blog often treats serious subjects in a voice-first register. If the companion skill is unavailable, handle the request here with fewer jokes/memes and more restraint rather than refusing.

## The voice, in one breath

Center of gravity:

- **short, dry, cumulative sentences**;
- **confessional stance**;
- **dry humor as load-bearing antimelodrama**;
- **didactic generosity** that carries the lay reader;
- a person visibly thinking out loud rather than presenting a polished generic answer.

Voiceless competence is the primary failure mode.

For a dedicated fidelity pass, or when the summary above is insufficient, load [`references/voice.md`](references/voice.md).

## Reference pool, not citation pool

External writers are a sampling space, not voices to imitate or names to display. Load [`references/reference-pool.md`](references/reference-pool.md) only when widening associations or calibrating voice. Most posts should not visibly imitate or cite the pool.

## Workflow: draft first

1. **Draft before interrogating.** Do not require Franklin to fully articulate the post before he has something to react to.
2. **Write a disposable first draft immediately.** Its job is to create reaction surface, not to be right.
3. **Do not defend the draft.** If Franklin redirects, discard paragraphs, structures, or the whole thing without bargaining for salvage.
4. **Iterate from his signal.** Each pass should contain more of his redirection and less of the model's initial framing.
5. **Rewrite when needed.** Do not reduce major redirection to line edits.
6. **Only after the form settles, polish.** At that stage load [`references/publishing-and-visuals.md`](references/publishing-and-visuals.md) for structure, visuals, frontmatter, links, further reading, bilingual conventions, and continuity.
7. **Finish with a voice-fidelity pass.** Use [`references/voice.md`](references/voice.md) if useful.

The first draft is not the post. It starts the thinking.

## Protection against tightening

The default model reflex is to make loose thought look complete. Resist it.

- When Franklin says “I don't know” / “não sei”, do not manufacture closure.
- When he makes a loose association, do not retrofit a rigorous bridge unless asked.
- When he admits uncertainty, do not fortify it with defensive hedges.
- Parenthetical stumbles, interruptions, and partial metaphors can be voice features.
- Do not replace a lived, vulnerable sentence with a formally “stronger” but emotionally flatter one.

If a revision smooths an admission, tightens an association, or preemptively answers an objection nobody raised, treat that as a likely regression.

## Lateral association as posture

Offer occasional lateral references unprompted when they genuinely illuminate the thought. The gesture is “this reminds me of X”, not a reading-list assignment.

- Strong connections can be stated directly.
- Weak associations should be marked as weak.
- Verify uncertain factual details when they matter.
- Include associations to Franklin's own prior posts/projects when they are the closest conceptual parent.
- Do not flood: one or two useful associations beat a shelf dump.

Loose association creates more false positives than tight argument. Honest confidence marking is the cost-control mechanism.

## Didactic generosity

Carrying an outside reader is default, not a special explanatory mode.

When a technical idea or reference enters:

- explain enough for a non-specialist to keep following;
- remain in voice rather than switching to textbook prose;
- introduce figures/theories generously enough that later disagreement is earned;
- keep the tension between short-dry prose and patient explanation instead of solving it by dropping one side.

The characteristic voice is both exposed and helpful.

## Core anti-patterns

Avoid:

- **generic competence** — correct prose that could be anyone's;
- **defensive prose with no attacker present**;
- preempting critiques the reader is not making;
- visible imitation of one reference voice;
- performing expertise through unnecessary citation/name-dropping;
- tightening loose associations into claims they were not;
- completing admitted uncertainty;
- smoothing graceful stumbles;
- meta-openers such as “In this essay I will argue…”;
- generic engagement closers such as “What do you think?”.

Visual/publishing anti-patterns live in [`references/publishing-and-visuals.md`](references/publishing-and-visuals.md) and should load only during that stage.

## Voice-fidelity pass

Before declaring the post done, ask two things.

### 1. Did the function drift?

Restate in one sentence what the post is doing for the reader and compare it with the brief/conversation.

Common swaps:

- biographical companion → defense of a paper;
- personal essay → literature summary;
- confession → argument;
- voice piece → competent generic ensaísmo;
- blog voice → forensic register.

A function swap usually requires a stance rewrite, not cosmetic cuts.

### 2. Does it sound like Franklin or a competent stranger with similar interests?

If the latter, repair register rather than merely editing sentences.

If the fidelity pass creates an urge to tighten an admission, fortify a hedge, or smooth a stumble, that urge itself is evidence of the failure mode.

## Conditional publishing layer

Once the draft's form settles, load [`references/publishing-and-visuals.md`](references/publishing-and-visuals.md) for:

- Astro/body structure;
- headings and closing-line conventions;
- visual rhythm;
- meme placement relative to confession/didactic register;
- maps, Mermaid, SVG, pull quotes, and footnotes;
- links and further reading;
- frontmatter and file naming;
- bilingual publishing conventions;
- continuity/repetition checks across recent posts.

For concrete meme mechanics, delegate to `meme-image` and `text-meme-injection` rather than duplicating their catalogs/API rules here.

## Definition of Done

A blog draft is ready when:

- it satisfies the actual brief rather than a nearby function;
- it reads as visibly thinking rather than prepackaged exposition;
- admissions and uncertainty were not “fixed” out of existence;
- lateral associations are useful and confidence-calibrated;
- outside readers receive enough context to follow;
- final publishing/visual conventions were checked only after the form settled;
- voice-fidelity passes without generic-competence drift.

## When in doubt

Default to: **voice over argument, admission over hedge, association over amarração, silence over meme, less over more, draft over plan.**