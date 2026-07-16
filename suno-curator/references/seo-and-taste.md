# Profile, description, and playlist quality: SEO + editorial taste

Guidance for *how to word* a Suno profile bio, song descriptions, and
playlist titles/descriptions well — as opposed to `write-api.md`, which
covers *how to send the request*. Still subject to this skill's
non-negotiable boundaries: these are recommendations to draft and hand to
Franklin, not things this skill applies to Suno on its own.

Synthesized 2026-07-16 from general music-streaming SEO practice (Spotify,
Apple Music, etc. — Suno doesn't publish its own SEO guidance) plus
Suno-specific profile facts. Sources at the bottom. Treat the general
streaming-platform advice as *adapted*, not *verified on Suno* — Suno isn't
a search-driven discovery platform the way Spotify is, but the same
mechanics (natural language over keyword-stuffing, specificity beats
genericness, consistency across fields) transfer to any place a human or an
LLM reads the text and decides whether to click.

## Suno-specific facts to work within

- Bio: up to 1,200 characters.
- Genres: up to 5, shown as a filter/keyword surface, not free text — see
  `write-api.md`'s `bio.user_inputted_genres`.
- Up to 10 songs can be pinned to the profile for priority visibility.
- Song `display_tags` (also via `write-api.md`) is a short comma-separated
  list, not the long-form AI-style `metadata.tags` description — treat it
  like Spotify genre tags, not like ad copy.

## Writing the profile bio

- State genre/sound in the first sentence — don't bury it.
- Write like a genuinely knowledgeable fan describing the sound to another
  fan, not like ad copy or a LinkedIn summary. Use specific sub-genre and
  texture language ("spoken-word over sparse classical guitar," not "great
  music for all moods").
- Include a concrete, factual detail (a series the catalog is known for, a
  recurring collaborator, a language/bilingual angle) instead of vague
  superlatives ("amazing," "best").
- Keep stage name / handle exactly consistent with how it appears
  elsewhere (the blog, social links) — this matters for both human search
  and for LLMs trying to attribute the work correctly when asked about it.
- Don't keyword-stuff the bio with a genre list; that reads as spam and
  wastes the 1,200 characters that could carry actual signal.

## Choosing genre tags

- Pick genres that are true simultaneously, not aspirational — 5 slots are
  precious, spend them on what a listener would actually search for to
  find this catalog specifically, not on broad umbrella terms alone.
- Mix one or two broad/searchable terms (e.g. "folk," "ambient") with one
  or two more specific ones that differentiate the catalog (e.g.
  "spoken-word," "bilingual PT/EN") — broad terms win volume, specific
  terms win the right listener.

## Song `display_tags`

- Same logic as profile genres, at song scale: 3–5 short terms a listener
  would search, not a restatement of the AI-generated style description.
- Keep them stable across a series (e.g. all "Moving Window" tracks sharing
  a tag) so the series reads as a set, not as disconnected one-offs.

## Playlist titles

- Be specific and evocative, not generic. "Late Night Drive Vibes" beats
  "Playlist 3." A title that names a mood, activity, or clear angle is what
  gets found and remembered.
- Front-load the searchable term, then let a second clause add color —
  e.g. "Bilingual Spoken-Word: Borges-Inspired Tracks," not a poetic title
  alone with no genre/mood anchor.

## Playlist descriptions

- Never leave it blank — an empty description reads as neglect and gives
  up all searchability for that playlist.
- Name the through-line explicitly: mood, activity, sub-genre, recurring
  theme, or the specific songs/series it collects. Someone deciding whether
  to click should be able to tell from the description alone what they're
  getting.
- Natural language, not a keyword list — write one or two real sentences
  a curator would say out loud, not a comma-stuffed tag dump.

## Playlist curation ("taste")

- A playlist earns its name by having a genuine through-line — pulling
  every private/unpublished track into one bucket isn't curation, it's a
  folder. Prefer smaller, sharply-defined playlists over one big
  everything-list.
- Order matters: build some flow (tempo, mood, or thematic progression)
  rather than dumping tracks in creation order. Avoid jarring adjacent
  jumps in energy or style unless that contrast is the explicit point.
- Cohesion across title, cover image, and description reinforces the same
  idea three times — mismatched signals (moody title, cheerful cover, blank
  description) undercut all three.
- When mixing well-known catalog highlights with lesser-known tracks, lead
  with something recognizable/strong so the playlist earns trust in the
  first slot, then use the rest to surface what deserves more attention —
  that's the actual curatorial job, not just compiling everything that
  fits a tag.

## Sources

- [Spotify artist profile optimization checklist — Musical SEO](https://musicalseo.com/blog/spotify-artist-profile-optimization-checklist/)
- [Generative Engine Optimization for Musicians (2026) | Chartlex](https://www.chartlex.com/blog/marketing/generative-engine-optimization-musicians-2026)
- [Spotify SEO 2026: Beyond the Playlist Pitch](https://artistrack.com/spotify-seo-2026-strategy/)
- [Why Your Artist Bio Matters & How to Write a Killer One | Tunepact](https://tunepact.com/blog/artist-bio-matters-write)
- [Music SEO: Why It's Essential and How to Leverage It | Tunepact](https://www.tunepact.com/blog/music-seo-strategy)
- [How to optimize your artist profile on streaming platforms – AIR Media-Tech](https://air.io/en/youtube-hacks/how-to-optimize-your-artist-profile-on-spotify-apple-music-and-other-streaming-platforms)
- [How to Curate Music Playlists: 7 Steps for Success](https://resources.onestowatch.com/how-to-curate-music-playlists/)
- [How to Write a Playlist Description That Gets Found in Search – PlaylistFeed](https://playlistfeed.com/2025/05/20/how-to-write-a-playlist-description-that-gets-found-in-search/)
- [Best Practices For Naming And Describing Your Playlists - FasterCapital](https://fastercapital.com/topics/best-practices-for-naming-and-describing-your-playlists.html)
- [How to Name Playlists for Growth and Discovery](https://www.artist.tools/post/how-to-name-playlists-for-growth-and-discovery)
- [Suno AI Profile Customization – July 2025 Update](https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/suno-ai-profile-customization-july-2025)
