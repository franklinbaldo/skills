---
name: opf-finetune
description: >-
  Fine-tune the OpenAI Privacy Filter (OPF, openai/privacy-filter) — a small
  bidirectional token-classifier derived from gpt-oss — to detect arbitrary span
  categories beyond its native PII labels. Use this whenever the goal is to tag,
  label, segment, or extract REGIONS / SPANS of text with a trained model rather
  than with prompting or regex: marking parts of legal documents (dispositivo,
  ementa, relatório, fundamentação, artigo, inciso), structural tagging of
  statutes, field extraction from editais/PNCP, or any custom token-classification
  ontology. Trigger on "fine-tune OPF", "treinar o privacy filter", "span tagger",
  "token classification for legal text", "marcar regiões", "extend OPF to new
  categories", "custom label space", or when working on span/region tagging inside
  CausaGanha, Leizilla, or Baliza — even if OPF is not named explicitly. Do NOT use
  for prompt-based extraction with a chat LLM, for regex pattern matching, or for
  OPF's out-of-the-box PII redaction (that needs no fine-tune).
compatibility: >-
  Requires Python and the openai/privacy-filter (OPF) training runtime. Data prep
  is CPU-capable, but practical full fine-tuning requires a CUDA GPU; the documented
  Colab/Drive path additionally requires network access and Google authentication.
---

# Fine-tuning OPF for custom span domains

## What OPF is, and why it is the right base here

OpenAI Privacy Filter (`openai/privacy-filter`, Apache 2.0) is a **bidirectional
token-classification model with span decoding**. It started as an autoregressive
gpt-oss-style checkpoint, then its LM head was swapped for a token-classification
head and it was post-trained with a supervised token-level loss. So instead of
generating text, it labels every token in **one forward pass** and decodes coherent
spans with a constrained Viterbi pass over **BIOES** tags (Begin, Inside, Outside,
End, Single).

Properties that matter for legal-text span tagging:

- **Tiny and local-friendly.** 1.5B total / **50M active** params (MoE, top-4 of 128
  experts), `d_model=640`. Trains and runs on modest hardware, CPU-viable, no API.
- **Long context, no chunking.** 128k-token window — a whole acórdão fits.
- **Strong language prior.** It is context-aware: it can tell a *dispositivo* from a
  *relatório* by surrounding language, not just keywords.
- **Data-efficient fine-tune.** OpenAI reports ~10% of a training split already
  saturating their benchmark; a few thousand annotated examples typically move a new
  category several F1 points. You do not need a huge corpus to start.
- **Permissive license.** Apache 2.0, commercial use fine.

Conceptually this is the "small specialized model" path (the SLM side of the
BERT-LeNER-vs-SLM question) — but pre-trained, data-efficient, and shipped with a
fine-tuning CLI. For tagging *regions* of Brazilian legal text it is a strong default;
for *generative* extraction (writing a summary of the dispositivo) it is the wrong
tool — use a chat LLM for that.

## Read these two warnings before designing anything

These are load-bearing. They change the label design and the annotation budget.

### 1. OPF is English-primary. Your corpus is PT-BR.

The model card states performance drops on non-English text and non-Latin scripts.
The gpt-oss base carries *some* multilingual capacity, but **Portuguese legal text is
out of distribution**. Consequences:

- Treat PT-BR validation as **mandatory, not optional**. Never trust a number from an
  English-shaped eval.
- Budget **more annotated PT-BR examples** than the "few thousand" English figure
  suggests, especially for subtle, context-dependent categories.
- Expect boundary noise on heavily formatted text (numbered articles, citation
  blocks, "fls.", abbreviations). Plan eval to measure boundary error, not just
  presence (see `references/training-and-eval.md`).

This is the single biggest risk of the project. Lead with it; do not bury it.

### 2. Banded attention + BIOES favors short, contiguous spans — not giant regions.

OPF uses **banded attention** (band 128, effective window ~257 tokens) and decodes
BIOES spans with Viterbi. This is excellent for compact spans and **fragile for
labeling an entire multi-thousand-token region** token-by-token (e.g. "the whole
relatório"). A 4,000-token region asked of a 257-token attention window will tend to
fragment or drift at the boundaries.

**Design around it: tag short anchors, reconstruct regions as a post-step.** There are
two anchor schemes — pick per region shape:

- **Single-anchor** (for regions that *tile* the document — each ends where the next
  begins). Tag only the *opening cue* — `É o relatório`, `Ante o exposto`, `Vistos` — as a
  short span; reconstruct the region in post as *open → next opening / end-of-document*.
- **Start/end pair** (for *discrete, non-tiling* regions — gaps or other material between
  them — and/or regions with a reliable closing cue). Tag a `_inicio` span and a `_fim`
  span as **two separate short-span categories**; the region is everything between a
  matched pair. This is the only way to express a long region's two ends in OPF's
  vocabulary: BIOES `B`/`E` mark the begin/end of *one contiguous span*, not "opens here,
  closes 3,000 tokens later". Use it for votos in an acórdão (discrete, strong closer
  "É como voto", last one has no "next anchor"), transcription blocks, statute articles.
  Pairing is post-processing: nearest-forward, sequential (no nesting), a missed `_fim`
  closes at the next `_inicio`/EOD, an unmatched marker is a **data-quality signal**.
