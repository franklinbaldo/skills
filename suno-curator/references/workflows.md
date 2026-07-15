# Curatorial workflows

Choose one workflow per session. This separation prevents a mechanical audit
from quietly turning into editorial rewriting or destructive cleanup.

## A. Sync run

### Inputs

- current public profile snapshot;
- current blog corpus;
- current schema and repository guidance;
- newest committed PT/EN music pair.

### Procedure

1. Run the bundled audit and save the output when it will support the PR.
2. Review every `missingFromBlog` item. Confirm it is public and not represented
   under a different `sunoId` due to a source-side replacement.
3. Inspect the generator's output shape without executing it. If it creates
   version directories, do not run it.
4. Create or generate only the missing flat stubs using current corpus shape.
5. Copy only source-backed fields: title, source lyrics, date, image URL,
   duration, style prompt, and clip ID.
6. Curate 1–3 genres from RFC 0011; do not derive a long prompt-shaped list.
7. Load `franklin-blog` and draft composer notes. When the song's context is
   unknown, leave the notes explicitly incomplete instead of inventing a
   creation story.
8. Create/update the EN companion only when requested or required by the current
   repository policy. Keep the semantic pair aligned.
9. Re-run the audit and validation commands.
10. Report source count, created count, skipped count, remaining gaps, and title
    drift separately.

### Stop conditions

Stop before writing when:

- the checkout is not the expected blog repository;
- the source clip is private or absent;
- lyrics cannot be verified;
- file layout is ambiguous;
- unrelated working-tree changes would be overwritten.

## B. Metadata pass

### Procedure

1. Run the audit.
2. Build a mechanical worklist from missing fields, same-language duplicates,
   and RFC 0011 violations.
3. Verify every replacement value from API data or an existing translation
   pair.
4. Fix only metadata. Do not change lyrics or composer notes.
5. For blog-only IDs, private clips, or title drift, add findings to the report;
   do not delete or overwrite automatically.
6. Re-run the audit. The before/after delta is the main result.

## C. Catalog report

### Evidence table

For each candidate, gather:

| Dimension | Evidence |
| --- | --- |
| Source status | public/private/absent, creation date, playlist membership |
| Mirror status | PT/EN coverage, metadata completeness, title drift |
| Quality signal | Hrönir rating, sample count, review themes |
| Exposure signal | featured status, series position, catalog visibility |
| Confidence | high/medium/low and why |

### Judgment rules

- Never equate a low-sample rank with low quality.
- Prefer “strong but under-evaluated” over “hidden gem” unless the evidence
  genuinely supports the claim.
- Cap highlights at a useful decision set, normally 3–5.
- Explain exclusions when an obvious popular or high-ranked song is not chosen.
- Check series continuity concretely — e.g. the _Moving Window_ series (12+
  numbered parts): verify ordering and gaps, and whether Suno-side playlists
  still reflect the catalog's actual grouping.
- Separate recommendations into:
  - blog changes the agent may implement;
  - Suno-side actions Franklin must decide and perform.

### Suggested report structure

```markdown
# Catalog report — <date>

## Scope and confidence
## Catalog/mirror health
## Highlights (3–5)
## Strong but under-evaluated
## Featured but weak or stale
## Series and playlist continuity
## Blog actions
## Suno-side recommendations
## Uncertainty and next evidence needed
```

## D. Deep dive

1. Identify the canonical PT file and any EN companion by `translationKey` and
   `sunoId`.
2. Read both files fully and inspect relevant Hrönir evidence.
3. Compare source lyrics and metadata without normalizing them.
4. Diagnose separately:
   - song/lyric limitations that cannot be edited in the blog;
   - metadata defects;
   - weak or generic composer notes;
   - PT/EN semantic drift;
   - missing links to related works or series.
5. Load `franklin-blog` and revise the authorial framing, preserving uncertainty
   and avoiding promotional boilerplate.
6. Validate both languages in the same commit when the change is semantic.

## Validation matrix

| Change | Minimum checks |
| --- | --- |
| Read-only report | audit command; Hrönir ranking command if used |
| Frontmatter only | audit; prettier; `hronir:doctor`; targeted tests if available |
| New/changed post body | audit; prettier; doctor; tests; build |
| Generator/script change | offline fixture test; repository test suite; build if generated content affects it |

Never report an unchecked command as successful.

## PR summary template

```markdown
## What changed

- ...

## Evidence

- Public clips: N
- Mirrored IDs before/after: N → N
- Remaining gaps: ...

## Validation

- `...` ✅/❌

## Not changed

- No Suno-side action was performed.
- Lyrics were not invented or normalized.

## Recommendations for Franklin

- ...
```
