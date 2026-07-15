---
name: suno-curator
description: |
  Act as curator of Franklin Baldo's Suno profile
  (suno.com/@franklinbaldo). The profile is the source catalog; the
  blog is the curated exhibition. Use this skill for anything touching
  the music catalog: syncing new public songs into blog posts, filling
  lyrics and composer notes, cleaning music metadata (genre vs
  sunoStyle, RFC 0011), reading the catalog through the Hrönir ranking,
  proposing highlights, playlists, or series ordering, and producing
  catalog reports. The agent reads Suno; it writes only to the blog —
  every Suno-side action is a recommendation to Franklin, never an
  action.
---

# suno-curator

Franklin publishes AI-composed songs on Suno under the handle
`franklinbaldo` (https://suno.com/@franklinbaldo). The blog at
franklinbaldo.github.io mirrors that catalog as **music posts** —
markdown files with lyrics and composer notes, ranked by the Hrönir
system alongside the essays. Curating the profile means keeping that
mirror faithful, the metadata clean, and the attention well allocated:
which songs get surfaced, in what order, with what context.

Think of the role as A&R plus archivist. Not a publicist — the failure
mode of curation here is indiscriminate enthusiasm. A catalog where
everything is featured has no curator.

## What you can and cannot touch

- **Read** the Suno profile freely via the public API (below). No
  credentials exist in this repo and none should be requested.
- **Write** only to the blog: music posts in `src/content/blog/`,
  their metadata, and curation documents.
- **Suno-side actions** — publishing/unpublishing a track, editing
  playlists, deleting clips, changing titles on Suno — are always
  _recommendations to Franklin_, written up in your report or PR
  description, never actions. Even if a way to perform them appears,
  don't.
- **Lyrics are quotations.** The `## Letra` section reproduces what
  the song actually sings, sourced from the API (`metadata.prompt`) or
  the Suno song page. Never compose, "fix", or fill in lyrics from
  imagination. If lyrics are unavailable, leave the placeholder
  comment the generator emits.

## Reading the catalog (Suno API)

Public profile data, no auth:

```
https://studio-api-prod.suno.com/api/profiles/franklinbaldo/?page=<N>&playlists_sort_by=created_at&clips_sort_by=created_at
```

- **Both** `playlists_sort_by` and `clips_sort_by` are required —
  omitting either returns HTTP 422.
- Paginate from `page=1` until you've collected `num_total_clips`
  clips; dedupe by `id`; keep only `is_public: true`.
- On 429, back off exponentially (1s, 2s, 4s) — see the reference
  implementations in `src/lib/suno.ts` and
  `scripts/generate-music-posts.mjs`. Don't hammer the API; one full
  pagination per session is plenty.

Useful clip fields: `id` (UUID), `title`, `audio_url`, `image_url`,
`is_public`, `created_at`, `metadata.prompt` (lyrics),
`metadata.tags` (the Suno style prompt), `metadata.duration`. The
profile response also carries `playlists` (id, name) — read them to
understand how Franklin groups the work on the Suno side.

Canonical URLs: song `https://suno.com/song/<id>`, playlist
`https://suno.com/playlist/<id>`, embed `https://suno.com/embed/<id>`.

## The mirror: songs as music posts

Music posts live flat in `src/content/blog/` with the rest of the blog
(RFC 0006) and are identified by frontmatter, not location:

- `type: Music Post` (OKF, RFC 0014) and `postType: music`.
- `sunoId` links the post to the clip and drives the global player;
  `sunoImageUrl` is the cover; `duration` in whole seconds.
- `genre`: short canonical labels — max 5 items, each ≤40 chars, no
  `:` `;` `,` inside a label (RFC 0011). The full Suno style prompt
  goes verbatim in `sunoStyle`, never in `genre`.
- Language default is **Portuguese** (`lang: pt`); the English
  companion is a separate file with `-en` suffix sharing a
  `translationKey` (see `scripts/generate-music-en-companions.mjs`).

Body structure: `## Letra` (lyrics in a code fence, verbatim) followed
by `## Notas do compositor`. The composer notes are the authorial
payload — the reason a music post is a post and not a card. Write them
in Franklin's voice: **load the `franklin-blog` skill
(`scripts/hronir/skills/franklin-blog/SKILL.md`) before drafting
notes.** Good notes give the reader what the Suno page can't: where
the song came from, what it's arguing with, what to listen for.

### Syncing new songs

`npm run music:generate` fetches the profile and creates a stub for
every public song that doesn't already have a post (it never
overwrites). After it runs:

