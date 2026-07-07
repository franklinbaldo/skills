---
name: text-meme-injection
description: |
  Inject text memes (it's giving, X-coded, rent free, the duality of, hits
  different, greentext, dialogic blocks, POV scenarios, escalation lists,
  alignment charts) into blog posts, essays, and other long-form prose to
  make reading lighter without breaking voice. Catalog organized by
  stability tier (stable / in-rotation / risky-TikTok-coded), with EN and
  PT-BR sections — PT-BR tilts brasileiro-internet (tá comédia, passei
  pano). Use when the user asks to "make this funnier," "loosen this up,"
  "add some texture," "deixa mais engraçado," "tá acadêmico demais," or
  asks for memes/irony in their writing. Also when reviewing a draft they
  describe as "too academic," "too stiff," or "too earnest." Do NOT use
  for legal documents, technical docs, condolences, medical writing, or
  any text marked as serious.
---

# Text Meme Injection

A skill for adding meme-register humor to long-form prose without making
it cringe.

## When to use

Trigger this skill when the user asks for any of:

- "make this funnier" / "deixa mais engraçado"
- "loosen this up" / "essa parte tá dura"
- "add some texture" / "dar uma respirada na leitura"
- "this is too academic" / "tá acadêmico demais"
- explicit ask for memes, irony, jokes, or "mid-text" humor in a draft
- review of a blog post / Substack / essay where they want the register
  lighter

The `franklin-essay` skill is a separate, optional skill that is not
bundled with this one. Where installed, it defers all text-meme
mechanics here; this skill works standalone and does not assume
`franklin-essay` is present.

## When NOT to use

Hard exclusions, regardless of how it's framed:

- **Legal pieces** (petições, pareceres, recursos) — Franklin's standing
  rule
- **Grief, illness, abuse, addiction, suicide** — even tangentially
- **Medical writing** about real patients
- **Condolences, apologies, breakup notes**
- **Posts that are already funny** — adding meme density to comedy thins
  the comedy. Read the draft first; if it's already landing, leave it.
- **Technical documentation** where someone might be debugging at 3am
- **Anything in the voice of someone other than the writer** unless
  explicitly authorized

If unsure, ask one sentence: "Tá tudo OK injetar humor meme aqui ou esse
post tem registro mais sério?"

## Two modes

Memes split into two operational modes. Different rules apply to each.
Most failure modes come from confusing them.

### Inline mode

The meme rides inside a sentence — parenthetical, em-dash insertion,
end-of-clause tag. The prose carries the meaning; the meme adds texture.

> *The whole quarter was rough — it's giving collapse — and the numbers,
> when you look at them honestly, mostly confirm it.*

Inline memes are **frequent and small**. ~1 per 400–500 words in
non-serious registers (Franklin's blog); ~1 per 800 words in dry
essay registers. They're seasoning.

### Block mode

The meme gets its own paragraph or visual block. Greentext, dialogic
("nobody: / me:"), POV scenarios, escalation lists, "they don't know"
sequences, alignment charts, starter packs. The block itself is the
joke; surrounding prose sets it up and lands afterward.

> The trip planning had been going well. Then this happened:
>
> > be me
> > flight at 6am, alarm set for 4am
> > wake up at 4:47am
> > the airline app says "we are sorry"
> > we are also sorry
>
> The next available flight was eleven hours later, which gave us time to
> develop personalities.

Block memes are **rare and large**. Maybe **one per post**, often zero.
They're set pieces.

## Stability tiers

Every meme in the catalogs (see "Meme catalogs" below) carries a tier.
The skill exists to lighten prose without dating it; tier informs
choice.

| Tier | Age | Risk of aging | Notes |
|------|-----|---------------|-------|
| **Stable** | 10+ years | Very low | Safe in almost any register. The default reach. |
| **In rotation** | 1–3 years | Moderate | Currently active; will probably stabilize but might fade. Use when register carries. |
| **Risky / TikTok-coded** | <1 year, platform-native | High | Will date the prose to a moment. Use only if the post benefits from being a time capsule, or if the user explicitly wants the moment captured. |

The tier is a hint, not a verdict. A "risky" meme in a post that wants
to feel current can be exactly right; a "stable" meme in a post about
a meme cycle can feel mummified. Read the post first, then tier.

When proposing a meme to the user, tag the tier in parens:
*"— it's giving collapse — (stable)"* / *"— very demure — (risky,
will age)"*.

