---
name: thx
description: Typed decisions with calibrated probabilities — yes/no (noul), choice and score — from THX-02, an open-weights (Apache-2.0) 4.5B decision model by HAL-X-AI, through its free hosted API, locally on a free Colab T4 (colab CLI) or Kaggle GPU for large batches, or the Gemini Decisions API (gemini-decision-1, also on OpenRouter) as a hosted alternative. Use for bulk triage where a confidence threshold separates automatic action from human review — code-smell tagging per chunk, deciding whether an error variant stays or goes, routing items to codemod rules.
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

| Route                                                                                         | Model                           | Free tier                                                      | Notes                                                                                                                                                                       |
| --------------------------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `api.hal-x.ai/v1/decide` (`thx02` client; docs at api.hal-x.ai/docs/thx-02)                   | THX-02                          | Yes, no key needed for `thx-01`/`thx-02`; limited per IP       | Send `"model": "THX-02"`: without it the API answers with **THX-01**. Body `{"model", "state", "questions", "think"}`.                                                      |
| [Hugging Face Space](https://huggingface.co/spaces/hugging-apps/thx-02)                       | THX-02                          | Yes                                                            | Manual trials, not bulk.                                                                                                                                                    |
| Self-hosted server (`thx02[server]`)                                                          | THX-02                          | Your GPU                                                       | `POST /v1/decide` with `{"state", "questions", "think"}`, `Authorization: Bearer <token>`.                                                                                  |
| Colab T4 / Kaggle GPU, `scripts/thx_gpu.py`                                                   | THX-02                          | Free GPU quota                                                 | **For large batches.** See [references/gpu-lotes.md](references/gpu-lotes.md).                                                                                              |
| Gemini Developer API (`generativelanguage.googleapis.com/v1beta/decisions`)                   | gemini-decision-1 (proprietary) | 200 RPM, 50k TPM, 10k RPD; **inputs may be used for training** | Header `x-goog-api-key`. Paid tier: about US$0.10 per 1M input tokens.                                                                                                      |
| OpenRouter (`POST openrouter.ai/api/alpha/decisions`, body `{"model", "state", "questions"}`) | `google/gemini-decision-1`      | Paid: US$0.10 per 1M input tokens; no daily cap                | Tested 13/11/2026: 9/14 on the answer key, the same as the Google API. The key must cover the apex host `openrouter.ai` (`*.openrouter.ai` does not).                       |
| OpenRouter                                                                                    | `parallel/decisions-fast:free`  | Yes                                                            | **Not for code.** Tested 13/11/2026: 6/14 on the answer key; it misread literal facts and returned 10 web citations on every call, so the input is sent to a search engine. |

`gemini-decision-1` has no published weights and cannot run on your own GPU.
THX-02 can.

## Large batches: THX-02 on a free GPU

For thousands of items, repeated sweeps or private code, run THX-02 on a free
Colab T4 (colab CLI) or Kaggle GPU with `scripts/thx_gpu.py`. There is no rate
limit, and the inputs stay in your account. `thx02` always loads BF16 on CUDA,
which the T4 lacks natively, so calibrate on a sample before the batch. Steps,
paths and resume procedure: [references/gpu-lotes.md](references/gpu-lotes.md).

## Ask facts, not preferences

The most important rule. A question like "should this be deleted?" or "what
should be done?" asks about **your** policy, not about the input, and no
model can read your policy from the snippet. Ask only facts the input
contains, and turn them into a verdict with a rule written in code.

Sort every fact by who can answer it:

| Kind of fact | Who answers                          | Example                                                                                                                     |
| ------------ | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| Structural   | the parser/AST, no model             | Does the variant carry data? Is its only field another error? Is it constructed anywhere, or only matched?                  |
| Semantic     | thx, 1–2 short `noul` questions      | Is the value that failed the check available where the error is created? Does the checked condition exist in a browser DOM? |
| World        | measurement (logs, recorded traffic) | How often does this case occur in production?                                                                               |
| Verdict      | a rule in code                       | not constructed or impossible → remove; drops an available value → carry it; …                                              |

Measured on the same 14-item key. The last column is the current method: the
AST answers the structural facts, the model answers two semantic `noul`
questions with `true`/`false` criteria, and the state is JSON holding only
the construction sites.

| Model             | Preference question | Facts + rule (old extractor) | AST facts + 2 semantic questions |
| ----------------- | ------------------- | ---------------------------- | -------------------------------- |
| THX-02            | 4/14                | 7/14                         | **8/14**                         |
| gemini-decision-1 | 7/14                | 9/14                         | **7/14**                         |

The "old extractor" numbers are inflated. It cut each file at the first
`#[cfg(test)]`, which dropped the production code after a test module in the
middle of a file. Three variants then looked "never constructed" and were
counted right for the wrong reason. **Check the extractor against the source
before blaming or crediting the model.**

The current question set can reach at most **11/14**: three owner decisions
depend on reasons no question asks about (a wrapper that stays, a wrapper and a
cookie error removed for non-DOM reasons). When the score stalls, compute this
ceiling first. If it is low, the questions are missing a fact; a better model
will not help. Both models still miss a value hidden inside a chained
expression (`ler(self.unico(chave)?)`), so keep semantic questions concrete
and short. For wording, criteria and thresholds, follow
[references/perguntas.md](references/perguntas.md).

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

THX-02 on the same key (2026-11-12, hosted API, `model: "THX-02"`): it chose
`fica` for **all 14** items, with or without thinking (`think: "auto"`). Its
`noul` answers stayed between 0.17 and 0.55, so they barely separate the
classes. Only `sem_fato` was slightly higher on the two "carrega valor" items
(0.55 and 0.64). On Rust code with Portuguese criteria, this is outside its
training distribution. With AST facts and two semantic questions it scored
8/14, ahead of gemini-decision-1 (7/14), but its `noul` values sit closer to
0.5, so a threshold separates less. Re-run the key for every new domain
before trusting either model.

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

Treat this as an **exploratory map**, not as decisions. Some tags are
preferences ("burocracia", "nome_meta") or depend on code outside the chunk
("duplicacao"). In the `ies` run (2,314 chunks, 0 API errors), the tags with
p ≥ 0.9 were `ok_engole_erro` 45, `option_colapsa_fatos` 33 and
`bool_esconde_motivo` 12. Their top sites matched a manual antipattern sweep
made independently. Use the map to choose families, then switch to the
AST-located, per-site questions above.

### Keep or remove an error variant

1. **Structural facts, from the AST:** `tem_campo` (the variant carries data),
   `so_embrulha` (its only field is another error type), and `construida` (it
   is created somewhere, not only matched).
2. **Semantic facts, from thx** (`noul`):
   - `valor_em_maos`: where the variant is created, is the value that failed
     the check available? Ask this only when the variant has no field.
   - `dom_impossivel`: does the checked condition describe something that
     cannot exist in a browser DOM?
3. **World facts, from measurement,** when the case depends on data, for
   example zero occurrences in recorded traffic.
4. **Verdict, by rule:**
   - not constructed, or the condition is impossible → `sai`;
   - no field and the value is at hand → `carrega_valor`;
   - only wraps another error, in a leaf (not a command-level aggregate) →
     `achata`;
   - otherwise → `fica`.

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
where it stopped.

`scripts/thx_gpu.py` runs THX-02 locally on a Colab or Kaggle GPU, with the
same JSONL contract. Use it for large batches; see [references/gpu-lotes.md](references/gpu-lotes.md).

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
