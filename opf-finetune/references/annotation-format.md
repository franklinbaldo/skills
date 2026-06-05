# Annotation format & label space

## The training JSONL

One JSON object per line. The trainer consumes the same schema as `opf eval`.

```json
{"text": "Record train_000 includes marker CS-TRN-000-NE5CXVRT and must be archived.", "label": [{"category": "custom_secret", "start": 33, "end": 52}], "info": {"id": "train_000", "split": "train"}}
```

Fields:

- `text` (string) — the raw text. Keep it as-is; do not pre-tokenize.
- `label` (list) — span annotations. Each is `{"category": str, "start": int, "end": int}`.
  The field may also be named `spans`; `label` is what the demo data uses. Prefer one
  name consistently across all files.
- `info` (object, optional) — free metadata (id, split, source proc. number). Ignored
  by training; useful for debugging and for tracing a span back to its document.

### Offset rules (the part that breaks)

- Offsets are **character** offsets into `text`, **not** token or byte offsets.
- `start` is **inclusive**, `end` is **exclusive** — i.e. `text[start:end]` is exactly
  the span surface. Verify by slicing: in the example above,
  `text[33:52] == "CS-TRN-000-NE5CXVRT"`.
- Count Python `str` characters. Accented PT-BR (`ção`, `é`, `À`) is multi-byte in
  UTF-8 but **single characters** in `str`. Counting bytes silently shifts every span
  after the first accent.
- No overlapping spans of the same scheme; the BIOES decoder assumes a single span per
  region. If two categories legitimately overlap, you need a different label or a
  separate model — don't fake it with overlaps.
- Spans should not include leading/trailing whitespace; trim before recording offsets.

Always run the validator before training:
```bash
python scripts/opf_annotate.py validate train.jsonl --label-space label_space.json
```

## The label space JSON

`--label-space-json` defines the *entire* output ontology. Internally each category is
expanded into `B-/I-/E-/S-` tags plus the shared background `O`, so N categories →
`1 + 4N` token classes.

```json
{
  "category_version": "legal_regions_v1",
  "span_class_names": ["O", "dispositivo", "resultado", "fundamentacao_chave", "ref_normativa"]
}
```

Rules:

- `span_class_names` is the preferred key.
- **`O` must be the first entry.**
- Category names are your own; keep them stable across versions (bump
  `category_version` when the set changes) so checkpoints and data stay legible.

### Replace vs. union

The label space you pass *replaces* OPF's native PII taxonomy. Two modes:

- **Replace** (only legal categories + `O`): the model forgets PII. Correct when you
  only want region tagging.
- **Union** (legal categories + the PII categories you still want): one model does
  both. To make union work you must **also include PII-annotated examples** in the
  training data — listing a category in the label space without examples teaches the
  model nothing about it and can degrade it. Native PII category names are:
  `account_number`, `private_address`, `private_email`, `private_person`,
  `private_phone`, `private_url`, `private_date`, `secret`.

## Sampling the corpus to annotate

You annotate a *sample*, not the whole corpus — so the sample has to represent the
distribution the model will face in production, or the metrics lie and the model
overfits whatever you happened to grab.

- **Stratify by sub-distribution; for legal text that axis is the court/tribunal.**
  Format, boilerplate, section cues (`Ante o exposto` vs. other closings), numbering
  conventions, and even OCR quality differ by tribunal. A sample drawn from one tribunal
  trains a tagger that overfits that tribunal's conventions. This is SKILL.md Warning 1
  one level finer: within PT-BR legal text, **each tribunal is its own sub-distribution**,
  and the sample must cover them.
- **Allocation: prefer coverage over raw proportionality.** A robustness-oriented span
  tagger needs to *see every format*, so default to **equal allocation per tribunal with
  a floor and a cap**, not proportional sampling (which drowns small tribunals and
  over-weights the biggest). Proportional matches production traffic but under-covers the
  rare formats that break models; pick coverage unless you have a reason not to.
- **Within a tribunal:** random with a **fixed seed**; if metadata allows, spread across
  decision date and decision type so you don't grab one period or one batch; **dedup**
  near-identical boilerplate so it doesn't dominate.
- **Record a sample manifest** (per-tribunal counts, seed, source archive item ids /
  versions, date ranges). This makes the sample reproducible and *expandable* — when you
  later add data for weak tribunals or weak classes (Warning 1 follow-up), you extend the
  manifest instead of resampling from scratch.

When there is **no consolidated dataset yet**, sample directly from the per-source
archives rather than waiting for consolidation — the GHA matrix pattern for "one archive
per source → sample → combine" is in `colab-and-drive.md`; ontology-design patterns and
worked examples are in `ontology-recipes.md`. The sampled pool is the *input to
annotation*; the annotated, reviewed subset becomes the gold committed to git.

## LLM-driven annotation (no human annotation team required)