## Core principles

### 1. The cut test (both modes)

For every meme you propose, ask: if I remove this, does the paragraph
lose anything? If the answer is "no, it reads cleaner," cut it. Memes
that survive editing do actual work — compression, register-shift, a
beat-change the prose needed anyway.

### 2. Mode discipline

**Inline memes never become arguments.** The argument lives in the
prose around them. The meme is a wink, not a paragraph. If you find
your inline meme growing into three sentences, either kill it or
promote it to a block.

**Block memes never appear without setup and landing.** A greentext
dropped cold into a post is jarring. There needs to be a sentence
before that says, in effect, "here comes a bit," and a sentence after
that returns to the thread.

### 3. Density

| Mode | Frequency | Notes |
|------|-----------|-------|
| Inline (non-serious register) | ~1 per 400–500 words | Franklin's blog default |
| Inline (dry essay register) | ~1 per 800 words | Conservative |
| Block | 0–1 per post | Two block memes in one post is almost always too many |
| Combined ceiling | 1 inline per 250 words is the upper limit | Above this, becomes content-marketing texture |

### 4. Don't explain the meme

If a reader doesn't recognize "it's giving" or ">be me," the prose
still needs to function as slightly-odd writing. Never write "as the
meme goes" or "as people say online." That's the social equivalent of
a parent using slang.

The phrase has to *work* even for someone reading it as straight
English/Portuguese.

### 5. Steal the form, not the catchphrase

