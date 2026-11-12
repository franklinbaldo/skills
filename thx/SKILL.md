---
name: thx
description: Typed decisions with calibrated probabilities — yes/no (noul), choice and score — from THX-02, an open-weights (Apache-2.0) 4.5B decision model by HAL-X-AI, through its free hosted API, the thx02 package, a Colab T4 via the colab CLI, or the Gemini Decisions API (gemini-decision-1) as a hosted alternative. Use for bulk triage where a confidence threshold separates automatic action from human review — code-smell tagging per chunk, deciding whether an error variant stays or goes, routing items to codemod rules.
compatibility: >-
  Hosted routes need network access (api.hal-x.ai or
  generativelanguage.googleapis.com). The local route needs a GPU (Colab T4 via
  the colab CLI, or Kaggle) and the HAL-X-AI/THX-02 weights from Hugging Face.
  Scripts run with `uv run`.
---

# thx — typed decisions with calibrated probabilities

Ask typed questions about an input and get a probability per answer, with no
generated text. It is a **classifier, not a rewriter**: decide with thx, rewrite
with a deterministic tool (ast-grep, a script), and prove with the compiler or
tests.

## When to use

- Bulk judgment per item: "is this `None` reachable?", "does this error drop
  the observed value?", "which class?".
- Multi-label tagging: one `noul` question per tag, many tags per request.
- Routing: confidence ≥ threshold goes to automatic action, the rest to review.

Do not ask it about facts outside the input (how often something happens in
production data, control flow across files). Measure those first and include
the measurement in the input.

## Question types

The same three types in THX-02 and in the Gemini Decisions API:

```json
{
  "refund": {"type": "noul", "instructions": "Does the customer ask for a refund?"},
  "team": {
    "type": "choice",
    "instructions": "Which team should handle this?",
    "criteria": {"billing": "Charges and refunds", "support": "Technical problems"}
  },
  "anger": {
    "type": "score",
    "instructions": "How frustrated is the customer?",
    "criteria": ["calm", "annoyed", "angry"]
  }
}
```

- `noul`: the answer is the probability of "yes", for example `{"type": "noul", "noul": 0.97}`.
- `choice`: `criteria` is a **map** from id to description (THX-02 accepts up to
  255 options). The answer has `choice`, `probabilities` by id and `confidence`.
  On Gemini, sending a list here returns HTTP 400 `Invalid input at 'questions.<id>'`.
- `score`: `criteria` is an ordered **list**. The answer has the probability of
  each level.
- Put many short questions in one request: every question's instructions count
  as input.

## Endpoints

Check this table before relying on it. The THX-02 facts come from its model
card and the `thx02` package; the free-tier numbers are not published.

