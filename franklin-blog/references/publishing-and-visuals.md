# Publishing, visuals, and continuity

Load this reference after the post's voice and overall form have substantially settled, or earlier only when the task is specifically about blog formatting, visuals, links, frontmatter, or continuity with recent posts.

## Structural rules

- No `# H1` in the body; Astro renders the title from frontmatter.
- No `---` horizontal rules in body prose.
- Use `## H2` sparingly. Short essays often need no headers; longer pieces use evocative, content-specific headings rather than “Introduction” / “Conclusion”.
- Paragraph length may vary. Short/dry sentence rhythm matters more than enforcing a paragraph-size formula.
- Closing line: short, slightly cryptic/deadpan when the post wants one; avoid repeating recent closing gestures.
- Author convention: no Borges in the body as a casual reference; bibliographic use in further-reading sections is fine.

## Visual rhythm

For non-confessional long-form register, a visual/rest beat roughly every 400–500 words is a useful heuristic, not a quota. Confessional or emotionally weighted passages may deliberately go longer without one.

Possible rests include:

- image memes;
- text-meme blocks;
- Mermaid diagrams;
- inline SVG;
- maps;
- footnotes;
- pull quotes;
- section headings.

The passage decides. Do not add a visual simply because a counter says one is due.

## Memes and voice

Use companion skills for mechanics:

- `meme-image` for recognizable image-meme templates;
- `text-meme-injection` for inline/block text memes.

Voice constraint:

- text memes lean toward the didactic/expository pole;
- image memes are affect-heavy and therefore retreat faster as a passage becomes confessional;
- in emotionally exposed prose, the dry sentence often already supplies the antimelodrama. An image meme can cheapen it.

Do not reuse the same meme template repeatedly in a post just because it worked once.

## Other visual forms

### Maps

For real geography, use an appropriate embeddable map. Keep the map functional rather than decorative.

### Mermaid

Use for compact conceptual structures. Prefer simple flow/graph/mindmap/timeline forms; avoid diagrams whose complexity exceeds the explanatory payoff.

### Inline SVG

Use for non-diagrammatic illustrations when SVG is the right medium. Respect the site's theme variables instead of hardcoding presentation that fights dark/light mode.

### Pull quotes

Exceptional. Usually zero, occasionally one. Do not manufacture quote-worthy sentences just to populate the layout.

## Footnotes

Use sparingly. A footnote should reward the reader rather than becoming a second essay under the essay.

Markdown syntax:

```markdown
Text.[^note]

[^note]: Footnote text.
```

## Links

Link works, technical terms, and lesser-known names on first useful mention when the reader benefits. Do not link to perform familiarity.

Prefer primary or authoritative sources over aggregators. For classics/philosophy, established scholarly repositories are preferable to generic summaries when available.

## Further reading

Posts over roughly 1,200 words normally benefit from:

```markdown
## For further reading

- **{Author}, *{Title}*** — one sentence on why this matters here.
```

Aim for a small curated set rather than bibliography dumping. Mix source types when useful. Self-links are appropriate when they are genuinely the next thing the reader would want; avoid auto-promotion loops.

## Frontmatter

Typical shape:

```yaml
---
title: "..."
description: "..."
date: "YYYY-MM-DD"
lang: en  # or pt
translationKey: ...
tags: [...]
---
```

Write `description` late, after the post exists. Keep it evocative and concise rather than summarizing the conclusion.

## File naming

Use the blog's established content path and slug conventions. Check recent files before inventing a new convention, especially for Portuguese posts.

## Bilingualism

Voice rules remain the same across English and Portuguese; concrete meme vocabulary differs.

- Default to the language of the conversation when the requested language is otherwise ambiguous.
- Preserve Portuguese words in English when translation would erase the useful concept, with a brief gloss only if needed.
- Preserve technical Greek/Latin transliteration in Portuguese when it carries technical weight.

## Continuity across posts

For a follow-up or a post that belongs to an active sequence, inspect relevant prior posts before final polish. Check recent work for accidental repetition of:

- closing-line gestures;
- image-meme templates;
- inline meme forms;
- self-link patterns;
- recurring structural tricks.

Two recurrences can be a motif. Three in a row can become an accidental tic. Vary when the repetition stops doing work.

This continuity pass happens after the draft has a voice and shape; it should not delay the first draft.