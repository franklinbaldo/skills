# Suno write API (reverse-engineered)

**Status: live, gated on authorization.** This is `suno-profile`'s actual
write surface — see `SKILL.md`'s non-negotiable boundaries: every request
built from this reference still requires Franklin's explicit per-action
authorization before it's sent, but once given, this skill does send it.
This file exists so that construction and verification don't have to
rediscover the API from scratch each session.

Discovered 2026-07-16 by capturing real browser requests (DevTools Network
tab) against a live, authenticated session and confirming each field by
reading the value back afterward. Not from any public/official Suno
documentation — Suno does not publish a write API.

## Base

- Host: `https://studio-api-prod.suno.com`
- Auth: `Authorization: Bearer <Clerk JWT>` header, captured from a live
  browser session (no public way to mint one headlessly). Tokens are
  short-lived (`exp` claim, roughly 1 hour) and session-bound — do not persist
  them in the repo or in skill files.
- Most write calls are `POST` with a trailing slash; a couple of exceptions
  are noted below. `DELETE` is **not** supported anywhere in this API
  (confirmed: `405 Method not allowed`) — don't reuse REST conventions from
  unrelated APIs without testing them first.
- Success does not always mean the change is visible on the very next `GET`
  — there is a short read-after-write propagation delay (observed up to
  ~10s) on several endpoints. Don't conclude a write failed from one stale
  read; re-check after a few seconds.

## Song (clip) metadata

`POST /api/gen/{clip_id}/set_metadata/`

Accepts a subset of:

```json
{
  "title": "...",
  "lyrics": "...",
  "caption": "...",
  "caption_mentions": {"user_mentions": []},
  "remove_image_cover": false,
  "remove_video_cover": false,
  "image_s3_id": "image_<clip_id>"
}
```

- This is the same endpoint the "Edit song details" modal submits as a
  whole — even fields the user didn't touch get resent, unchanged.
- Cover image is set via `image_s3_id` (e.g. `image_<clip_id>`), **not**
  `image_url`. A plain `image_url` field is silently ignored (accepted with
  200, never applied).
- Tags/genre are **not** part of this endpoint's schema (top-level `tags`
  and nested `metadata.tags` are both silently ignored).

## Song tags / genre

`POST /api/gen/{clip_id}/set_display_tags`

```json
{"display_tags": "folk, spoken-word, Latin, borges"}
```

Comma-separated string. Confirmed this is genuinely a separate write path
from `set_metadata` — the two were tried independently. Read back via the
top-level `display_tags` field on `GET /api/clip/{clip_id}/` (not
`metadata.tags`, which holds a different, longer AI-style description and
is not directly settable this way).

## Cover image generation (AI)

`POST /api/gen/prompt_image/`

```json
{
  "generated_text_id": "...",
  "prompt": "...",
  "clip_id": "...",
  "quantity": 2,
  "image_gen_category": "advanced"
}
```

## Pinning a song to the profile

`POST /api/profiles/pin-clip/{clip_id}`

```json
{"submit_to_contest": false, "max_pins": 5}
```

`max_pins` in the captured request was `5`, not Suno's actual 10-pin UI
limit — meaning unrelated to the true cap, or a stale/plan-specific value.
**Do not trust it as documentation of the real limit; treat 10 as the
UI-stated cap until this is understood better.**

Read back the current pinned set via `GET /api/profiles/v2/{handle}`,
finding the `feed` entry with `feed_id: "user_pinned_songs"` — not a
simple boolean on the clip object (`GET /api/clip/{id}/` doesn't reliably
include `is_pinned`; only the `pin-clip` response itself does, for the
clip just pinned).

**Known bug, observed directly, twice:** pinning a new clip evicted an
*already-pinned, unrelated* clip from the set — with only 3-4 total pins
active, nowhere near the stated `max_pins: 5` or the UI's 10-slot cap.
Verify the full pinned set after every pin/unpin, not just the clip you
touched. Separately, an evicted-then-re-pinned clip **lost its pin
caption** (reverted to none) even though the clip itself came back —
re-apply the caption after any unpin/re-pin cycle, don't assume it
survived. No corresponding `unpin-clip`-style endpoint has been captured
yet; presumably exists but unmapped.

## Pinned-song caption (profile page)

`PUT /api/profiles/pin-caption/{clip_id}`

```json
{"caption": "..."}
```

