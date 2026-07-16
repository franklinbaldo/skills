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

test("does not flag a clip already aggregated via tracks[] as missing", async () => {
  const root = await mkdtemp(join(tmpdir(), "suno-curator-"));
  const blog = join(root, "src", "content", "blog");
  await mkdir(blog, { recursive: true });
  await writeFile(
    join(root, "package.json"),
    JSON.stringify({ name: "franklinbaldo-pico" })
  );

  await writeFile(
    join(blog, "aggregate.mdx"),
    `---
type: Music Post
postType: music
title: Primary
lang: pt
sunoId: clip-primary
sunoImageUrl: "https://example.com/cover.jpg"
duration: 120
translationKey: music-aggregate
genre:
  - indie
tracks:
  - label: "Alt version"
    sunoId: clip-track
    duration: 90
    genre:
      - indie
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

test("treats source title whitespace as noise, not real title drift", async () => {
  const root = await mkdtemp(join(tmpdir(), "suno-curator-"));
  const blog = join(root, "src", "content", "blog");
  await mkdir(blog, { recursive: true });
  await writeFile(
    join(root, "package.json"),
    JSON.stringify({ name: "franklinbaldo-pico" })
  );

  await writeFile(
    join(blog, "whitespace.mdx"),
    `---
type: Music Post
postType: music
title: Portas Infinitas
lang: pt
sunoId: clip-1
sunoImageUrl: "https://example.com/cover.jpg"
duration: 120
translationKey: music-whitespace
genre:
  - indie
---

## Letra
`
  );

  const profile = join(root, "profile.json");
  await writeFile(
    profile,
    JSON.stringify({
      num_total_clips: 1,
      clips: [
        {
          id: "clip-1",
          title: "Portas Infinitas ",
          is_public: true,
          metadata: { duration: 120 },
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
  assert.deepEqual(report.titleDrift, []);
});
