# Training, evaluation & inference

## Install

The `opf` CLI ships in the OpenAI repo. Weights are on the Hub.

```bash
git clone https://github.com/openai/privacy-filter
cd privacy-filter
pip install -e .          # exposes the `opf` CLI: redact / eval / train
# base checkpoint: openai/privacy-filter (downloaded on first use, ~3 GB bf16)
```

Repo layout worth knowing:

- `opf/__main__.py` — unified CLI entry (`redact`, `eval`, `train`).
- `opf/_train/` — fine-tuning runners. `opf/_eval/` — dataset loading, metrics.
- `opf/_core/` — span conversion + decoding. `opf/_model/` — transformer + weights.
- `examples/scripts/finetuning/` — runnable demo harnesses (copy these).
- `examples/data/finetuning_custom_label_demo/` — `{train,validation,test}.jsonl` to
  see the exact schema in practice.

Always sanity-check the live flag surface: `opf train --help`, `opf eval --help`.

## Train

Minimal:

```bash
opf train train.jsonl --output-dir ./ckpt
```

Recommended (explicit validation + custom ontology):

```bash
opf train train.jsonl \
  --validation-dataset val.jsonl \
  --label-space-json label_space.json \
  --output-dir ./ckpt_legal_v1
```

Output dir contains:

- `config.json` — model + label-space config.
- `model.safetensors` — fine-tuned weights.
- `finetune_summary.json` — run metrics/metadata (archive this per run).
- `USAGE.txt` — generated usage notes for the checkpoint.

### Demo harnesses

`examples/scripts/finetuning/finetune_custom_label_demo.sh` defines a brand-new label
space (`O` + one new category) and trains the model to recognize it instead of the
originals — the closest template to a legal-region fine-tune. The
`finetune_secret_demo.sh` shows adapting to a *policy change* on an existing category.
Both accept `--checkpoint` (required), optional `--workdir`, optional
`--output-checkpoint-dir` (defaults to `<workdir>/finetuned_checkpoint`). They use
tiny toy splits and high epoch counts so before/after behavior is obvious — scale both
down/up for real data.

### Data budget

OpenAI found ~10% of their training split already pushed F1 >96% and nearly saturated
the benchmark. Start small (hundreds–low thousands of PT-BR examples), measure, and add
data where the per-category F1 is weakest rather than uniformly. Remember Warning 1:
the English data-efficiency numbers are optimistic for PT-BR.

## Evaluate

```bash
opf eval test.jsonl --label-space-json label_space.json   # confirm flags with --help
```

What to look at, for legal text specifically:

- **Span-level F1**, and separately **exact-match vs. partial/overlap** F1. Boundary
  drift is the characteristic OPF failure mode on formatted text, so a model can have
  good "did it find the region" recall but poor exact boundaries.
- **Per-category** breakdown — anchors (short, cue-based) usually score far higher than
  any dense-region category, which is a signal to re-anchor that category.
- A few **qualitative renders** (`scripts/opf_annotate.py preview`) beat any single
  number for spotting systematic boundary errors.

## Operating-point tuning (precision vs. recall)

Decoding is a constrained Viterbi over BIOES tags with linear-chain transition scoring
plus six transition-bias parameters (background persistence, span entry, continuation,
closure, boundary handoff). Tuning these shifts the operating point **without
retraining**:

- Discourage staying in background / encourage span entry+continuation → broader,
  more contiguous spans → **higher recall**.
- The opposite → tighter, fewer spans → **higher precision**.

For legal work, a false positive (mislabeling text as the dispositivo or a wrong
outcome) is usually costlier than a miss a human can catch on review, so **bias toward
precision** and keep a review path. Set the operating point on the validation set, then
confirm once on the held-out test set. Exact parameter names: `opf eval --help` and the
decoding config in `opf/_core/`.

## Inference / integration

CLI redaction-style output:

```bash
opf redact --checkpoint ./ckpt_legal_v1 input.txt
```

Or load directly with transformers and consume spans in your pipeline:

```python
from transformers import pipeline

clf = pipeline("token-classification", model="./ckpt_legal_v1",
               aggregation_strategy="simple")   # groups BIOES into whole spans
out = clf(open("acordao.txt").read())
# out: [{"entity_group": "dispositivo", "score": ..., "word": ...,
#        "start": <char>, "end": <char>}, ...]
```

`aggregation_strategy="simple"` is the quick path (HF's own span grouping). The
constrained-Viterbi decoder shipped with the model gives more coherent boundaries than
naive aggregation — use the `opf` runtime / `opf/_core` decoding when boundary quality
matters (it usually does for legal regions).

**Reconstructing long regions** (Warning 2): take consecutive anchor spans and fill the
text between them in post-processing — the model marks `É o relatório` and `Ante o exposto`; your code labels everything between as the relatório region. Do this here, in
integration, not by asking the model to label every token.

## Hardware

50M active params (MoE) makes this light: full fine-tunes run on a single modest GPU,
and CPU inference is viable for batch ETL (Baliza-style). For training on CPU-only,
shrink batch size and expect it to be slow but workable on small PT-BR sets. Capture
the seed and `finetune_summary.json` for every run so checkpoints are reproducible.