Sets the caption shown under a song **on the profile's pinned-songs
section**, not the song's own `caption` field (that one lives on
`set_metadata` and shows on the song's own page). Distinct field, distinct
endpoint, distinct storage: read back via `GET /api/profiles/v2/{handle}`'s
top-level `pin_captions` array (`[{"clip_id", "caption"}, ...]`), not from
the clip object itself. Cleared by the eviction bug above — see "Pinning
a song to the profile."

## Song visibility (publish/unpublish)

`POST /api/gen/{clip_id}/set_visibility/`

```json
{"is_public": true, "submit_to_contest": false}
```

## Reading the profile

Two distinct, non-overlapping endpoints — using the wrong one for a given
field is a real gap, not just a style choice:

- `GET /api/profiles/{handle}/?page=<N>&playlists_sort_by=created_at&clips_sort_by=created_at`
  (unversioned, no `v2`) — paginated **clips and playlists listing**. This
  is what `suno-curator`'s `blog-contract.md` and `audit-catalog.mjs`
  use. It does **not** carry the bio, genre tags, pin captions, or social
  links — don't expect them here.
- `GET /api/profiles/v2/{handle}` — the actual profile object:
  `metadata` (display name, handle, avatar/cover URLs), `bio`
  (`profile_description`, `user_inputted_genres`, `section_order`),
  `social_links`, top-level `pin_captions`
  (`[{"clip_id", "caption"}, ...]`), `stats` (followers, plays, clip
  count), and `feed` (pinned songs and other profile sections — see
  `pin-caption`'s note above on where `is_pinned` shows up). This is the
  endpoint for bio/genre/pin-caption work and for `curation-plan.md`'s
  self-critique, which reads live profile state before proposing changes.

## Profile (bio, genres, social links)

`PATCH /api/profiles/v2/{handle}`

```json
{
  "metadata": {"display_name": "...", "handle": "..."},
  "bio": {
    "profile_description": "...",
    "user_inputted_genres": ["ambient", "folk", "..."],
    "section_order": ["pinned_songs", "songs", "hooks", "playlists", "personas"]
  },
  "social_links": {
    "spotify_link": null,
    "soundcloud_link": null,
    "x_link": "https://x.com/...",
    "instagram_link": null,
    "youtube_link": null,
    "tiktok_link": null
  }
}
```

This is a full-object PATCH — send every field, not just the one being
changed, or the omitted fields may be cleared. Confirmed the hard way: an
early capture accidentally overwrote the live profile bio with placeholder
text while mapping this endpoint.

## Playlists

| Action | Endpoint | Body |
|---|---|---|
| Create | `POST /api/playlist/create/` | `{"name": "..."}` |
| Edit metadata | `POST /api/playlist/set_metadata` | `{"playlist_id", "name", "description", "image_url"}` (cover as a base64 `data:image/...` URI, unlike song covers) |
| Visibility | `POST /api/playlist_reaction/{playlist_id}/set_visibility/` | `{"is_public": bool}` |
| Add/remove/reorder songs | `POST /api/playlist/update_clips/` | `{"playlist_id", "update_type": "add"\|"remove"\|"remove_by_id"\|"reorder", "metadata": {"clip_ids": [...]}, "recommendation_metadata": {}}` |
| Delete | `POST /api/playlist/trash/` | `{"playlist_id": "..."}` |

Known issues, observed directly:

- `update_clips` with `update_type: "remove"` or `"remove_by_id"` returned a
  generic `500 An unexpected error occurred` (`error_type: "server_error"`)
  every time it was tried, even though the shape matches the schema (a
  malformed body gets a clean `422` with the accepted enum values instead).
  This looks like a real bug in Suno's backend, not a client-side mistake.
  Despite the 500, the removal was later observed to have actually applied
  (confirmed on a delayed re-read) — the failure may be in the response
  path, not the mutation itself. Treat a 500 here as "maybe applied,
  reverify before retrying" rather than "definitely failed."
- `trash` on a non-empty playlist returned `204` immediately but the
  playlist stayed `is_trashed: false` for longer than the usual propagation
  delay; it did eventually take effect. Empty playlists trashed cleanly and
  immediately.

## Deliberately not verified

- Bulk/multi-song operations beyond playlists (e.g. batch visibility
  toggles) — not tested.
- Whether `set_metadata`'s `lyrics` field has a length limit or markdown
  handling.
- Rate limits on any of the above.