- Reserve dense token-level labeling for genuinely short targets (an outcome verb, a
  party name, a statute reference, a date, a value).

The model finds the seams (short anchors); your code fills/pairs the regions. Neither
scheme asks the model to span a long region.

If a task seems to demand dense labeling of long regions with no anchors, stop and
reconsider the ontology before spending annotation effort.

## End-to-end workflow

The detail lives in the reference files; this is the spine.

1. **Design the ontology** → a custom label space. List `O` first, then your span
   categories; choose single-anchor vs. start/end-pair per category (Warning 2); decide
   *replace vs. union* (below) and *what to activate* (below).
   See `references/ontology-recipes.md` for the ontology-design patterns and worked
   examples, and `references/annotation-format.md` for the label-space JSON shape.

2. **Annotate → JSONL.** One record per line:
   `{"text": ..., "label": [{"category": ..., "start": <char>, "end": <char>}], "info": {...}}`.
   Offsets are **character** offsets, `start` inclusive, `end` exclusive (Python
   slicing). This is where most bugs live — validate with the bundled helper:

   ```bash
   uv run scripts/opf_annotate.py validate train.jsonl
   ```

   Annotate fully LLM-driven (a capable model labels, evaluators verify — no human
   annotation team needed); keep the eval gold slice checked by an ensemble of
   *differently-prompted / differently-framed* evaluators so their errors decorrelate
   from the labeler's (escalate to a different family or owner spot-check only for
   suspected weight-level blind spots). When an agent runs this, **spawn subagents**
   (one per labeling batch / per evaluator role) rather than scripting an API call — see
   the `llm-work-via-subagents` skill. Details in `references/annotation-format.md`.

3. **Train.** Hold out a real validation split.

   ```bash
   opf train train.jsonl \
     --validation-dataset val.jsonl \
     --label-space-json label_space.json \
     --output-dir ./ckpt_legal_v1
   ```

   Confirm exact flags with `opf train --help`; OpenAI ships runnable demo harnesses
   in `examples/scripts/finetuning/` worth copying. Output dir gets `config.json`,
   `model.safetensors`, `finetune_summary.json`, `USAGE.txt`.
   Full setup, hardware notes, and operating-point tuning: `references/training-and-eval.md`.

4. **Evaluate in-domain (PT-BR), tune the operating point.** `opf eval` on a held-out
   PT-BR set; span-level F1 with attention to boundaries. For legal use, false
   positives are usually costlier than misses — bias the Viterbi operating point
   toward precision. See `references/training-and-eval.md`.

5. **Infer / integrate.** `opf redact` for CLI, or load with transformers
   (`pipeline("token-classification", aggregation_strategy="simple")`) and consume the
   spans in your pipeline. Reconstruct long regions from anchors here.

## Where the work runs: prep vs. training, and Drive

OPF's base model is ~2.8 GB and a full fine-tune wants a GPU, while Colab runtimes are
ephemeral (the base re-downloads and checkpoints vanish on every reset). Organize around
that: **split data-prep and training into two notebooks** joined by a frozen artifact set
(`train/val/test.jsonl` + `label_space.json` + `manifest.json`), and **use Drive as the
persistence layer** — base model stored once, each run's checkpoint + metrics saved
immediately. Prep is CPU/iterative and portable (local, CPU Colab, or CI prepare-only +
IA upload); only training needs the GPU notebook. Concrete Drive tree, restore-or-fetch
caching, the manifest schema, and the Colab `uv`/`sys.executable`/`n-ctx` gotchas are in
`references/colab-and-drive.md`. Read it before wiring up any Colab run.

Prep itself starts with **sampling**: annotate a *stratified sample across all sources*
(equal-per-source with floor/cap, seeded), not whatever corpus is handy — each source is a
sub-distribution (for legal text, each tribunal; for any corpus, each publisher/format/era)
and a lopsided sample overfits one format. When there's no consolidated dataset yet, sample
directly from the per-source archives via a GHA matrix-per-source → combine job (see
`references/colab-and-drive.md` and `references/ontology-recipes.md`).

## Replace vs. union: a decision you make once

`--label-space-json` *defines the whole label space*. If you list only your legal
categories + `O`, the model **forgets** its native PII labels (catastrophic
forgetting — fine if you only want legal regions). If you also want PII (e.g. to
anonymize litigants — relevant given the CPF-anonymization concerns), **union** the
PII categories into the same `span_class_names` and include PII-annotated examples in
the training data, so one model does both legal-region tagging and party redaction.
Decide before annotating, because it sets what you annotate.

