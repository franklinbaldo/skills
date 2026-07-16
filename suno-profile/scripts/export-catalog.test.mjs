import assert from "node:assert/strict";
import test from "node:test";
import { parseArgs, buildMarkdown } from "./export-catalog.mjs";

test("parseArgs: defaults handle, out, includePrivate, accepts overrides", () => {
  assert.deepEqual(parseArgs([]), { out: null, handle: "franklinbaldo", includePrivate: false });
  assert.deepEqual(parseArgs(["--out", "x.md", "--handle", "someoneelse"]), {
    out: "x.md",
    handle: "someoneelse",
    includePrivate: false,
  });
  assert.equal(parseArgs(["--include-private"]).includePrivate, true);
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
      is_public: true,
    },
    {
      id: "clip-2",
      title: "Beatriz",
      duration: 120,
      tags: "trap-rap",
      caption: "",
      lyrics: "On the scorching February morning",
      play_count: 23,
      is_public: false,
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
  assert.match(md, /### Beatriz \(private\/unpublished\)/);
  assert.match(md, /### Xadrez\n/);
  assert.match(md, /On the scorching February morning/);
});

test("buildMarkdown: labels a private/unpublished clip explicitly, doesn't label a public one", () => {
  const md = buildMarkdown(FIXTURE);
  assert.match(md, /### Xadrez\n/); // public — no suffix
  assert.match(md, /### Beatriz \(private\/unpublished\)\n/);
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

test("buildMarkdown: lyrics containing a literal ``` don't break the fence for later songs", () => {
  const fixture = {
    ...FIXTURE,
    clipDetails: [
      {
        id: "clip-1",
        title: "Contains A Fence",
        duration: 100,
        tags: "",
        caption: "",
        lyrics: "before\n```\nsome pasted code\n```\nafter",
        play_count: 5,
      },
      {
        id: "clip-2",
        title: "Comes After",
        duration: 100,
        tags: "",
        caption: "",
        lyrics: "ordinary lyrics",
        play_count: 1,
      },
    ],
  };
  const md = buildMarkdown(fixture);
  // The fence around the tricky lyrics must be longer than any backtick
  // run inside them (4 backticks beats the embedded 3), so it doesn't
  // close early.
  assert.match(md, /````\nbefore\n```\nsome pasted code\n```\nafter\n````/);
  // "Comes After" must still render as its own heading, not get swallowed
  // into the unterminated block a naive 3-backtick fence would produce.
  assert.match(md, /### Comes After/);
});

test("buildMarkdown: a pinned feed item with no content_item is skipped, not a crash", () => {
  const fixture = {
    ...FIXTURE,
    profile: {
      ...FIXTURE.profile,
      feed: {
        items: [
          {
            content_id: "pinned_songs_feed",
            content_item: {
              items: [{ content_item: null }, { content_item: { id: "clip-1", title: "Xadrez" } }],
            },
          },
        ],
      },
    },
  };
  assert.doesNotThrow(() => buildMarkdown(fixture));
  const md = buildMarkdown(fixture);
  assert.match(md, /Xadrez/);
});
