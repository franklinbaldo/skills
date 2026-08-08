# Meme image generation routes

Use this reference when the problem is not only template choice but how the image should be produced.

The goal is to avoid equating `meme-image` with one API or one visual grammar.

## Route A — Memegen predefined templates

Best default for recognizable classic meme shorthand.

Strengths:
- large live catalog;
- URL-addressable output;
- no local rendering pipeline;
- template semantics are already culturally legible.

Weaknesses:
- salience bias can collapse selection onto the same handful of famous templates;
- third-party availability becomes part of publishing;
- template grammar constrains the joke.

Use the exploration protocol in `template-discovery.md` whenever selection is open-ended.

## Route B — Memegen custom background / overlay

Memegen supports `custom` backgrounds and image overlays. Use this when the joke needs meme typography/composition but a stock template is the wrong visual object.

This route expands the visual vocabulary without creating a second renderer. It is especially useful when the post already has an image, screenshot, diagram, generated illustration, or project-specific asset that can carry the joke.

Do not hotlink an arbitrary third-party image just because the API accepts a URL. Prefer an image the publishing context already has rights to use.

## Route C — Self-hosted render

When durability, typography, or privacy matters, render once and commit the asset instead of depending on a remote rendering URL.

A thin local renderer may use an already-available image primitive such as SVG/HTML + rasterization, Pillow, ImageMagick, or Sharp. This is a rendering route, not a second meme-selection framework: selection, exploration, text constraints, alt text, and evals remain governed by `meme-image`.

Prefer this route when:
- the post must not depend on a third-party image service;
- a custom background is already in the repository;
- exact fonts/layout matter;
- the generated output should be immutable and content-addressable.

Do not add a renderer dependency merely to reproduce what Memegen already does adequately.

## Route D — Original generated visual

When the humor depends on a scene that no established template expresses well, use an available image-generation model to create an original visual and then add concise meme text only if it improves the result.

This route is for original scenes, not imitation of a living artist or a copyrighted character/style request that should be avoided. Preserve provenance: record that the visual was generated rather than sourced from a template catalog.

The evaluation question changes here. Familiarity of the template is no longer a benefit, so judge:
- immediate readability;
- visual-comedic timing;
- whether the image communicates the intended relation before the caption explains it;
- fit with the surrounding post.

## Route E — Other template services

Other services may expose a materially different template catalog or rendering affordances. Treat them as optional adapters, not canonical dependencies.

For example, Imgflip exposes `caption_image` and a large community template ecosystem, but API generation requires account credentials and generated images are service-hosted. Use only when credentials and the service boundary are acceptable.

Never put credentials in a skill, repository, URL, fixture, or benchmark result.

## Route selection

Choose a route by the missing capability:

- stock recognizable grammar needed → predefined template;
- stock grammar but project-specific image needed → custom background/overlay;
- same semantics but durable/local asset needed → self-hosted render;
- no stock grammar fits the joke → original generated visual;
- another catalog materially improves the candidate pool → optional external service.

Do not add a new backend solely for novelty. Backend diversity is useful when it expands the visual/comedic hypothesis space or improves publishing properties.
