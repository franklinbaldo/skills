#!/usr/bin/env node
//
// Fetches the whole Suno catalog — every public song's full metadata
// (title, lyrics/prompt, style tags, caption, duration, play_count),
// every playlist (name, description, track list), and the profile itself
// (bio, genres, pin captions, pinned songs, social links, stats) — and
// assembles it into one consolidated markdown file. Meant as context for
// ask-gemini.mjs (or any other text-based Q&A), not as a publishable
// document — no editorial framing, just raw extracted data.
//
// Read-only: no writes to Suno. Reuses mint-bearer-token.mjs for auth.
//
// Usage:
//   node export-catalog.mjs [--out <path>] [--handle franklinbaldo]
//   node export-catalog.mjs --include-private   # also private/unpublished
//                                                  songs, via feed/v3

import { writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { mintBearerToken } from "./mint-bearer-token.mjs";

const API_BASE = "https://studio-api-prod.suno.com";
const DEFAULT_HANDLE = "franklinbaldo";
const CONCURRENCY = 5;
const STAGGER_MS = 150;

export function parseArgs(argv) {
  const args = { out: null, handle: DEFAULT_HANDLE, includePrivate: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--out") args.out = argv[++i];
    else if (arg === "--handle") args.handle = argv[++i];
    else if (arg === "--include-private") args.includePrivate = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return args;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Same exponential-backoff-on-429/5xx contract as the sibling scripts in
// this skill set (suno-curator/scripts/audit-catalog.mjs's fetchJson,
// gemini-audio-critic.mjs's withRetry) — this script makes a call per clip
// (dozens to ~100 per run), so a single transient failure without a retry
// would abort the whole export.
async function withRetry(fn, label) {
  for (let attempt = 0; attempt < 4; attempt++) {
    const response = await fn();
    if (response.ok) return response;
    if ((response.status === 429 || response.status >= 500) && attempt < 3) {
      await sleep(1000 * 2 ** attempt);
      continue;
    }
    const body = await response.text().catch(() => "");
    throw new Error(`${label}: HTTP ${response.status} ${body.slice(0, 500)}`);
  }
  throw new Error(`${label}: exhausted retries`);
}

async function fetchJson(url, jwt) {
  const res = await withRetry(() => fetch(url, { headers: { Authorization: `Bearer ${jwt}` } }), url);
  return res.json();
}

async function fetchAllClips(handle, jwt) {
  const clips = new Map();
  const playlistRefs = [];
  let page = 1;
  // num_total_clips is undocumented API surface (see
  // suno-curator/scripts/audit-catalog.mjs's identical guard) — if it's
  // ever missing/renamed, treat the total as unknown rather than letting a
  // stray 0 silently stop pagination after page 1.
  let total = null;
  while (total === null || clips.size < total) {
    const body = await fetchJson(
      `${API_BASE}/api/profiles/${handle}/?page=${page}&playlists_sort_by=created_at&clips_sort_by=created_at`,
      jwt
    );
    const rawTotal = Number(body.num_total_clips);
    if (Number.isFinite(rawTotal)) total = Math.max(0, rawTotal);
    const pageClips = body.clips ?? [];
    if (pageClips.length === 0) break;
    for (const c of pageClips) {
      // Strict === true, not a bare truthy check — an undocumented API
      // omitting this field on some clip shapes shouldn't be silently
      // treated the same as an explicit "private."
      if (c.is_public === true) {
        clips.set(c.id, { id: c.id, title: c.title, play_count: c.play_count ?? 0 });
      }
    }
    // Verified live 2026-07-16: `playlists` carries the full, identical
    // list on every page (not paginated itself), so reading it only once
    // from page 1 is correct, not an unverified assumption.
    if (page === 1) playlistRefs.push(...(body.playlists ?? []));
    page++;
  }
  return { clips, playlistRefs };
}

// The public profile endpoint above never returns private/unpublished
// clips, even authenticated as the owner — it's the same data a visitor
// sees. /api/feed/v3 (cursor-paginated, POST) is the real "my library"
// feed, returning every generation regardless of visibility. Its
// list-level is_public has been observed to disagree with the per-clip
// detail endpoint's — fetchClipDetail's value (fetched for every clip
// regardless of route) is treated as authoritative, this is only used to
// build the id list.
//
// Confirmed live 2026-07-16: this endpoint silently truncates under rapid
// pagination — a burst of calls with no delay produced a 200 OK with an
// empty clips array and no has_more/next_cursor on what should have been
// a mid-feed page (not a 429, so withRetry's error-status retry never
// sees it). Two consecutive full paginations with only a 150ms stagger
// returned 420 and then 320 results from the same underlying account
// state; with a 400ms stagger both runs agreed (the shorter was a strict
// subset of the longer — truncation, not a shifting dataset). Fixed two
// ways: a longer stagger, and retrying a suspiciously-empty non-first
// page a few times before accepting it as genuinely the end of the feed.
async function fetchAllClipsIncludingPrivate(jwt) {
  const auth = { Authorization: `Bearer ${jwt}`, "Content-Type": "application/json" };
  const clips = new Map();
  let cursor = null;
  let page = 0;
  while (true) {
    page++;
    const body = cursor ? { cursor } : {};
    let next;
    for (let attempt = 0; ; attempt++) {
      next = await fetchJsonWithBody(`${API_BASE}/api/feed/v3`, jwt, body);
      const looksTruncated = page > 1 && (next.clips ?? []).length === 0 && attempt < 3;
      if (!looksTruncated) break;
      console.error(`  page ${page}: suspiciously empty response, retry ${attempt + 1}/4...`);
      await sleep(1000 * 2 ** attempt);
    }
    for (const c of next.clips ?? []) {
      if (!clips.has(c.id)) clips.set(c.id, { id: c.id, title: c.title, play_count: c.play_count ?? 0 });
    }
    if (!next.has_more || !next.next_cursor || page > 150) break;
    cursor = next.next_cursor;
    await sleep(Math.max(STAGGER_MS, 400));
  }
  return clips;
}

async function fetchJsonWithBody(url, jwt, body) {
  const res = await withRetry(
    () =>
      fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${jwt}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    url
  );
  return res.json();
}

async function fetchClipDetail(id, jwt) {
  const body = await fetchJson(`${API_BASE}/api/clip/${id}/`, jwt);
  return {
    id,
    title: body.title,
    duration: body.metadata?.duration ?? null,
    tags: body.metadata?.tags ?? "",
    caption: body.metadata?.caption ?? body.caption ?? "",
    lyrics: body.metadata?.prompt ?? "",
    play_count: body.play_count ?? 0,
    is_public: body.is_public === true,
  };
}

// Per-item failures (a clip deleted mid-run, a transient error that
// survived withRetry's backoff) are collected rather than left to reject
// the whole batch — losing one clip out of ~100 shouldn't discard the
// other 99 that already succeeded.
async function fetchAllClipDetails(clipIds, jwt) {
  const details = [];
  const failures = [];
  let idx = 0;
  async function worker() {
    while (idx < clipIds.length) {
      const i = idx++;
      try {
        details.push(await fetchClipDetail(clipIds[i], jwt));
      } catch (error) {
        failures.push({ id: clipIds[i], message: error.message });
      }
      if (idx < clipIds.length) await sleep(STAGGER_MS);
    }
  }
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  return { details, failures };
}

async function fetchProfile(handle, jwt) {
  return fetchJson(`${API_BASE}/api/profiles/v2/${handle}`, jwt);
}

async function fetchPlaylistDetail(id, jwt) {
  const body = await fetchJson(`${API_BASE}/api/playlist/${id}`, jwt);
  return {
    id,
    name: body.name,
    description: body.description ?? "",
    is_public: body.is_public,
    // A playlist can contain a track that was later deleted or made
    // private by its owner — `clip` may be null/absent for that entry.
    tracks: (body.playlist_clips ?? [])
      .map((pc) => pc.clip?.title)
      .filter(Boolean),
  };
}

// Same per-item resilience as fetchAllClipDetails — one bad playlist
// shouldn't discard every already-fetched clip detail.
async function fetchAllPlaylistDetails(playlistRefs, jwt) {
  const results = await Promise.allSettled(playlistRefs.map((p) => fetchPlaylistDetail(p.id, jwt)));
  const playlists = [];
  const failures = [];
  results.forEach((r, i) => {
    if (r.status === "fulfilled") playlists.push(r.value);
    else failures.push({ id: playlistRefs[i].id, message: r.reason?.message });
  });
  return { playlists, failures };
}

// Picks a fence longer than the longest run of backticks already present
// in the text, so lyrics/prompts that happen to contain literal ``` (e.g.
// a pasted code example) can't prematurely close the block and corrupt
// every song listed after it in the output.
function codeFenceFor(text) {
  const runs = text.match(/`+/g) ?? [];
  const longest = runs.reduce((max, run) => Math.max(max, run.length), 0);
  return "`".repeat(Math.max(3, longest + 1));
}

// Pure formatting function — exported for offline testing without a live
// Suno session. Takes already-fetched data and produces the markdown.
export function buildMarkdown({ handle, profile, clipDetails, playlists }) {
  const lines = [];
  lines.push(`# Suno catalog export: ${handle}`);
  lines.push("");
  lines.push(
    `Raw extracted data, not editorial content — generated for use as Q&A context, not for publishing as-is.`
  );
  lines.push("");

  lines.push("## Profile");
  lines.push("");
  lines.push(`- Display name: ${profile.metadata?.display_name ?? ""}`);
  lines.push(`- Bio: ${profile.bio?.profile_description ?? ""}`);
  lines.push(`- Genres: ${(profile.bio?.user_inputted_genres ?? []).join(", ")}`);
  lines.push(`- Social links: ${JSON.stringify(profile.social_links ?? {})}`);
  lines.push(`- Stats: ${JSON.stringify(profile.stats ?? {})}`);
  lines.push("");

  lines.push("## Pinned songs");
  lines.push("");
  const pinCaptions = new Map((profile.pin_captions ?? []).map((p) => [p.clip_id, p.caption]));
  const pinnedFeed = profile.feed?.items?.find((i) => i.content_id === "pinned_songs_feed")
    ?.content_item?.items ?? [];
  for (const item of pinnedFeed) {
    const clip = item.content_item;
    if (!clip) continue;
    lines.push(`- **${clip.title}** (${clip.id}) — pin caption: "${pinCaptions.get(clip.id) ?? ""}"`);
  }
  lines.push("");

  lines.push("## Playlists");
  lines.push("");
  for (const pl of playlists) {
    lines.push(`### ${pl.name}${pl.is_public ? "" : " (private)"}`);
    lines.push("");
    if (pl.description) lines.push(pl.description);
    lines.push("");
    lines.push(`Tracks: ${pl.tracks.join(", ")}`);
    lines.push("");
  }

  lines.push("## Songs");
  lines.push("");
  const sorted = [...clipDetails].sort((a, b) => b.play_count - a.play_count);
  for (const clip of sorted) {
    lines.push(`### ${clip.title}${clip.is_public ? "" : " (private/unpublished)"}`);
    lines.push("");
    lines.push(`- ID: ${clip.id}`);
    lines.push(`- Play count: ${clip.play_count}`);
    lines.push(`- Duration: ${clip.duration ?? "?"}s`);
    lines.push(`- Style tags: ${clip.tags}`);
    lines.push(`- Caption: ${clip.caption || "(empty)"}`);
    lines.push("");
    lines.push("Lyrics/prompt:");
    lines.push("");
    const fence = codeFenceFor(clip.lyrics);
    lines.push(fence);
    lines.push(clip.lyrics);
    lines.push(fence);
    lines.push("");
  }

  return lines.join("\n");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const jwt = await mintBearerToken();

  let clips, playlistRefs;
  if (args.includePrivate) {
    console.error(`Fetching FULL clip list (public + private) for ${args.handle}...`);
    clips = await fetchAllClipsIncludingPrivate(jwt);
    // feed/v3 doesn't carry playlist refs — reuse the public endpoint's
    // page-1 response for those regardless of --include-private.
    ({ playlistRefs } = await fetchAllClips(args.handle, jwt));
  } else {
    console.error(`Fetching public clip list for ${args.handle}...`);
    ({ clips, playlistRefs } = await fetchAllClips(args.handle, jwt));
  }
  console.error(`Found ${clips.size} clips, ${playlistRefs.length} playlists. Fetching details...`);

  const [{ details: clipDetails, failures: clipFailures }, { playlists, failures: playlistFailures }, profile] =
    await Promise.all([
      fetchAllClipDetails([...clips.keys()], jwt),
      fetchAllPlaylistDetails(playlistRefs, jwt),
      fetchProfile(args.handle, jwt),
    ]);

  if (clipFailures.length) {
    console.error(
      `Warning: ${clipFailures.length} clip(s) failed and are excluded: ${clipFailures.map((f) => `${f.id} (${f.message})`).join("; ")}`
    );
  }
  if (playlistFailures.length) {
    console.error(
      `Warning: ${playlistFailures.length} playlist(s) failed and are excluded: ${playlistFailures.map((f) => `${f.id} (${f.message})`).join("; ")}`
    );
  }

  const markdown = buildMarkdown({ handle: args.handle, profile, clipDetails, playlists });
  const outPath = args.out ?? `./catalog-export-${args.handle}.md`;
  await writeFile(outPath, markdown, "utf8");
  console.error(`Wrote ${markdown.length} chars to ${outPath}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(`export-catalog: ${error.message}`);
    process.exitCode = 1;
  });
}
