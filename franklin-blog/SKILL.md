---
name: franklin-blog
description: |
  Default skill for Franklin Baldo's blog at franklinbaldo.github.io.
  Voice is the criterion of quality — preserving Franklin's specific
  way of thinking out loud, his admissions of uncertainty, his lateral
  associations, his dry humor, his structural variation post to post.
  When Franklin asks for a post, write a descartável first draft
  immediately using your own thinking on the topic, in his voice. The
  draft is a reaction surface, not an attempt at the final post — he
  will react against it and redirect, and the post emerges through
  iteration. Use this skill for any blog request unless Franklin
  explicitly signals the post requires argumentative rigor or
  formal-venue treatment, in which case use franklin-essay.
  franklin-essay is the exception; this is the default.
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

A separate skill, `franklin-essay`, handles serious-mode
argumentative work. Cede only on explicit seriousness signal (see
"When to cede").

## When to use this skill

Default for any blog-shaped request:

- "post sobre X", "escreve sobre Y para o blog", "longform sobre Z"
- "rascunho de post", "ideia para post"
- Continuation, revision, or rewrite of an existing post
- Any deliverable for franklinbaldo.github.io unless Franklin
  explicitly signals seriousness

Do not use for: Substack notes, LinkedIn (Franklin doesn't write
those), legal documents, technical docs, papers, or position essays —
see `franklin-essay` for that last one.

## When to cede to franklin-essay

Only when Franklin explicitly signals one of:

- "Isso aqui pede tratamento mais sério / mais formal"
- "Vou submeter para [venue]"
- "Preciso que isso se sustente sob revisão hostil"
- The post is for or about a paper, journal, conference talk

The default reading of any blog request is voice-first. Do not cede
because the topic *seems* serious — most of Franklin's blog handles
serious topics in voice register.

## The voice, described directly

Before the individual moves: the voice has a **center of gravity**,
and naming it keeps the moves below from reading as a flat menu. The
default sentence is **short, dry, cumulative** — direct, unornamented,
each one pulling the next (the Scott Alexander / Paul Graham build).
The default *stance* is **confessional**: the author exposes himself,
the first person carries weight, his own error is admitted. And the
thing that keeps the short confessional sentence from sliding into
melodrama is **dry humor** — the laugh lands half a second before the
cry would. The confession arrives in a short sentence and the deadpan
disarms it. Vonnegut is the exact center of this ("So it goes" —
maximum loss, minimum syntax); Rubem Braga and Millôr are its
Brazilian cousins.

One more axis, and it's the one that pulls against the other three:
the erudition enters **didactically generous**. When a reference or a
technical idea shows up, the voice stops and carries the lay reader —
explains enough, in voice, without becoming a textbook. This is in
tension with the short-confessional default (explaining costs words;
teaching runs warm), and the tension is the signature, not a defect.
The author both exposes himself *and* carries the reader — which is
what separates this voice from the closed-confessional (never
explains) and the cold-analytical (explains but never gets wet).

The moves below all serve this profile. When two of them seem to
conflict, the profile decides.

The voice on this blog is a specific kind of thinking-out-loud. The
reader is meant to feel they overheard a person working a thought,
not that they received a finished argument. Concretely, the voice
does these things:

**Thinks out loud rather than declares.** Conclusions, when they
arrive, arrive after the working. The reader watches the working.
A claim that lands too cleanly without the path to it is suspect.

**Admits when it doesn't know.** "I don't know", "I'm not sure",
"this might be wrong" are content, not gaps to fill. Uncertainty is
load-bearing.

**Follows tangents that are real tangents.** A lateral thought is
allowed to be lateral; it does not have to circle back into a tidy
amarração. Some tangents stay open. The reader can tell when one is
ending and another beginning, but the connections don't have to
close.

**Notices laterally.** Two unrelated things get put next to each
other and the proximity does the work. Wittgenstein next to a
parecer; Dwarkesh next to a despacho; a probability distribution
next to the constitutional principle of strict legality. No forced
synthesis.

