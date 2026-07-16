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
- Auth: `Authorization: Bearer <Clerk JWT>` header. Tokens are short-lived
  (`exp` claim, roughly 1 hour) and session-bound.

### Two-tier auth: ephemeral Bearer vs. durable Clerk cookie

Suno uses Clerk for auth. Two distinct secrets exist, with very different
risk profiles:

| Secret | Lifetime | Renewable without the user? | Risk if leaked |
| --- | --- | --- | --- |
| Bearer JWT (`Authorization` header) | ~1 hour | No — expires on its own | Low — short window, dies unattended |
| Clerk `__client` session cookie (`auth.suno.com`, httpOnly) | Long-lived, renewable | Yes | **High — equivalent to the account password** |

The axis that matters isn't read-vs-write, it's **interactive-vs-autonomous**.
Interactive write sessions (Franklin present) only ever need a fresh Bearer.
Autonomous/scheduled writes would need the durable cookie — which is why
storing it at all is a deliberate, explicit decision, not a convenience
default.

**Minting a fresh Bearer from the cookie:**
`GET https://auth.suno.com/v1/client?__clerk_api_version=<ver>&_clerk_js_version=<ver>`,
sent with the `__client` cookie attached, returns the current Clerk client
object; `response.sessions[0].last_active_token.jwt` is a fresh Bearer JWT.
This is exactly what `clerk-js` calls in the background on every page load —
confirmed live via Chrome DevTools Protocol (`Network.getCookies` to read the
httpOnly cookie value directly from the browser's cookie jar, since it's
unreadable from page JS; `Network.requestWillBeSent`/`responseReceived` to
observe the call). Scripted end-to-end in this skill:

- `scripts/login-and-capture.mjs` — launches a plain, non-automated
  `chrome.exe` process (not Playwright's own launcher, which flips
  `navigator.webdriver` and trips Google's "this browser may not be secure"
  OAuth block — a fingerprinting check, unrelated to which Chrome profile is
  used) on a fresh, isolated `--user-data-dir` (the true default profile
  still refuses remote debugging outright — a separate, hard restriction),
  then attaches Playwright to it via `chromium.connectOverCDP`. Franklin
  logs in himself in that window; the script only polls
  `auth.suno.com/v1/client` (reusing the browser's cookies automatically)
  until it reports an `active` session with a signed-in user — the mere
  presence of a `__client` cookie is **not** sufficient, Clerk sets one for
  anonymous visitors too. Once confirmed, the cookie is stored in
  **Windows Credential Manager** via `scripts/credmgr.ps1` (P/Invoke to
  `advapi32.dll`'s `CredWrite`/`CredRead`/`CredDelete` — the actual OS
  keyring on Windows, equivalent to what `python-keyring`'s `wincred`
  backend would use; reached this way since no Python runtime is installed
  in this environment). The cookie value is never printed or written to a
  plaintext file — piped via stdin into the credential store. The browser
  and its temporary profile are torn down afterward (`taskkill /T` for the
  whole process tree, since a CDP-attached-not-launched browser survives a
  plain Playwright `close()`).
- `scripts/mint-bearer-token.mjs` — reads the stored cookie back and calls
  the Clerk endpoint above to mint a fresh Bearer on demand. Verified live:
  cookie → minted Bearer → `200` from `studio-api-prod.suno.com/api/session/`.
- `scripts/keyring.mjs`'s `deleteSecret(target)` — no script calls this
  automatically; it's the manual credential-rotation step. If Franklin ever
  wants to revoke the stored cookie (e.g. after logging out everywhere, or
  suspecting the credential store was exposed), run
  `node -e "import('./keyring.mjs').then(k => k.deleteSecret('suno-clerk-client-cookie'))"`
  from `suno-profile/scripts/`, then re-run `login-and-capture.mjs` to
  capture a fresh cookie.

**What this skill still won't do:** touch the cookie or credential store
without Franklin present to log in and trigger the capture, or use a minted
Bearer for anything beyond the single authorized action of that moment —
storing the cookie removes the *re-paste-every-hour* friction, it does not
by itself authorize unattended writes. An autonomous/scheduled write mode
(e.g. a GitHub Actions secret holding this same cookie) is a further,
separate decision — not yet made — because it changes the blast radius of a
leak from "this machine, this Windows user" to "anyone with access to that
secret store."

Back to the basics that apply regardless of which auth path minted the
Bearer:

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

**Known historical data-quality issue, found and fixed live:** some older
song `caption` values (written well before this session, by whatever
client wrote them at the time) have every accented character replaced by
a plain space — e.g. `"M sica"` instead of `"Música"`. Verified with an
isolated, from-scratch `curl` (bypassing any script, straight to disk,
inspected at the byte level: the character in place of `ú` is byte `32`,
an ordinary space) that this is genuine stored corruption on Suno's side,
not an artifact of any fetch/parse pipeline. The current write path
handles UTF-8 correctly — a same-session round-trip test (write a normal
accented string via `set_metadata`'s `caption`, wait out propagation
delay, re-read from scratch) came back byte-correct. **Fix: just rewrite
the caption with normal UTF-8 text; no special encoding, HTML entities,
or NFD-vs-NFC handling needed.** Treat any caption with this exact
pattern (accented letters missing, replaced by a bare space, and nowhere
else does the surrounding text look truncated) as this known issue, not
a new bug to investigate from scratch.

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

## Trashing a song (clip)

`POST /api/gen/trash`

```json
{"trash": true, "clip_ids": ["<clip_id>", "..."]}
```

Captured live 2026-07-16, both directions: `{"trash": true, ...}` then
`{"trash": false, ...}` against the same `clip_id` — confirms this is a
toggle (trash/restore), not literally the client always sending `true`. Not
yet confirmed whether it's genuinely reversible indefinitely or only within
some retention window before permanent deletion — treat a trash as a real
action needing the same read-back verification discipline as any other
write, not as a risk-free no-op just because `false` exists. Takes a batch
(`clip_ids` is a list, not a single id). This is the real "delete a song"
action —
`DELETE` as an HTTP method is still unsupported everywhere in this API (see
"Base" above); Suno's own client uses this POST endpoint instead, the same
shape playlists' own `trash` endpoint uses.

Per `SKILL.md`'s non-negotiable boundaries, this is the one action in this
reference that most needs per-clip explicit authorization before sending —
verify the exact clip_id(s) with Franklin immediately before the call, not
from a stale list, since a batch call trashes everything in `clip_ids` in
one shot with no per-item confirmation from the API itself.

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

**Correction (2026-07-16):** an earlier version of this section claimed
pinning a new clip could evict an unrelated already-pinned clip, based on
a pinned song disappearing during a live session. That was a wrong causal
inference — the disappearance was Franklin manually unpinning a clip
himself in the same window, not an effect of this endpoint. Confirmed
independently the same day: pinning a 5th clip (`Beatriz`) onto an
existing 4-clip pinned set left all 4 prior clips **and** their pin
captions intact, verified via a fresh `GET /api/profiles/v2/{handle}`
immediately after. Treat `pin-clip` as additive and non-destructive to
the rest of the pinned set unless a future observation reproduces
otherwise. It remains possible that a clip **manually** unpinned (by
whatever means) and later re-pinned loses its pin caption — that
specific sequence hasn't been cleanly isolated from the API's own
behavior, so don't assume it either way; just re-verify the full pinned
set and captions after any pin/unpin/re-pin sequence, same general
discipline as the propagation-delay note above, not because of a
confirmed bug. No corresponding `unpin-clip`-style endpoint has been
captured yet; presumably exists but unmapped.

## Pinned-song caption (profile page)

`PUT /api/profiles/pin-caption/{clip_id}`

```json
{"caption": "..."}
```

**Server-enforced hard limit: 500 characters.** Confirmed by the actual
error, not a guess: a 600-character caption is rejected with `400
{"detail": "Caption exceeds maximum length of 500 characters."}` — the
write is atomic (rejected outright, not truncated), so an over-length
caption never partially applies. Note this is a display constraint on
top of the hard limit: 500 characters is far more than reads well in the
UI — see `seo-and-taste.md`'s "Pinned-song captions" for the practical
target length, confirmed too long in Franklin's own real feedback the
first time a ~124-character caption was applied live.

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
- `POST /api/feed/v3` (cursor-paginated: `{"cursor": "..."}` after the
  first call, response carries `clips`, `has_more`, `next_cursor`) — the
  only endpoint that returns **every** clip regardless of visibility,
  public or private/unpublished. Neither endpoint above ever returns a
  private clip, even authenticated as the owner. Used by
  `scripts/export-catalog.mjs --include-private` and
  `quality-review.md`'s candidate-gathering step.

  **Confirmed live 2026-07-16: silently truncates under rapid
  pagination.** A burst of calls with only a ~150ms stagger produced a
  `200 OK` with an empty `clips` array and no `has_more`/`next_cursor` on
  what should have been a mid-feed page — not a `429` any retry-on-error
  logic would catch. Two consecutive full paginations with that short a
  stagger returned inconsistent totals (420, then 320) from the same
  account state; a 400ms+ stagger made consecutive runs agree (the
  shorter was a strict subset of the longer — truncation, not a shifting
  dataset). `export-catalog.mjs` and the blog repo's
  `generate-music-posts.mjs` both apply a 400ms+ stagger plus a retry on
  a suspiciously-empty non-first page before accepting it as the real end
  of the feed — treat a script without that fix as unreliable for
  anything that needs a complete count.

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

**`set_metadata` and `image_url`, confirmed live (2026-07-16):** passing
the *existing* cover's plain `https://` URL back in `image_url` fails
with `400 {"detail": "Failed to upload image"}` — the endpoint tries to
upload whatever string is given, and a plain URL isn't a valid upload
payload; it needs an actual base64 `data:image/...` URI to set a new
cover. **Omitting `image_url` entirely is safe** — confirmed the cover
survives untouched, along with `name`, when only `description` is sent.
So despite the `PATCH /api/profiles/v2/{handle}`-style "full object"
framing in the row above, `set_metadata` is closer to a genuine partial
update for fields you don't touch — still worth verifying the untouched
fields survived on the next read rather than assuming, since this
wasn't true of the profile endpoint.

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
