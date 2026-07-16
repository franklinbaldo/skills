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

import { writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { mintBearerToken } from "./mint-bearer-token.mjs";

const API_BASE = "https://studio-api-prod.suno.com";
const DEFAULT_HANDLE = "franklinbaldo";
const CONCURRENCY = 5;
const STAGGER_MS = 150;

export function parseArgs(argv) {
  const args = { out: null, handle: DEFAULT_HANDLE };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--out") args.out = argv[++i];
    else if (arg === "--handle") args.handle = argv[++i];
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return args;
}

async function fetchJson(url, jwt) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${jwt}` } });
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

async function fetchAllClips(handle, jwt) {
  const clips = new Map();
  const playlistRefs = [];
  let page = 1;
  let total = null;
  while (total === null || clips.size < total) {
    const body = await fetchJson(
      `${API_BASE}/api/profiles/${handle}/?page=${page}&playlists_sort_by=created_at&clips_sort_by=created_at`,
      jwt
    );
    total = body.num_total_clips ?? total;
    const pageClips = body.clips ?? [];
    if (pageClips.length === 0) break;
    for (const c of pageClips) {
      if (c.is_public) clips.set(c.id, { id: c.id, title: c.title, play_count: c.play_count ?? 0 });
    }
    if (page === 1) playlistRefs.push(...(body.playlists ?? []));
    page++;
  }
  return { clips, playlistRefs };
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
  };
}

async function fetchAllClipDetails(clipIds, jwt) {
  const details = [];
  let idx = 0;
  async function worker() {
    while (idx < clipIds.length) {
      const i = idx++;
      details.push(await fetchClipDetail(clipIds[i], jwt));
      await new Promise((r) => setTimeout(r, STAGGER_MS));
    }
  }
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  return details;
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
    tracks: (body.playlist_clips ?? []).map((pc) => pc.clip.title),
  };
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
    lines.push(`### ${clip.title}`);
    lines.push("");
    lines.push(`- ID: ${clip.id}`);
    lines.push(`- Play count: ${clip.play_count}`);
    lines.push(`- Duration: ${clip.duration ?? "?"}s`);
    lines.push(`- Style tags: ${clip.tags}`);
    lines.push(`- Caption: ${clip.caption || "(empty)"}`);
    lines.push("");
    lines.push("Lyrics/prompt:");
    lines.push("");
    lines.push("```");
    lines.push(clip.lyrics);
    lines.push("```");
    lines.push("");
  }

  return lines.join("\n");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const jwt = await mintBearerToken();

  console.error(`Fetching clip list for ${args.handle}...`);
  const { clips, playlistRefs } = await fetchAllClips(args.handle, jwt);
  console.error(`Found ${clips.size} public clips, ${playlistRefs.length} playlists. Fetching details...`);

  const [clipDetails, playlists, profile] = await Promise.all([
    fetchAllClipDetails([...clips.keys()], jwt),
    Promise.all(playlistRefs.map((p) => fetchPlaylistDetail(p.id, jwt))),
    fetchProfile(args.handle, jwt),
  ]);

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
