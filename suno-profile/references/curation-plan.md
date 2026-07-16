# Curation plan: template and process

A curation plan is the answer to "what should this Suno profile, as a
whole, say and show?" — as opposed to the per-field wording advice in
`seo-and-taste.md`. It
exists because fixing the bio, then a tag list, then a caption, one
request at a time, tends to produce a profile that's locally fine and
globally incoherent — a bio that claims one identity while the pinned
songs suggest another, or a playlist that duplicates a thread the bio
already covers instead of adding a new one.

## What the plan is, concretely

One markdown document, kept up to date, not regenerated from scratch each
session. Propose `<blog-repo>/docs/suno-curation-plan.md` the first time
this mode runs; if Franklin already keeps it somewhere else, follow that
instead and update this note.

## Template

```markdown
# Suno profile curation plan

Last reviewed: <date>

## Identity statement

One or two sentences: what is this catalog, in the terms a listener or an
LLM summarizing the profile would use. Not a list of genres — a claim
about what makes the catalog itself, distinct from "an artist who makes
[genre]."

## Recurring threads

The 2-5 things the catalog keeps coming back to, each with:
- name
- what it actually is (one line)
- example songs
- current strength (established / emerging / one-off that could become one)

## Bio

Current text, and whether it still matches the identity statement and
thread list above. If not: what specifically drifted.

## Genre tags (profile-level, max 5)

Current list, and the rationale for each — which ones are load-bearing
(searchable, broad) vs. differentiating (specific to this catalog). Flag
any tag nobody could explain the purpose of.

## Pinned songs (max 10)

For each pinned slot: song, why it's pinned (which thread it represents,
or why it stands alone), and its pin caption. Look at the slate as a set —
flag redundancy (two slots making the same pitch) and gaps (a strong
thread with no pinned representative).

## Song descriptions

Catalog-wide completeness, not just pinned songs — a song's own `caption`
(distinct from its pin caption) is real searchable text sitting empty on
most songs by default. Run the audit method below, report the percentage
empty and a play-count-sorted priority list, and draft captions for a
small batch (5-10) at a time with Franklin rather than writing dozens
unilaterally in one pass — this is real editorial work, same discipline
as bio/pinned-caption drafting.

## Playlists

Existing playlists and their theme/status (active, needs a refresh, should
be retired). Proposed playlists not yet created, each with a one-line
thesis — reject "everything tagged X" as a thesis; a playlist needs a
reason a specific set of tracks belongs together.

## Open questions / next review triggers

What's unresolved, and what would prompt revisiting this plan before the
default cadence (a new thread emerging, a stale pinned song, Franklin
flagging something feels off).
```

## Drafting the plan

- Ground every claim in what's actually in the catalog — read the audit
  output, the profile's current bio/tags/pinned songs, and a representative
  sample of lyrics/captions before writing the identity statement. Don't
  invent a thread from one song; don't ignore a thread that shows up three
  or more times just because it wasn't discussed before.
- Bring drafts to Franklin as drafts, not as finished decisions — the
  identity statement and thread list are editorial judgment calls he needs
  to confirm or correct, the same way `seo-and-taste.md`'s wording
  suggestions get workshopped before anything is applied.
- Keep the plan shorter than the temptation suggests. A profile with 10
  pinned slots and 5 genre tags doesn't need a plan longer than a page to
  cover them well.

## Auditing song-description completeness

Per-clip `caption` isn't in the paginated profile listing (`blog-contract.md`'s
endpoint) — it only comes back from `GET /api/clip/{id}/`, one request
per song. For a catalog-sized audit (dozens to ~100 songs):

- Fetch the basic clip list once (id, title, play_count) from the
  paginated endpoint, then fetch each clip's full detail with modest
  concurrency (5 workers was fine) and a small stagger between requests
  (~150ms) — Suno rate-limits sustained bursts, and a full-catalog audit
  is exactly the kind of sustained load that trips it.
- Sort empty-caption results by `play_count` descending — that's the
  actual prioritization signal (a highly-played song with no caption is
  a bigger gap than an obscure one).
- While reading captions that do exist, watch for the corrupted-old-data
  pattern in `write-api.md` (accented characters replaced by plain
  spaces) — flag it and propose the corrected text in the audit report;
  do not call `set_metadata` to fix it until Franklin explicitly
  authorizes that specific change, same as any other write.
- Report the completeness percentage and a prioritized list; don't draft
  the missing captions in the same breath — that's the next, separate,
  Franklin-reviewed step (see "Song descriptions" in the template above).

## Applying the plan

- Never apply the whole plan in one session. Each piece (the bio, one
  pinned caption, one playlist) is drafted, brought to Franklin, and only
  sent — via `write-api.md` — once he explicitly authorizes that specific
  change. Having a plan is not standing authorization.
- Propose one scoped piece at a time, not the whole plan at once: it keeps
  each change reviewable and the plan/profile diff legible.
- After a piece is applied (and its read-back verified, per
  `write-api.md`'s propagation-delay note), update the plan document to
  reflect what's now live, so the plan never silently drifts out of sync
  with the real profile the way the bio and pinned captions did before
  this mode existed.
- Treat "the plan says X but the profile still shows Y" as a normal,
  expected state between sessions — it's a to-do list, not a bug, as long
  as the plan document says so explicitly (e.g. a checklist or status per
  section).

## Review cadence

Two kinds of trigger, either one is sufficient:

- **Event-based**: a new song opens a potential new thread, a pinned song
  stops representing its thread well, or Franklin says something feels
  off.
- **Time-based**: at the start of any suno-profile session, check the
  plan's `Last reviewed` date. If it's been more than a week (or the plan
  has no date, meaning it's never been reviewed), run the self-critique
  below before doing anything else that session — don't wait for Franklin
  to ask.

A review session re-reads the live profile state (not just the plan
document — the two can have drifted) and reconciles differences before
proposing new changes.

## Self-critique checklist

The actual content of a time-triggered review. Go through the live
profile — not the plan document, the real bio/tags/pinned songs/playlists
via `GET /api/profiles/v2/{handle}` (see `write-api.md`'s "Reading the
profile") — and answer each honestly, citing specifics rather than a vague
pass/fail:

- **Taste**: Does the pinned-song slate still read as a coherent set (see
  `curation-plan.md`'s "Pinned songs" section and `seo-and-taste.md`'s
  curation guidance)? Any redundant slots making the same pitch? Any
  strong recurring thread with no pinned representative?
- **SEO**: Does the bio still state genre/sound in the first sentence,
  avoid superlatives, and carry a concrete detail (per
  `seo-and-taste.md`)? Do the 5 genre tags still mix broad/searchable with
  specific/differentiating, or has one become dead weight? Do pinned-song
  captions still say something specific and non-redundant with each
  other?
- **Consistency**: Does the bio's identity claim still match what the
  recurring-threads list and the actual catalog show? Has a new song
  contradicted or outgrown the identity statement? Do playlist
  titles/descriptions still match their stated thesis, or has one drifted
  into "everything tagged X"?

Report the findings to Franklin as a short list — what still holds, what's
drifted, and what you'd propose changing — then update the plan's
`Last reviewed` date once the review itself (not necessarily every
resulting change) is done. Changes proposed by a self-critique follow the
same rule as any other write in this skill: draft it, get Franklin's
explicit authorization for that specific change, only then send it.