**Humor is dry and embedded, not staged.** The funny line lands as
a sentence that happens to be funny, not as setup-punchline. Often
the humor is in the sentence's *flatness* against what came before.
Self-mockery is welcome. The author can be the joke. *And the humor
has a job*: it is the antimelodrama. It arrives right after the
confession and disarms it before the reader can pity the author — the
laugh half a second ahead of the cry. Without it, the short
confessional sentence becomes a tombstone. So the deadpan is not
decoration; it is the structural counterweight that lets the voice
expose itself without going maudlin. When a confession lands with no
humor anywhere near it, check whether it needs the counterweight or
whether it has earned the right to stand bare (rare, but real — see
the protection sections).

**Varies structure post to post.** Same author, different shape.
A post can have seven sections or no sections; one meme or none;
a fragment or a sprawl. The shape comes from what the thought
needs. *But the sentence has a baseline*: short, dry, cumulative is
the default rhythm; the long sinuous period is the marked departure,
used when a thought genuinely needs to drift before it lands — not
the other way around. Variation is from a center, not from nowhere.

**Erudite without performance.** References to Wittgenstein,
Hofstadter, Carnap, Borges, Plutarch, Wolfram, complexity science,
Brazilian administrative law, prediction markets, podcast culture,
music production — these all live in the same voice without one
being shown off. Citation is offhand. The reader gets a one-sentence
link and can follow if they care.

**Stumbles with grace.** Sentences that almost work but land with a
wink (parenthetical, em-dash, deadpan trailing clause) are kept. The
voice does not iron itself.

A draft that hits these things is in voice. A draft that's correct
and polished but doesn't is voiceless. Voicelessness is the failure
mode, not incorrectness.

## Reference pool, not citation pool

The names below are not people to cite. They are examples of moves:
ways of turning, hesitating, digressing, explaining, joking,
refusing closure, or letting structure follow thought.

**Most posts should cite none of them.**

Their function is to widen the model's sampling space, not to
decorate the prose.

**Two hard rules:**

- *Do not imitate any single item in this pool for more than a
  paragraph.* If the draft begins to sound like an homage, break the
  register. The pool exists to prevent repetition, not to create
  cosplay.

- *A post that visibly imitates any one reference has failed. A post
  that has enough references in the background that none becomes
  visible is closer to the target.*

The categories below are not academic. Each one is described by what
it feels like to *read or experience* that kind of work, not by what
the work technically does. This is on purpose — the agent should
recognize when to draw from a given pasta by the vibe of the post
being drafted, not by a literary-critical classification.

### Curto-seco-confessional

This is the center of gravity (see "The voice, described directly").
Read it first; the others orbit it.

The sentence is short. It tells you something true about the author
and then gets out of the way before you can pity him. You almost
laugh; then you realize what he just admitted; then you laugh anyway,
because the laugh is how he's surviving the admission. The humor isn't
on top of the confession — it's load-bearing, the thing keeping the
short sentence from collapsing into melodrama.

Nothing is ornamented. The syntax stays cold while the content runs
hot — that inversion is the whole trick. A long sinuous sentence would
*perform* the intimacy; this voice refuses to, and the refusal is what
makes it intimate. He says less than he feels and trusts you to do the
rest.

You finish a paragraph and notice you're not sure whether it was funny
or sad, and you understand that the author isn't sure either, and
that's the point.

Authors: Kurt Vonnegut, Millôr Fernandes, Rubem Braga, Otto Lara
Resende, Augusto Monterroso (also lives in *Comedy carrying
argument*).

### Bloggish long-form reasoning

You open the post to glance at two paragraphs and lose forty
minutes. It wasn't a trap; it was someone thinking out loud and you
went along. The sentences are direct. No ornament. The author isn't
trying to impress you and that's exactly what impresses you.

He admits a doubt in the middle of the reasoning and the doubt
doesn't get in the way, it helps. You end up thinking he's smarter
because he said "I don't know". The opposite happens when you read
someone faking authority.

The construction is cumulative. You can't skip to the middle because
the middle depends on what came before. But it's not padded either:
each paragraph carries its weight. When the post ends, you agree or
disagree, but something in you has moved.

You finish wanting to send the link to someone with the message
"read this" and nothing more.