Most live meme-formats are **syntactic** ("it's giving X," "X-coded,"
">be me / >do thing," "the X is X-ing"), not lexical ("we live in a
society"). Syntactic formats let you say a new thing every time.
Catchphrases date quickly. Lean structural.

### 6. Voice match

If the writer is dry → deadpan structural memes ("the duality of,"
"X-coded"). If warm/personal → self-aware ones ("in this essay I will,"
"rent free"). If doing weird-Twitter cosmic-philosophy stuff (Franklin's
blog register) → "and I took that personally," dril-adjacent absurdism,
galaxy-brain tiers, greentexts about cosmic protagonists.

Never use a meme that sounds like a register the writer doesn't already
inhabit. Stan-Twitter ("ate, no crumbs") in a Heideggerian essay is
jarring in the wrong direction.

### 7. Block memes have stronger voice constraints than inline

An inline "it's giving" can ride along under almost any voice. A full
greentext block changes the texture of the post for as long as it
lasts. Make sure the writer would actually want to be heard in that
voice for that long.

## Workflow

When you get a draft to work on:

1. **Read the whole thing first.** Don't propose insertions
   paragraph-by-paragraph. The post has a shape; you're looking for
   the right slots in the shape.
2. **Identify the register** (see calibration below).
3. **Decide first whether a block is wanted.** Is there one moment in
   this post that wants to become a set piece? Often the answer is
   no, and the post just wants 3–4 inline beats. If yes, identify
   which moment and which block format fits.
4. **Find inline injection points.** Look for: (a) sentences doing
   setup work that could land harder with a wink, (b) transitions
   between sections that feel mechanical, (c) moments where the
   writer is already being slightly self-deprecating or ironic — meet
   them there, don't introduce it from nowhere.
5. **Propose 2–3 candidates per slot,** not just one. Different
   registers, different memes, different tiers. Let the user pick.
6. **Apply the cut test to each.** If you can't justify why it's
   better with than without, drop it.
7. **Show the user a diff,** not the whole rewritten post. Make it
   easy to accept/reject each one.
8. **Stop at the agreed density.** Don't keep finding more places.

## Calibration by register

Match the meme family to the writing register.

| Register | Inline best fits | Block fits | Avoid |
|----------|-----------------|------------|-------|
| Dry observational essay | "it's giving," "X-coded," "the duality of," "the [noun] of it all" | Galaxy-brain tiers, escalation lists | Stan Twitter, "main character energy," POV: blocks |
| Personal / Substack confessional | "in this essay I will" subverted, "rent free," "I'm normal about" | "they don't know," dialogic ("me at 3am: / also me:") | Greentext, dril absurdism |
| Cultural criticism | "ate," "main character energy," "the [noun] of it all," "X-coded" | "interviewer: / me:" dialogic | "we live in a society" (corny here) |
| Weird-Twitter / cosmic philosophy (Franklin's blog) | "and I took that personally," "we live in a society," "the duality of," "the math is mathing" | Greentext (>be me), galaxy-brain tiers, escalation lists | Stan Twitter, TikTok-coded, POV: |
| Tech / dev blog | "this is fine," "X-coded," "rent free," "the math is mathing" | Greentext (works perfectly here — its native habitat is tech-adjacent), galaxy-brain tiers | "main character energy," "ate" |
| Comedic review / pop culture | almost anything; lean stan + performative | Dialogic ("nobody: / me:"), POV:, alignment charts | Greentext (too 4chan-coded for a review) |

If you can't identify the register confidently, **ask one question**
before proposing anything: "Esse post é mais ensaio sério com lampejos
secos, ou é mais um diário Substack onde dá pra ser autoirônico?"

## Meme catalogs

The full meme catalogs live in reference files loaded on demand —
before proposing or injecting any meme, read the catalog matching the
target language (paths relative to this skill's directory):

- `references/catalog-en.md` — EN inline formats and EN block formats
- `references/catalog-pt-br.md` — PT-BR inline (brasileiro-internet
  default, plus the literário-deadpan subset) and PT-BR block formats,
  including loanword and translation guidance

Both catalogs are organized by the stability tiers defined above, and
every entry carries a tier tag — the tier system, the cut test, and
the core principles in this file apply to every catalog entry. For
mixed-language posts, read both files.

## Language: PT vs EN — combined posts

Some posts mix languages (Franklin does this). In those:

- Keep memes in the language of the surrounding sentence.
- Don't force PT memes into EN sentences for "localness" — reads as
  affected.
- Loanwords (POV:, hits different, core memory) can ride either
  side.
- Italicize when the meme is in the non-dominant language of the
  paragraph — preserves the register-shift signal.

## Anti-patterns

Things that mark amateur meme-injection. Avoid these unconditionally:

1. **Stacking inline memes.** Two memes in one sentence is one too
   many. *"It's giving collapse, no crumbs, we live in a society"*
   reads like a bot.
2. **Block memes without setup or landing.** A greentext dropped
   between two unrelated paragraphs reads as a glitch. The prose
   around it has to acknowledge it.
3. **Multiple block memes in one post.** Almost always wrong. The
   block is a special move; using it twice halves the impact of
   each.
4. **Explaining the meme.** *"As people say online, this is rent
   free in my head."* No.
5. **Aged formats deployed as if current**: "her: / me, an
   intellectual:" mid-prose, "(POLICE CALLED)," "girls will
   literally just," "in this economy" framings, four-tier
   expanding-brain lists that think they're being clever, "tell me
   you're X without telling me you're X" past 2024. Some are fine
   in deliberately retro/nostalgic contexts; assume they're not
   unless told.
6. **Stan Twitter in serious essays.** *"Hegel ate"* is not the
   move in a philosophy post unless the post is *already* doing
   irreverent register-clash on purpose. Read the draft.
7. **Greentexts with 4chan-native content** (slurs, ironic-bigotry
   humor, "based" as approval). The format is fine; the original
   user-base register is not. Use clean greentexts —
   self-deprecation, mundane catastrophes, cosmic confusions.
8. **Forcing a meme into a slot that doesn't have one.** If no
   candidate passes the cut test, the paragraph doesn't want a
   meme. Move on.
9. **Memes that punch down.** Anything where the joke depends on
   a stereotype, on mocking marginalized groups, on body shape,
   mental state, or class background. Plenty of formats are
   clean; use those.
10. **Self-harm/dissociation humor** ("we love a dissociating
    queen") without confidence in the user's context. Tumblr's
    mental-illness self-deprecation register is fine in
    Tumblr-shaped posts, dangerous in others.
11. **Risky-tier memes deployed as if stable.** "Very demure" or
    "girl dinner" used straight, without time-capsule framing,
    dates the prose to 2024 in a way the writer probably didn't
    want.
12. **Translating untranslatable memes.** *"servida, sem migalhas"*
    is not what "served, no crumbs" means. Either keep in English
    or skip.

## Cut criteria — what's not in the active catalog and why

For transparency about the editorial line of this skill:

- **"Stan-Twitter (ate, served, mother, no crumbs)"** — inline-only,
  no block form, very specific register. Listed in the catalog as
  awareness but flagged as wrong register for most long-form prose
  Franklin writes.
- **"Tumblr 'we love a [X] queen' / 'I'm dissociating'"** — omitted
  from active catalog due to mental-illness register concerns. Use
  "I'm normal about" or "in this essay I will" instead, which
  scratch a similar itch without the dissociation framing.
- **"Wojak edits / Chad vs. virgin"** — visual-format-bound; no
  clean text-only version exists. Belongs to `meme-image` if
  anywhere.
- **"Sigma male / alpha / etc."** — manosphere-coded; carries
  baggage that contaminates the joke.

## What to deliver

When you're done, the user gets:

- **A diff-style list** of proposed insertions (or replacements),
  each tagged with mode (inline/block), meme family used, tier,
  and a one-line reason.
- **The full revised version** as a separate artifact only if
  explicitly asked.
- **What you considered and rejected**, briefly — useful for the
  user to calibrate your future passes.

Format example:

```
PROPOSED INJECTIONS

[INLINE] §3, sentence 2 — adding "— it's giving early-stage panic —"
  family: structural / it's giving
  tier: stable
  reason: §3 is doing a list of warning signs; the parenthetical
          compresses the diagnosis without forcing a topic sentence.

[BLOCK] between §5 and §6 — greentext set piece (~5 lines)
  family: block / >be me
  tier: stable
  reason: §5 ends on the bureaucratic absurdity moment; the post
          wants one set-piece beat there before §6 returns to the
          argument.

[INLINE] §7, final sentence — replacing "it was strange" with
"the duality of it"
  family: structural / the duality of
  tier: stable
  reason: clause already names two contradictory facts; phrase
          compresses.

[INLINE] §9, mid-paragraph — "tá comédia"
  family: PT-BR brasileiro-internet
  tier: stable
  reason: writer's register is already PT-BR colloquial; this
          lands a beat where prose is currently flat.

REJECTED
- §2 had a slot but no candidate passed cut test (cleaner without)
- §6 is already funny — adding meme density would thin it
- §8 considered "very demure" (risky tier) — would date the post
  for no benefit
```

## Maintenance notes

The catalogs in `references/` will age. Quarterly review:

- Move items between tiers as cycles run their course (in-rotation
  → stable, or in-rotation → risky-then-cut).
- Add new in-rotation items as they emerge.
- Cut risky-tier items that died without stabilizing.

When tier-shifting, leave a one-line note in the entry: *(promoted
from in-rotation 2026-05; was stable enough across registers)*.
