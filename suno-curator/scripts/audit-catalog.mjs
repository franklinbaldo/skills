#!/usr/bin/env node

import { readFile, readdir } from "node:fs/promises";
import { extname, join, resolve } from "node:path";

const PROFILE_URL =
  "https://studio-api-prod.suno.com/api/profiles/franklinbaldo/";

function usage() {
  console.error(`Usage: node audit-catalog.mjs [options]\n\nOptions:\n  --repo <path>          Blog repository root (default: .)\n  --profile-json <path>  Offline Suno profile snapshot (one page or {pages:[...]})\n  --format <json|markdown>  Output format (default: markdown)\n  --help                 Show this help\n`);
}

function parseArgs(argv) {
  const args = { repo: ".", format: "markdown", profileJson: null };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--help") return { ...args, help: true };
    if (arg === "--repo") args.repo = argv[++i];
    else if (arg === "--profile-json") args.profileJson = argv[++i];
    else if (arg === "--format") args.format = argv[++i];
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!args.repo) throw new Error("--repo requires a path");
  if (!args.profileJson && args.profileJson !== null)
    throw new Error("--profile-json requires a path");
  if (!new Set(["json", "markdown"]).has(args.format))
    throw new Error("--format must be json or markdown");
  return args;
}

const sleep = (ms) => new Promise((resolvePromise) => setTimeout(resolvePromise, ms));

async function fetchJson(url) {
  for (let attempt = 0; attempt < 4; attempt++) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (response.ok) return response.json();
    if ((response.status === 429 || response.status >= 500) && attempt < 3) {
      await sleep(1000 * 2 ** attempt);
      continue;
    }
    throw new Error(`HTTP ${response.status} on ${url}`);
  }
  throw new Error(`Exhausted retries on ${url}`);
}

function pageUrl(page) {
  const url = new URL(PROFILE_URL);
  url.searchParams.set("page", String(page));
  url.searchParams.set("playlists_sort_by", "created_at");
  url.searchParams.set("clips_sort_by", "created_at");
  return url.toString();
}

function normalizePages(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.pages)) return payload.pages;
  return [payload];
}

function clipsFromPages(pages) {
  const byId = new Map();
  for (const page of pages) {
    for (const clip of page?.clips ?? []) {
      if (clip?.id && clip.is_public !== false && !byId.has(clip.id)) {
        byId.set(clip.id, clip);
      }
    }
  }
  return [...byId.values()];
}

async function loadProfile(profileJson) {
  if (profileJson) {
    const payload = JSON.parse(await readFile(resolve(profileJson), "utf8"));
    return clipsFromPages(normalizePages(payload));
  }

  const pages = [];
  const first = await fetchJson(pageUrl(1));
  pages.push(first);
  const total = Math.max(0, Number(first?.num_total_clips ?? 0));
  const seen = new Set((first?.clips ?? []).map((clip) => clip?.id).filter(Boolean));
  let page = 2;
  while (seen.size < total) {
    const next = await fetchJson(pageUrl(page));
    pages.push(next);
    const clips = next?.clips ?? [];
    if (clips.length === 0) break;
    for (const clip of clips) if (clip?.id) seen.add(clip.id);
    page++;
  }
  return clipsFromPages(pages);
}

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) files.push(...(await walk(path)));
    else if ([".md", ".mdx"].includes(extname(entry.name))) files.push(path);
  }
  return files;
}

function frontmatter(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  return match?.[1] ?? null;
}