## Ontology design: definitions are durable, volume is incremental

The label space is the expensive, durable part; data is incremental. Two principles:

- **Spend the upfront effort on crisp category *definitions* (cues + boundary rules), not
  on coverage.** Adding examples later is cheap (a reviewable diff); *redefining* a
  category forces re-annotating everything already labeled. Lock the definitions and
  volume becomes just-add-examples.
- **Define every category now, but gate *activation* in the trained label space.** A
  category with very few examples isn't free: in a small classifier it can *degrade* the
  dense categories (label competition, diluted Viterbi transitions, noisy gradients). So a
  category can be *defined-but-staged* (annotated when seen, not in the trained label
  space) until it crosses an example floor (~25 spans), then *activated*. The manifest
  records `active` vs `staged`. If instead you choose to activate everything (a valid
  call when you want maximal coverage and accept the risk), make it **observable and
  reversible**: report per-category F1 *with support*, and keep the active set as a
  one-line config so dropping a category that drags down the dense ones is a retrain, not
  a re-annotation.

**Avoid over-labeling.** For an outcome/operative category, tag the **one operative
instance**, not every occurrence: exactly one operative `dispositivo_abertura`, and
`resultado` only inside the dispositivo (or an explicit mérito-chapter scope) — never on
reasoning verbs, intermediate rulings, transition cues like "Decido", or outcomes quoted
from precedent. Multiple conflicting spans per document defeat extraction. This is the
single error the *category-disambiguation* evaluator in the ensemble exists to catch.

- **`O` must be the first entry** in `span_class_names`.
- **Character offsets, end-exclusive.** Misaligned offsets (off-by-one, counting
  bytes not chars on accented PT-BR text, trailing whitespace inside the span) are the
  #1 silent failure. Always run the validator.
- **UTF-8 / accents.** Count Python `str` characters, not bytes. `len("ção") == 3`.
- **Validation split is not optional**, and it must be PT-BR and in-domain.
- **Don't dense-label long regions** — anchor + reconstruct, single-anchor or start/end
  pair (Warning 2). For pairs, an unmatched `_inicio`/`_fim` is a data-quality signal.
- **Don't over-label operative categories** — one operative anchor per decision; no
  intermediate/reasoning cues (see Ontology design).
- **Reproducibility.** Set/record a seed; capture `finetune_summary.json` per run.
- **Verify the CLI surface.** Flag names beyond `--validation-dataset`,
  `--label-space-json`, `--output-dir` should be confirmed with `--help` rather than
  assumed.
- **OPF is a detection aid, not a guarantee.** OpenAI explicitly flags legal/medical
  as high-risk. Keep a human-review path for anything consequential.
- **Annotating with an agent? Spawn subagents, not an API script** — one subagent per
  labeling batch / per evaluator role. See the `llm-work-via-subagents` skill.
- **Commit the gold to git; Drive/IA are caches.** Version-control the reviewed splits +
  `label_space.json` + `manifest.json` (`.gitignore` whitelist) so annotation
  improvements are reviewable diffs and checkpoints trace to exact labels — see
  `references/colab-and-drive.md`.

## Reference files

- `references/annotation-format.md` — JSONL schema, character-offset rules, label-space
  JSON, model-assisted annotation strategy, common annotation mistakes.
- `references/training-and-eval.md` — install/CLI, `opf train`/`eval`/`redact`,
  operating-point (precision/recall) tuning, hardware, output artifacts, inference code.
- `references/ontology-recipes.md` — ontology-design patterns (anchor vs. pair, define vs.
  activate, scoping) with worked, generalizable examples.
- `references/colab-and-drive.md` — runtime organization: separate data-prep vs. training
  notebooks joined by a frozen artifact set, Drive layout for base model + checkpoints,
  caching patterns, and Colab environment gotchas.

## Bundled script

- `scripts/opf_annotate.py` — validate/convert span annotations to OPF JSONL.
  `validate` (offset sanity, overlap, UTF-8, label-space coverage), `from-spans`
  (build JSONL from `(text, [(start,end,category)])`), `preview` (render spans
  inline to eyeball boundaries). Run `uv run scripts/opf_annotate.py --help`.

## Real-use postmortem

After any material use of this skill, perform a brief self-postmortem before ending the task:
assess whether routing was correct, whether the skill materially improved/neutral/degraded the
result, what concrete instruction mattered, and any friction or workaround. Routine success
stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and add
evidence to an existing matching issue or open a sanitized **Skill use feedback** issue. Never
publish secrets, private/confidential facts, credentials, or personal data, and do not interrupt
the user's task merely to report feedback.