By 2026 the right default is a **fully LLM-driven** annotation pipeline. You do not need
to hire annotators, and you do not need to hand-label the training set — a capable model
labels, a stronger or independent model verifies, and OPF (a *classifier*, not a
generator, at inference) is forgiving of residual noise in the training labels. Insisting
on manual annotation here would forfeit most of the scale that makes this approach worth
doing. So lean into the machines.

1. **Label.** Run a capable LLM (or NotebookLM) over the corpus, emitting spans —
   easiest is to have it mark spans with sentinels you convert to offsets with
   `scripts/opf_annotate.py from-spans`, so the model never counts characters. For
   PT-BR legal text, anchor cues are reliable: `É o relatório`, `Vistos`,
   `Ante o exposto`, `Posto isso`, `Julgo procedente/improcedente`, `D.S.G.`,
   article/inciso markers.
2. **Verify (model-checks-model).** Pass the labels to a **stronger** model as a judge
   to correct boundaries and catch category errors, and feed its systematic findings
   back into the labeling prompt and re-run. This weak-label → strong-verify loop is
   genuinely high-quality in 2026 and converges fast; it is the workhorse for the
   **training** split, where label noise is averaged out anyway.

### The one place model-checks-model is not enough: the eval

This is a measurement constraint, not a labor or trust issue, so it survives however
good the models get. If your evaluator's errors are **correlated** with your labeler's
errors, the evaluator can't see them. The deepest source of correlation is shared
weights reasoning over the same text *with the same framing*: a systematic error (a PT-BR
legal convention the model consistently misreads, a boundary it always gets wrong) then
lands in both train and test, the model learns it, is *rewarded* for reproducing it, and
the metric stays high while the model is quietly wrong. You can't grade your own homework
with the same pen, asking the same question.

The goal is therefore to **decorrelate the evaluators' errors from the labeler's**, on
the gold slice. Humanness and different model families are not required — independence is
a spectrum, and the cheap levers are free:

- **Diverse evaluator prompts (primary lever).** An ensemble of evaluators with
  *differentiated* system prompts — strict-boundary reviewer, category-disambiguation
  specialist, etc. — catches the largest error class: instruction underspecification
  (the labeler *could* get it right but wasn't told the convention). Disagreement among
  them flags the gold examples to fix. For most pipelines this is sufficient and needs
  no second model.
- **Differentiated task framings (stronger, still single-model).** Vary *what the model
  conditions on*, not just its tone: one evaluator re-labels from scratch blind; another
  *critiques* the existing label; another answers targeted yes/no boundary questions; and
  an **adversarial** one builds the strongest case that the label is *wrong*. Forcing the
  model to argue the opposite surfaces counter-evidence it won't volunteer
  (self-critique exceeds self-generation), which pierces some errors that mere
  persona-swapping can't.
- **Cross-family or owner spot-check (optional escalation).** A truly weight-baked blind
  spot — one the model is confident about and no prompt dislodges — survives all
  single-model checks. *If* you suspect that (e.g. a category the ensemble agrees on but
  the trained model still flunks in practice), escalate: adjudicate the tiny gold slice
  with a different model family, or spend the afternoon checking 25–50 examples yourself.
  This is a backstop for the residual, not the default.

Record how the gold was verified in the manifest (`test_verified_by`, see
`colab-and-drive.md`) so a high F1 is interpretable rather than a mirage. Train labels:
go fully automatic. Eval labels: keep the evaluators' errors decorrelated from the
labeler's.

### Executing it: spawn subagents (see the `llm-work-via-subagents` skill)

When an agent orchestrates the annotation, **spawn subagents — do not write a script that
calls an LLM API with a key.** The general principle, patterns, and the one exception live
in the `llm-work-via-subagents` skill; consult it. The span-specific mapping is:

- **Labeling → shard across parallel subagents**, one per batch of documents. Each returns
  sentinel-marked spans or `(match, category)` pairs; the orchestrator converts and
  validates with `scripts/opf_annotate.py from-spans`, so no subagent ever counts
  characters.
- **The evaluator ensemble → one subagent per role** (strict-boundary,
  category-disambiguation, blind-relabel, adversarial), spawned in parallel over the gold
  slice — the diverse framings above are just diverse subagent briefs.

Because OPF *classifies* rather than *generates* at inference, noisy automatic training
labels are enough for a usable v1 — the leverage is in spending your scarce verification
effort on the gold slice, not on the training bulk.

## Common annotation mistakes

- Byte offsets on accented text → everything after the first accent is shifted.
- Including the trailing period/colon/whitespace in the span.
- Annotating a huge region as one span (see Warning 2 in SKILL.md — anchor instead).
- Listing a category in the label space with zero training examples.
- Inconsistent `label` vs `spans` field naming across files.
- Train/val leakage (same document, or near-duplicate boilerplate, in both splits).
