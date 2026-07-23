# Runtime organization: data-prep vs. training, and Drive as persistence

OPF's base model is ~2.8 GB and a full fine-tune of the 1.5B model wants a GPU
(fp32 weights + AdamW states ~24 GB exceed a 16 GB GHA runner; a T4's 16 GB VRAM is
fine with bf16 + small batch). Colab runtimes are **ephemeral** — the base checkpoint
re-downloads on every reset and trained checkpoints vanish when the runtime dies. So
the work has to be organized around two facts: *training needs a GPU, and the GPU box
forgets everything between sessions.* This file is the organization strategy that falls
out of those constraints.

## Two notebooks, one contract

Keep **data preparation** and **training** in separate notebooks. They have opposite
profiles:

- **Prep is CPU-bound and iterative.** You re-annotate, re-merge, re-split, re-validate
  many times. You do NOT want to hold (or burn quota on) a GPU while fiddling with
  annotations, and you do NOT want training to silently re-derive its inputs on every
  run.
- **Training is GPU-bound and should be reproducible from frozen inputs.** It consumes
  the prepared splits and never re-runs annotation.

The **contract between them is a frozen artifact set**, not shared code:

```
train.jsonl   val.jsonl   test.jsonl   label_space.json   manifest.json
```

The prep notebook *writes* this set; the train notebook *only reads* it. Benefits: the
splits are auditable (diff across versions), training always sees identical data, and
annotation costs no GPU time. Prep is portable — it can run in a CPU Colab, locally, or
in CI (GitHub Actions "prepare-only" + upload to Internet Archive is a valid backend);
only training requires the GPU notebook. The artifact store can be Drive (Colab-native)
or IA (CI-native) — same files either way.

### The gold set lives in git (source of truth), Drive/IA are caches

Commit the reviewed/gold splits + `label_space.json` + `manifest.json` **to the repo**.
Git is the canonical source of truth for the labels; Drive and IA are only
distribution/runtime caches downstream of it. The mechanism is a `.gitignore` whitelist —
ignore the bulk/derived/raw data, keep the gold:

```gitignore
data/*
!data/segmenter_splits/**
```

Why version-control the gold rather than just stash it on Drive: annotations are a
**living asset you keep improving**, and committing them makes every improvement a
*reviewable diff* — you can see exactly which spans changed, justify them in a PR, bisect
a metric regression to an annotation edit, and re-run from a known state. A gold set
sitting only on Drive is unversioned and unauditable; the same set in git is a dataset
you can evolve with the same rigor as code.

The flow becomes: **gold in git → prep reads it, validates, writes the manifest →
publishes a snapshot to Drive/IA for the GPU runtime.** Prep never re-derives the gold;
it promotes the committed gold into a runtime artifact. Bump `category_version` (and let
the manifest carry `source_commit`) so a checkpoint always traces back to the exact
committed annotations that produced it.

The prep notebook writes a small `manifest.json` alongside the splits; the train
notebook reads it and echoes it into the run. Record at least:

```json
{
  "category_version": "causaganha_v5",
  "seed": 13,
  "source_commit": "6b38676",
  "counts": {"train": 191, "val": 23, "test": 25},
  "per_class": {"sec_dispositivo": 88, "autoridade_judicial": 230, "parte_reu": 48},
  "test_verified_by": "prompt_ensemble:strict+adversarial+blind"
}
```

`test_verified_by` records *how the gold slice was checked* — e.g.
`"prompt_ensemble:strict+adversarial+blind"`, `"cross_family:gpt-x+gemini-y"`,
`"owner_spotcheck"`, or the honest `"same_as_train_labeler"`. It is the difference
between a test score that means "the model is correct" and one that only means "the model
imitates whatever labeled the data." If the evaluators' errors are correlated with the
labeler's (same model, same prompt, same framing), the score is a mirage; a
diverse-prompt/diverse-framing evaluator ensemble decorrelates most of it for free (see
annotation-format.md). Record it honestly.

## Sampling from per-source archives (when there's no consolidated table)

Until consolidation lands you can't sample from a unified dataset, so sample directly
from the per-source archives on IA. This is GHA-native as a **matrix job per source,
then a combine job** — the same "shard in parallel → merge" shape as the annotation
subagents:

- **Matrix job (one per source, in parallel).** Each job downloads *its own* source's
  zip from IA, **stream-extracts** (don't unzip the whole archive — list members and pull
  a seeded random subset; use range requests / partial extraction to respect the runner's
  ~14 GB disk and time limits), takes `N` documents with a **fixed seed**, dedups
  near-identical boilerplate, and emits a per-source sample shard + its counts. Retry
  IA with backoff (it rate-limits).
