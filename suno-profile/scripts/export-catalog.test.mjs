import assert from "node:assert/strict";
import test from "node:test";
import { parseArgs, buildMarkdown } from "./export-catalog.mjs";

test("parseArgs: defaults handle and out, accepts overrides", () => {
  assert.deepEqual(parseArgs([]), { out: null, handle: "franklinbaldo" });
  assert.deepEqual(parseArgs(["--out", "x.md", "--handle", "someoneelse"]), {
    out: "x.md",
    handle: "someoneelse",
  });
});

test("parseArgs: rejects an unknown argument", () => {
  assert.throws(() => parseArgs(["--nope"]), /Unknown argument/);
});

const FIXTURE = {
  handle: "franklinbaldo",
  profile: {
    metadata: { display_name: "Franklin Baldo" },
    bio: { profile_description: "Songs about chess and Borges.", user_inputted_genres: ["folk", "ambient"] },
    social_links: { x_link: "https://x.com/franklinbaldo" },
    stats: { followers: 10 },
    pin_captions: [{ clip_id: "clip-1", caption: "A pinned caption." }],
    feed: {
      items: [
        {
          content_id: "pinned_songs_feed",
          content_item: {
            items: [{ content_item: { id: "clip-1", title: "Xadrez" } }],
          },
        },
      ],
    },
  },
  clipDetails: [
    {
      id: "clip-1",
      title: "Xadrez",
      duration: 200,
      tags: "trip-hop",
      caption: "Chess as ritual.",
      lyrics: "Em seu canto grave",
      play_count: 7,
    },
    {
      id: "clip-2",
      title: "Beatriz",
      duration: 120,
      tags: "trap-rap",
      caption: "",
      lyrics: "On the scorching February morning",
      play_count: 23,
    },
  ],
  playlists: [
    { id: "pl-1", name: "Aleph caipira", description: "Borges' El Aleph, caipira style.", is_public: true, tracks: ["A", "B"] },
  ],
};

test("buildMarkdown: includes profile, pinned songs, playlists, and every song", () => {
  const md = buildMarkdown(FIXTURE);
  assert.match(md, /# Suno catalog export: franklinbaldo/);
  assert.match(md, /Songs about chess and Borges\./);
  assert.match(md, /folk, ambient/);
  assert.match(md, /Xadrez.*clip-1.*pin caption: "A pinned caption\."/s);
  assert.match(md, /### Aleph caipira/);
  assert.match(md, /Borges' El Aleph, caipira style\./);
  assert.match(md, /Tracks: A, B/);
  assert.match(md, /### Beatriz/);
  assert.match(md, /### Xadrez/);
  assert.match(md, /On the scorching February morning/);
});

test("buildMarkdown: sorts songs by play_count descending", () => {
  const md = buildMarkdown(FIXTURE);
  const beatrizIndex = md.indexOf("### Beatriz");
  const xadrezIndex = md.indexOf("### Xadrez", md.indexOf("## Songs"));
  assert.ok(beatrizIndex < xadrezIndex, "higher play_count (Beatriz, 23) should come before Xadrez (7)");
});

test("buildMarkdown: an empty caption is shown explicitly, not left blank", () => {
  const md = buildMarkdown(FIXTURE);
  assert.match(md, /Caption: \(empty\)/);
});