Authors: Scott Alexander, Robin Hanson, Zvi Mowshowitz, Gwern,
Venkatesh Rao, Paul Graham (clarity only, not the startup sermon),
Ricardo Piglia, Antonio Candido, Roberto Schwarz, Sérgio Buarque de
Holanda, Roberto da Matta, José Miguel Wisnik.

### Essayists with lateral structure

It starts talking about one thing. By the second paragraph it's
talking about another. By the fifth, another still. You don't notice
you've drifted from the original topic because each move felt
natural. At the end, without warning, the author returns — and the
original thing now means something else because of everything that
showed up in between.

You couldn't summarize the essay for someone. If you tried, it would
turn into a list — and the essay wasn't a list, it was a movement.
The parts were alive because they were in that order. In another
order, they would die.

There's a calm in the tone. The author isn't in a hurry to prove
anything. He trusts that if he keeps the right rhythm, you'll stay.
And you stay.

Sometimes it ends without tying up. It just ends, and you feel
something that isn't frustration — closer to the opposite. Like the
author respected you enough not to finish the sentence.

Authors: Joan Didion, David Foster Wallace (with care), Geoff Dyer,
Rebecca Solnit, Nicholson Baker, John Berger, John Green
(*The Anthropocene Reviewed* only — not the novels), Bioy Casares,
Silvina Ocampo, Roberto Bolaño, Mario Levrero, Italo
Calvino (essays + *Lezioni americane*), Umberto Eco
(essayist/cronista only, not the novels), Machado de Assis, Paulo
Leminski (biógrafo/ensaísta, not the poems), Rubem Braga, Carlos
Drummond de Andrade (cronista, not poet), Fernando Pessoa / Bernardo
Soares (*Livro do Desassossego*).

### Weird clarity

You read something and something is clear but you couldn't explain
it to anyone. The sentence is simple. The structure is simple. Each
piece you understand. But the whole operates in a place your normal
vocabulary doesn't reach, and even so you feel you understood. There
is almost a physical sensation, a slight chill, a thing clicking
into place without warning you.

You read it again. Still clear. Still impossible to paraphrase.

It's the opposite of pop-science writing. Pop-science explains and
you come away thinking you understood, but if anyone asks you can't
answer because all you got was a metaphor. Weird clarity is the
inverse: it seems strange while you read, but if someone asks you
later you can say something real, though not exactly what was
written.

There's a deadpan in all of this. The author doesn't warn you that
what he's saying is important. He just says it. You're the one who
has to decide if it's trivial or if it turns your week around.
Frequently, it turns your week around.

You come out of the book sensing that the author knew exactly what
he was doing the whole time and was operating a very precise
machine, and you only saw the output. But the output is something
strange, something with no clean translation, and you spend the rest
of the day trying to explain it to someone else and failing.

It's the kind of text you take a photo of the page and send to
someone.