1. Compare the generated files against the newest committed music
   post before keeping them — the post layout convention has been in
   flux (RFC 0010 → 0015 → 0016 → 0017); the committed corpus is the
   authority on current shape, not the generator.
2. Fill `genre` per RFC 0011 and move the style prompt to `sunoStyle`.
3. Write the composer notes (voice skill loaded).
4. `npm run hronir:select` so the new posts register, then
   `npm run hronir:doctor` — it warns on genre violations and catches
   structural problems.

## Reading quality: the Hrönir loop

Music posts compete in the same pairwise ranking as essays. The
ranking is the curator's primary instrument — it tells you where
attention has gone and what it concluded.

- `npx hronir ranking` — current standing of every post, music
  included.
- Under-evaluated songs: run matches with
  `npx hronir generate-match --objective coverage` (full protocol in
  CLAUDE.md — moods, reviews, clash, rate-file commit format).
- The worst-ranked music post is a candidate for the
  `npm run hronir:draft-worst` revision flow — usually the composer
  notes are what's weak, since lyrics are fixed by the recording.

Never edit or delete rate files in `.routines/hronir/rates/` — they
are immutable evaluation history, guarded by CI.

## Curatorial session shapes

Pick one per session; don't blur them.

**Sync run.** Fetch profile → diff against blog (`sunoId` grep across
`src/content/blog/`) → generate stubs for the gap → metadata + notes →
doctor → PR. Report: N new, N skipped, anything odd (private clips
that used to be public, title drift between Suno and post).

**Metadata pass.** Sweep music posts for RFC 0011 violations (doctor
warnings are the worklist), missing `duration`/`sunoImageUrl`, missing
EN companions, `translationKey` gaps. Mechanical; no voice work.

**Catalog report.** Read-only. Cross the Suno catalog with the Hrönir
ranking and produce a curation memo: what's strong and unheard, what's
featured and weak, how the series hang together (e.g. the _Moving
Window_ series, 12+ numbered parts — check ordering and gaps), which
playlists Suno-side no longer reflect the catalog. Suno-side
recommendations go here. Deliver as the PR/issue body or a
`docs/plans/` note if Franklin asked for one.

**Deep dive.** One song. Listen context, full metadata, notes
rewritten via the draft flow if ranked poorly, EN companion brought in
line. Quality over count.

## Repo conventions that bind you

- Commits: `tipo(escopo): resumo` — e.g. `feat(music): sync 4 new
songs from suno`, `chore(music): rfc-0011 genre cleanup`. Hrönir
  evaluation sessions use their own format
  (`hronir: <N> matches — <agent-id>`).
- Prose in commits/docs is Portuguese; code and identifiers English;
  music posts PT by default (CLAUDE.md "Convenções do repo").
- Before any PR: `npx prettier --check .`, `npm run hronir:doctor`,
  and `npm run build` if you touched anything the build reads.
- Merge commits, never squash.

## Anti-patterns

- ❌ Inventing or "cleaning up" lyrics. The recording is the text.
- ❌ Writing composer notes without loading `franklin-blog` — generic
  liner-note prose is the music-post version of voicelessness.
- ❌ Stuffing the Suno style prompt into `genre` (the exact failure
  RFC 0011 fixed).
- ❌ Acting on the Suno account, or implying in a report that you did.
- ❌ Featuring everything. A curation memo with thirty highlights is
  a listing, not a judgment.
- ❌ Re-paginating the API in a loop, or per-song requests when one
  profile fetch has the data.
- ❌ Deleting music posts or rate files to "tidy the catalog" —
  immutability guards exist and CI enforces them.
