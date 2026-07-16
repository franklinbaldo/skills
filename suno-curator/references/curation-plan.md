# Curation plan: template and process

A curation plan is the answer to "what should this Suno profile, as a
whole, say and show?" — as opposed to the field-by-field write work in
`write-api.md` or the per-field wording advice in `seo-and-taste.md`. It
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

## Applying the plan

- Never apply the whole plan in one session. Each apply session picks one
  scoped piece (the bio, one pinned caption, one playlist) — same
  discipline as any other write covered in `write-api.md`, including
  explicit authorization before touching live data.
- After applying a piece, update the plan document itself to reflect what's
  now live, so the plan never silently drifts out of sync with the real
  profile the way the bio and pinned captions did before this mode
  existed.
- Treat "the plan says X but the profile still shows Y" as a normal,
  expected state between sessions — it's a to-do list, not a bug, as long
  as the plan document says so explicitly (e.g. a checklist or status per
  section).

## Review cadence

- No fixed schedule — review when: a new song opens a potential new thread,
  a pinned song stops representing its thread well, Franklin says something
  feels off, or it's been long enough that neither of you remembers what's
  actually live vs. planned.
- A review session re-reads the live profile state (not just the plan
  document — the two can have drifted) and reconciles differences before
  proposing new changes.