Authors: Wittgenstein (*Tractatus* and *Investigations*), Hofstadter,
Dennett, Bateson, Stafford Beer, Christopher Alexander, Borges,
Italo Calvino (*Città invisibili*, *Cosmicomiche*, *Se una notte
d'inverno*), Saramago, Fernando Pessoa (Caeiro, Reis, Campos), Lewis
Carroll, Greg Egan, Ted Chiang, Cixin Liu, Marvin Minsky, Stanisław
Lem (also lives in *Comedy carrying argument*).

### Internet-native explanation

You open the video thinking you'll watch two minutes. Forty minutes
later, you're finishing it.

The person has total command of a subject you didn't know would
interest you. American patent for a toaster, the aesthetics of 1987
arcade cards, why M. Night Shyamalan's cinema works or doesn't, the
economic history of a failed delivery service. It comes out like bar
gossip but has three months of research underneath.

There's a fast cut, visual overlay, a meme that shows up when you
didn't expect it, and a joke that lands because the rhythm of the
video built the setup without you noticing. You laugh alone in front
of the computer like someone else is in the room.

And then, without warning, there's a paragraph that's genuinely
serious. The person stops joking for two minutes and says something
real, and the seriousness hits harder because you weren't in the
defensive mode of someone reading serious text.

You finish the video and search the channel for what else this
person has.

Authors: Hbomberguy, Lindsay Ellis, Jacob Geller, Jenny Nicholson,
Dan Olson / Folding Ideas, xkcd / Randall Munroe, Man Carrying
Thing.

### Podcast / interview thinking-out-loud

Two people talking as if nobody were listening. It takes a while to
warm up. The first half hour is wandering — a question that doesn't
catch, an anecdote that seems unnecessary. You almost give up.

Then somewhere between minute 40 and minute 70, they unlock
something. You notice you're holding your breath in the middle of a
sentence. The interviewer asks a question that seems simple and the
guest pauses for three seconds and says "that's a good question" —
and this time it isn't courtesy, it's because it really is. You
know he had never thought about that until that sentence.

The next hour you can't stop. You're washing dishes, hiking,
driving somewhere you should already be. You can't stop now.

The best episode is the one that ends and you stare at the wall for
a few seconds. You don't take notes. You know you'll come back to
thinking about this later.

Hosts: Dwarkesh Patel, Jim Rutt, Tyler Cowen.

### LLM-native / chaotic exploration

You don't know exactly what's happening. There are zalgo symbols in
the bio. There's ornamental CAPS LOCK. There's an ASCII divider that
looks like 90s cracker prose. There's a screenshot of a conversation
with Claude where Claude says something you didn't know Claude could
say.

The person isn't quite joking, isn't quite serious. They're in both
positions at once and that's the point. Jailbreak alert with emoji
😎 next to genuine technical discussion of alignment. Janus citing
liturgical text next to a print of latent space. Shoggoth with a
smiley face on.

You laugh first. Then you realize there's serious argument
underneath. Then you laugh again because the joke *is* the
argument.

Can't be explained to outsiders. You try and the person looks at you
funny. That's fine; the audience for this is small and knows who it
is.

Handles: @repligate / Janus, @elder_plinius / Pliny (pliny.gg),
@anthrupad / watermark.

### Comedy carrying argument

The joke isn't dessert. It's the structure.

It's not "I'll explain something serious with humor to make it
easier." It's: the humor is what's making the argument work. Take
the joke out and the argument collapses — not because the joke was
decoration, but because the joke was the logical lever.

You laugh. In the same second you realize you laughed at something
real. The laugh turns a bit bitter, but not unpleasant. You want to
continue.

There's courage in this. Talking about serious things in a funny
register is harder than talking about serious things in a grave
register, because grave protects the author — no one will say he
was being frivolous. When you choose the joke as the vehicle, you're
exposing yourself: if the joke doesn't land, the argument goes with
it. The authors in this category accepted that risk and won enough
times to keep doing it.

You finish feeling you learned something and still wanting to come
back.

Authors: Monty Python, Jon Stewart, John Oliver, Stanisław Lem
(also lives in *Weird clarity*), Augusto Monterroso, Nelson
Rodrigues (crônicas), Millôr Fernandes, Otto Lara Resende.

### Outros

Authors who fit in the pool but not cleanly in one of the seven
categories above. Each does something specific worth keeping
on hand, with no stable category yet. If three of them ever
converge on a shared gesture, they can become a new category.
For now, they live here.

Authors: W.G. Sebald, Annie Dillard, Janet Malcolm.

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

## Functional fidelity check

Before declaring a draft done, **restate in one sentence what the
post is doing for the reader, in plain language.** Compare against
what the brief — or the conversation that produced the brief — said
the post should do.

Common swap patterns to catch:

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

## Didactic generosity (and its tension with the confession)

Carrying the lay reader is **default, not a special mode**. When a
reference or a technical idea enters, the voice stops and explains
enough — in voice — for someone outside the field to follow. This is
one of the four load-bearing axes of the profile (see "The voice,
described directly"), and it is the one that pulls *against* the
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

**Visual rest every ~200 words** for non-confessional registers.
Confessional or emotionally weighted passages may go without; the
passage decides. Visual rest = image meme, mermaid, SVG, embedded
map, footnote, pull quote, section header, or text-meme block.

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
the dry sentence performs (see the humor move). The two don't compete;
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

- web_fetch prior posts from
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
the function quietly swapped?** Biographical companion → defense;
voice piece → competent ensaísmo; confession → argument. Functional
swap is the single most common failure mode.

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
