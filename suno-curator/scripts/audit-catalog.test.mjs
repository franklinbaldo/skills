import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import test from "node:test";

const execFileAsync = promisify(execFile);
const here = dirname(fileURLToPath(import.meta.url));
const script = join(here, "audit-catalog.mjs");

test("audits an offline PT/EN mirror without treating the pair as duplicate", async () => {
  const root = await mkdtemp(join(tmpdir(), "suno-curator-"));
  const blog = join(root, "src", "content", "blog");
  await mkdir(blog, { recursive: true });
  await writeFile(
    join(root, "package.json"),
    JSON.stringify({ name: "franklinbaldo-pico" })
  );

  const common = `type: Music Post
postType: music
sunoId: clip-1
sunoImageUrl: "https://example.com/cover.jpg"
duration: 120
translationKey: music-one
genre:
  - indie`;
  await writeFile(
    join(blog, "one.mdx"),
    `---\n${common}\ntitle: One\nlang: pt\n---\n\n## Letra\n`
  );
  await writeFile(
    join(blog, "one-en.mdx"),
    `---\n${common}\ntitle: One\nlang: en\n---\n\n## Lyrics\n`
  );

  const profile = join(root, "profile.json");
  await writeFile(
    profile,
    JSON.stringify({
      num_total_clips: 3,
      clips: [
        {
          id: "clip-1",
          title: "One",
          is_public: true,
          image_url: "https://example.com/cover.jpg",
          metadata: { duration: 120 },
        },
        { id: "clip-2", title: "Two", is_public: true, metadata: {} },
        { id: "clip-private", title: "Private", is_public: false, metadata: {} },
      ],
    })
  );

  const { stdout } = await execFileAsync(process.execPath, [
    script,
    "--repo",
    root,
    "--profile-json",
    profile,
    "--format",
    "json",
  ]);
  const report = JSON.parse(stdout);
  assert.equal(report.summary.publicClips, 2);
  assert.equal(report.summary.musicPosts, 2);
  assert.equal(report.summary.mirroredIds, 1);
  assert.equal(report.summary.sameLanguageDuplicates, 0);
  assert.deepEqual(report.missingFromBlog, [{ id: "clip-2", title: "Two" }]);
});

test("indexes tracks[] renditions and normalizes title whitespace", async () => {
  const root = await mkdtemp(join(tmpdir(), "suno-curator-"));
  const blog = join(root, "src", "content", "blog");
  await mkdir(blog, { recursive: true });
  await writeFile(
    join(root, "package.json"),
    JSON.stringify({ name: "franklinbaldo-pico" })
  );

  await writeFile(
    join(blog, "borges.mdx"),
    `---
type: Music Post
postType: music
title: Borges e eu
sunoId: clip-main
sunoImageUrl: "https://example.com/borges.jpg"
duration: 177
lang: pt
translationKey: music-borges
genre:
  - spoken word
tracks:
  - label: "greentext version"
    sunoId: clip-track-1
    sunoStyle: |-
      block scalar that must not leak keys
      sunoId: not-a-real-id
  - label: "glitch rap version"
    genre:
      - glitch
      - hip-hop
    sunoId: clip-track-2
---

## Letra
`
  );
  await writeFile(
    join(blog, "tempo.mdx"),
    `---
type: Music Post
postType: music
title: O Tempo
sunoId: clip-tempo
sunoImageUrl: "https://example.com/tempo.jpg"
duration: 90
lang: pt
translationKey: music-tempo
genre:
  - ambient
---

## Letra
`
  );

  const profile = join(root, "profile.json");
  await writeFile(
    profile,
    JSON.stringify({
      num_total_clips: 4,
      clips: [
        {
          id: "clip-main",
          title: "Borges e eu ",
          is_public: true,
          metadata: { duration: 177 },
        },
        { id: "clip-track-1", title: "greentext", is_public: true, metadata: {} },
        { id: "clip-track-2", title: "glitch", is_public: true, metadata: {} },
        {
          id: "clip-tempo",
          title: "O  Tempo",
          is_public: true,
          metadata: { duration: 90 },
        },
      ],
    })
  );

  const { stdout } = await execFileAsync(process.execPath, [
    script,
    "--repo",
    root,
    "--profile-json",
    profile,
    "--format",
    "json",
  ]);
  const report = JSON.parse(stdout);
  // Track renditions are mirrored by the post that carries them, never
  // reported as missing, and never recreated by a sync.
  assert.equal(report.summary.publicClips, 4);
  assert.equal(report.summary.mirroredIds, 4);
  assert.deepEqual(report.missingFromBlog, []);
  assert.equal(report.summary.sameLanguageDuplicates, 0);
  // Trailing whitespace from Suno is noise; internal differences still drift.
  assert.equal(report.titleDrift.length, 1);
  assert.equal(report.titleDrift[0].path, "src/content/blog/tempo.mdx");
  assert.equal(report.titleDrift[0].source, "O  Tempo");
});

test("indexes a track's sunoId regardless of key order within the item", async () => {
  const root = await mkdtemp(join(tmpdir(), "suno-curator-"));
  const blog = join(root, "src", "content", "blog");
  await mkdir(blog, { recursive: true });
  await writeFile(
    join(root, "package.json"),
    JSON.stringify({ name: "franklinbaldo-pico" })
  );

  // genre's own nested list ("- indie") uses the same "- " marker as a new
  // tracks[] item; a parser that treats every dash as a potential item
  // boundary can lose track of the real item indent once it walks past a
  // sub-list, and then fail to recognize sunoId lines that follow it.
  await writeFile(
    join(blog, "reordered.mdx"),
    `---
type: Music Post
postType: music
title: Primary
lang: pt
sunoId: clip-primary
sunoImageUrl: "https://example.com/cover.jpg"
duration: 120
translationKey: music-reordered
genre:
  - indie
tracks:
  - label: "Alt version"
    genre:
      - indie
      - spoken word
    sunoId: clip-track
    duration: 90
---

## Letra
`
  );

  const profile = join(root, "profile.json");
  await writeFile(
    profile,
    JSON.stringify({
      num_total_clips: 2,
      clips: [
        {
          id: "clip-primary",
          title: "Primary",
          is_public: true,
          metadata: { duration: 120 },
        },
        {
          id: "clip-track",
          title: "Alt version",
          is_public: true,
          metadata: { duration: 90 },
        },
      ],
    })
  );

  const { stdout } = await execFileAsync(process.execPath, [
    script,
    "--repo",
    root,
    "--profile-json",
    profile,
    "--format",
    "json",
  ]);
  const report = JSON.parse(stdout);
  assert.equal(report.summary.mirroredIds, 2);
  assert.deepEqual(report.missingFromBlog, []);
});