| Route                                                                       | Model                           | Free tier                                                      | Notes                                                                                      |
| --------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `api.hal-x.ai` (`thx02` client; docs at api.hal-x.ai/docs/thx-02)           | THX-02                          | Yes; the key is optional and limits are per IP                 | `pip install thx02`; key in `HALX_API_KEY` when needed.                                    |
| [Hugging Face Space](https://huggingface.co/spaces/hugging-apps/thx-02)     | THX-02                          | Yes                                                            | Manual trials, not bulk.                                                                   |
| Self-hosted server (`thx02[server]`)                                        | THX-02                          | Your GPU                                                       | `POST /v1/decide` with `{"state", "questions", "think"}`, `Authorization: Bearer <token>`. |
| Colab T4 / Kaggle, via the [`free-gpu`](../free-gpu/SKILL.md) skill         | THX-02                          | Free GPU quota                                                 | See below.                                                                                 |
| Gemini Developer API (`generativelanguage.googleapis.com/v1beta/decisions`) | gemini-decision-1 (proprietary) | 200 RPM, 50k TPM, 10k RPD; **inputs may be used for training** | Header `x-goog-api-key`. Paid tier: about US$0.10 per 1M input tokens.                     |
| [OpenRouter](https://x.com/OpenRouter/status/2120583084005605816)           | gemini-decision-1               | Not confirmed                                                  | US$0.10 per 1M input tokens.                                                               |

`gemini-decision-1` has no published weights and cannot run on your own GPU.
THX-02 can.

## Running THX-02 on a Colab T4 with the colab CLI

- **Size:** 4.5B decision model plus a 60M "think" adapter. The model card
  recommends BF16 and "one RTX 4090 (24 GB)"; it does not say anything about a
  T4.
- **Does it fit a T4?** 4.5B in 16-bit is about 9 GB, so it fits the T4's
  16 GB. The T4 has no native BF16, so load in FP16 (or FP32 on CPU) and check
  that the probabilities match a BF16 or API run on a sample.
- **Thinking mode:** it needs the thinker served by vLLM (FP8 on 24 GB GPUs).
  On a T4, use `think=False`.

Steps:

1. Open a T4 session with the [`free-gpu`](../free-gpu/SKILL.md) skill:
   `colab` CLI on Linux/macOS/WSL, or a Kaggle Kernel for long runs.

2. On the session:

   ```bash
   pip install "thx02[local]"
   hf download HAL-X-AI/THX-02 --local-dir THX-02
   ```

   ```python
   from thx02 import THX02
   m = THX02.load("THX-02")
   ```

3. Feed the same JSONL contract as `scripts/thx.py`:
   `{"id", "input"}` in, `{"id", "answers", "tokens"}` out. Pull the output
   back with the colab CLI file transfer.

Use the T4 when data must not leave the account, when the free API's per-IP
limit is too slow, or to avoid the Gemini free tier's training terms.

## Calibration: always check against an answer key

The model card says the probabilities are calibrated on its training
distribution. In a different domain, check a few hundred labeled examples
before trusting the confidence.

Observed with gemini-decision-1 on a 14-item answer key from the `ies` project
(decisions already taken by the owner: should this error variant stay or go?):

- **At confidence ≥ 0.9 it was right 4 out of 4.** Overall it was right 7 out of 14.
- It is reliable when the evidence is inside the snippet: a dropped observed
  value, or a case made impossible by the HTML5 tree.
- It fails when the deciding fact is outside the snippet: measured zero
  occurrences in recorded traffic, flow across files, or a `frameset` producing
  a document without `body`.

Re-run the same key on THX-02 before switching models.

## Recipes

### Code-smell tags per chunk

1. Split the source into top-level items (`fn`, `impl`, `enum`), at most about
   120 lines each, production code only.
2. Ask one `noul` question per tag. With 14 tags this comes to about 1,100
   input tokens per chunk.
3. Store one JSONL line per chunk, with the file, the line and the
   probability of each tag.
4. Rank by tag. Dense tags become codemod rules; sparse tags become a review
   list.

### Keep or remove an error variant

- **Input:** the project's criterion in two lines, the variant definition, and
  up to six construction or handling sites.
- **Questions:**
  - `impossivel` (noul);
  - `sem_fato` (noul);
  - `veredito` (choice): `fica`, `sai`, `carrega_valor`, `separa` or `achata`.
- **Threshold:** 0.9 for automatic action, as long as the answer key confirms it.

## Keys and privacy

- Never paste a key in chat or commit it. Read it from a secret store at run
  time and keep it only in memory. Franklin's Gemini key is `gemini-api-key` in
  Secret Manager (project `virtual-computer-fsb`), readable from Jatobá.
- `API_KEY_SERVICE_BLOCKED` from Gemini means the key's API restrictions do
  not include the Generative Language API, or the key belongs to another
  project. Fix the key; do not retry.
- Do not multiply free projects to bypass limits.
- Throughput is usually limited by your own pauses, not by the quota. With
  about 800 tokens per call, two parallel workers reached about 170 calls per
  minute on Gemini without a single 429. Back off only on 429.

## Script

`scripts/thx.py` (PEP 723, `uv run`) runs a questions file over a JSONL of
inputs. The output can be resumed, and the work can be split into parallel
slices.

```bash
GEMINI_API_KEY=... uv run thx/scripts/thx.py executar entradas.jsonl perguntas.json saida.jsonl --fatias 2
```

Ids that already have an answer are skipped, so a run that was killed resumes
where it stopped. For THX-02, use the `thx02` client or the local runtime with
the same JSONL contract.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