- **Combine job.** Concatenates the shards into one **sampling pool**, writes
  `sample_manifest.json` (per-source counts, seed, source IA item ids/versions, date
  ranges per annotation-format.md), and publishes the pool to IA/Drive.

The allocation policy (equal-per-source with floor/cap, not proportional — see
annotation-format.md) lives in the matrix `N` and the combine step's caps. Output of this
stage is the **pool to annotate**, not training data; annotation (subagents) and review
run on the pool, and the reviewed gold is what gets committed to git.

The full prep flow is therefore:

```
sample (GHA matrix per source → combine)  →  annotate (subagents)  →  review/eval
  →  validate (opf_annotate.py)  →  splits + label_space + manifest  →  commit gold to git
  →  prep promotes committed gold → snapshot to Drive/IA for the GPU train notebook
```

When consolidation is done, replace the matrix-over-zips with a stratified query over the
consolidated table; everything downstream (allocation, seed, manifest, git) stays the
same.

## Drive layout (the persistence layer)

Give Drive one tree, versioned by `category_version` and run id so nothing clobbers:

```
MyDrive/opf-finetune/
├── base/privacy_filter/                  # OPF base checkpoint — downloaded ONCE
├── data/<category_version>/              # frozen artifact set from the prep notebook
│   ├── train.jsonl  val.jsonl  test.jsonl  label_space.json
│   └── manifest.json
└── checkpoints/<category_version>/<run_id>/
    ├── config.json  model.safetensors  finetune_summary.json  USAGE.txt
    └── test_metrics.json
```

The base model lives **once** under `base/`; every run restores from there instead of
re-downloading. Each training run gets its own `checkpoints/<ver>/<run_id>/` so you can
compare runs and trace a checkpoint back to the exact data version that produced it.

## Caching patterns (learned the hard way)

These are the patterns that turn a flaky notebook into a resumable one. Order matters.

**1. Mount Drive at the very top**, before any install or download, so the cache is
available to every later cell:
```python
from google.colab import drive

drive.mount("/content/drive")
ROOT = "/content/drive/MyDrive/opf-finetune"
```

**2. Restore-or-fetch the base model** (skip the 2.8 GB copy when it is already local):
```python
import os, shutil

LOCAL_BASE = "/content/base/privacy_filter"
DRIVE_BASE = f"{ROOT}/base/privacy_filter"
if os.path.exists(f"{LOCAL_BASE}/config.json"):
    pass  # already here this session
elif os.path.exists(f"{DRIVE_BASE}/config.json"):
    shutil.copytree(DRIVE_BASE, LOCAL_BASE)  # restore from Drive (fast-ish)
else:
    # first time ever: download once, then persist to Drive for all future runs
    from huggingface_hub import snapshot_download

    snapshot_download("openai/privacy-filter", local_dir=LOCAL_BASE)
    shutil.copytree(LOCAL_BASE, DRIVE_BASE)
```

**3. Save the trained checkpoint + metrics to Drive immediately after training**, so a
runtime timeout never loses the run:
```python
RUN = f"{ROOT}/checkpoints/{CATEGORY_VERSION}/{RUN_ID}"
shutil.copytree("/content/out/best", RUN, dirs_exist_ok=True)
# also copy test_metrics.json into RUN
```

## Colab environment gotchas (encoded so you don't re-hit them)

- **Run OPF from the interpreter you installed it into.** Colab ships `uv`, but
  `uv run` discovers the cloned repo's project venv — which does not list `opf` — and
  fails with `No module named opf`. Install with `uv pip install --system` (Colab has
  no venv) and invoke with **plain** `python`, not `uv run`. `%pip install` also works.
- **Use `sys.executable` for shell-outs.** A bare `!python ...` may resolve to a
  different interpreter than the kernel where OPF was installed:
  ```python
  import sys, subprocess

  subprocess.run(
      [
          sys.executable,
          "-m",
          "opf",
          "train",
          "train.jsonl",
          "--validation-dataset",
          "val.jsonl",
          "--label-space-json",
          "label_space.json",
          "--output-dir",
          "/content/out/best",
          "--device",
          "cuda",
      ],
      check=True,
  )
  ```
- **Memory:** `os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"`.
- **Do not cargo-cult `--n-ctx 512`.** That value was a concession to fit CPU/16 GB RAM.
  On a GPU, push `n-ctx` up — long context with no chunking is OPF's whole advantage,
  and at 512 you truncate most legal documents mid-relatório and never see the
  dispositivo (see SKILL.md Warning 2). Set it as high as VRAM allows.

## Why this layout, in one line

Prep is cheap, iterative, and CPU; training is expensive, frozen, and GPU; Colab forgets
everything — so freeze the data into an artifact set, persist the base model and
checkpoints in Drive, and let each notebook do only its half.
