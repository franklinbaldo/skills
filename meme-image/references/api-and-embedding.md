# memegen.link API and embedding

Load this reference after deciding that an image meme is appropriate and you need URL construction, encoding, testing, or embedding details.

## URL shape

The URL is the meme specification:

```text
https://api.memegen.link/images/{template_id}/{line1}/{line2}/.../{lineN}.{ext}
```

Common extensions are `png`, `jpg`, `gif`, and `webp` where supported.

## Path encoding

In meme text path segments:

- space → `_` or `-`
- literal underscore → `__`
- literal dash → `--`
- newline → `~n`
- question mark → `~q`
- apostrophe → `~s`
- quotation mark → `~d`
- percent → `~p`
- hash → `~h`

Prefer short, plain text when possible; dense punctuation and long lines degrade layout.

## Useful query parameters

Examples include:

- `width=600`
- `height=600`
- `font=impact`, `font=titilliumweb`, `font=notosans`
- `layout=top`
- `style=<name>` where a template exposes styles

For blog use, explicitly constraining width is usually preferable to the template's native size.

## Examples

```text
https://api.memegen.link/images/drake/Cogito_ergo_sum/Loxias_says_cross_the_Halys.png?width=500
```

```text
https://api.memegen.link/images/gb/Know_thyself/Nothing_in_excess/E/If_you_want_to_talk_to_the_Oracle_go_to_Delphi.png?width=600
```

## Markdown embedding

Plain Markdown is valid:

```markdown
![Descriptive alt text](https://api.memegen.link/images/...)
```

For essay/blog presentation, a figure can carry caption, alt text, and lazy loading:

```html
<figure class="meme">
  <img
    src="https://api.memegen.link/images/..."
    alt="Describe the meme's visual and text content"
    loading="lazy"
  />
  <figcaption>Optional caption.</figcaption>
</figure>
```

Always provide useful `alt` text. For third-party images in long pages, prefer lazy loading.

## Testing

For production-facing posts, verify the generated URL rather than assuming a guessed template ID or encoding is valid. A quick HTTP request should return an actual image, not an error/placeholder.

## Service boundary

memegen.link is a third-party dependency. Embedding its URLs directly is acceptable for low-stakes personal-blog use when that dependency is acceptable. For high-stakes or durability-sensitive publishing, generate once and self-host the resulting asset.