function scalar(fm, key) {
  const match = fm.match(new RegExp(`^${key}:\\s*(.*)$`, "m"));
  if (!match) return null;
  const raw = match[1].trim();
  if (!raw || raw === "|-" || raw === ">-") return null;
  return raw.replace(/^(["'])(.*)\1$/, "$2");
}

function listField(fm, key) {
  const lines = fm.split(/\r?\n/);
  const index = lines.findIndex((line) => new RegExp(`^${key}:\\s*$`).test(line));
  if (index === -1) return [];
  const values = [];
  for (let i = index + 1; i < lines.length; i++) {
    const match = lines[i].match(/^\s+-\s+(.*)$/);
    if (!match) break;
    values.push(match[1].trim().replace(/^(["'])(.*)\1$/, "$2"));
  }
  return values;
}

function sourceDuration(clip) {
  const value = Number(clip?.metadata?.duration);
  return Number.isFinite(value) ? Math.round(value) : null;
}

async function loadPosts(repoRoot) {
  const blogDir = join(repoRoot, "src", "content", "blog");
  const posts = [];
  for (const path of await walk(blogDir)) {
    const text = await readFile(path, "utf8");
    const fm = frontmatter(text);
    if (!fm || scalar(fm, "postType") !== "music") continue;
    posts.push({
      path: path.slice(repoRoot.length + 1).replaceAll("\\", "/"),
      title: scalar(fm, "title"),
      sunoId: scalar(fm, "sunoId"),
      lang: scalar(fm, "lang"),
      translationKey: scalar(fm, "translationKey"),
      sunoImageUrl: scalar(fm, "sunoImageUrl"),
      duration: scalar(fm, "duration"),
      genre: listField(fm, "genre"),
    });
  }
  return posts;
}

function audit(clips, posts) {
  const clipsById = new Map(clips.map((clip) => [clip.id, clip]));
  const postsById = new Map();
  for (const post of posts) {
    if (!post.sunoId) continue;
    const group = postsById.get(post.sunoId) ?? [];
    group.push(post);
    postsById.set(post.sunoId, group);
  }

  const missingFromBlog = clips
    .filter((clip) => !postsById.has(clip.id))
    .map((clip) => ({ id: clip.id, title: clip.title ?? null }));
  const blogOnlyIds = [...postsById.keys()]
    .filter((id) => !clipsById.has(id))
    .map((id) => ({ id, posts: postsById.get(id).map((post) => post.path) }));

  const sameLanguageDuplicates = [];
  for (const [id, group] of postsById) {
    const byLang = new Map();
    for (const post of group) {
      const lang = post.lang ?? "missing";
      const paths = byLang.get(lang) ?? [];
      paths.push(post.path);
      byLang.set(lang, paths);
    }
    for (const [lang, paths] of byLang) {
      if (paths.length > 1) sameLanguageDuplicates.push({ id, lang, paths });
    }
  }

  const metadataGaps = [];
  const genreViolations = [];
  const titleDrift = [];
  for (const post of posts) {
    const missing = [];
    for (const key of ["sunoId", "lang", "translationKey", "sunoImageUrl", "duration"])
      if (!post[key]) missing.push(key);
    if (missing.length) metadataGaps.push({ path: post.path, missing });

    const invalid = post.genre.filter(
      (label) => label.length > 40 || /[:,;]/.test(label)
    );
    if (post.genre.length > 5 || invalid.length)
      genreViolations.push({ path: post.path, count: post.genre.length, invalid });

    const clip = clipsById.get(post.sunoId);
    if (clip && post.lang === "pt" && post.title && clip.title && post.title !== clip.title)
      titleDrift.push({ path: post.path, source: clip.title, blog: post.title });

    if (clip) {
      const expectedDuration = sourceDuration(clip);
      const actualDuration = post.duration ? Number(post.duration) : null;
      if (expectedDuration !== null && actualDuration !== null && expectedDuration !== actualDuration)
        metadataGaps.push({
          path: post.path,
          mismatch: { duration: { source: expectedDuration, blog: actualDuration } },
        });
    }
  }

  return {
    summary: {
      publicClips: clips.length,
      musicPosts: posts.length,
      mirroredIds: [...clipsById.keys()].filter((id) => postsById.has(id)).length,
      missingFromBlog: missingFromBlog.length,
      blogOnlyIds: blogOnlyIds.length,
      sameLanguageDuplicates: sameLanguageDuplicates.length,
      metadataGaps: metadataGaps.length,
      genreViolations: genreViolations.length,
      titleDrift: titleDrift.length,
    },
    missingFromBlog,
    blogOnlyIds,
    sameLanguageDuplicates,
    metadataGaps,
    genreViolations,
    titleDrift,
  };
}

function markdown(report) {
  const lines = ["# Suno catalog audit", "", "## Summary", ""];
  for (const [key, value] of Object.entries(report.summary)) lines.push(`- **${key}:** ${value}`);
  for (const section of [
    "missingFromBlog",
    "blogOnlyIds",
    "sameLanguageDuplicates",
    "metadataGaps",
    "genreViolations",
    "titleDrift",
  ]) {
    lines.push("", `## ${section}`, "");
    const rows = report[section];
    if (rows.length === 0) lines.push("None.");
    else for (const row of rows) lines.push(`- \`${JSON.stringify(row)}\``);
  }
  return `${lines.join("\n")}\n`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    usage();
    return;
  }
  const repoRoot = resolve(args.repo);
  const packageJson = JSON.parse(await readFile(join(repoRoot, "package.json"), "utf8"));
  if (packageJson.name !== "franklinbaldo-pico")
    throw new Error(`Unexpected repository package name: ${packageJson.name ?? "missing"}`);

  const [clips, posts] = await Promise.all([
    loadProfile(args.profileJson),
    loadPosts(repoRoot),
  ]);
  const report = audit(clips, posts);
  process.stdout.write(
    args.format === "json" ? `${JSON.stringify(report, null, 2)}\n` : markdown(report)
  );
}

main().catch((error) => {
  console.error(`audit-catalog: ${error.message}`);
  process.exitCode = 1;
});
