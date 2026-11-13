# Large batches: THX-02 on a free GPU

For large batches, run THX-02 on a free GPU instead of a hosted API.
"Large" means thousands of items, repeated sweeps over a codebase, or any
batch the hosted limits would stretch over days. On a GPU:

- **There is no rate limit.** The free `api.hal-x.ai` route is limited per IP,
  and the Gemini free tier stops at 10k requests per day.
- **Inputs stay in your account.** Nothing goes to a third-party API, and the
  Gemini free tier's training terms do not apply.
- **The cost is zero** within the provider's free GPU quota.

For a few hundred items, the hosted routes are simpler.

## Before the batch

- **Size:** 4.5B decision model, about 9 GB of weights from Hugging Face
  (`HAL-X-AI/THX-02`). It fits the T4's 16 GB.
- **Precision on a T4:** `thx02` 1.0.0 always loads the model in BF16 on CUDA,
  and there is no FP16 option. The T4 (sm75) and Kaggle's P100 (sm60) have no
  native BF16, so the run may be slower, or its probabilities may differ from
  the API. `../scripts/thx_gpu.py` prints a warning when it sees such a GPU.
- **Calibrate first:** run your answer key, or 20 to 50 items, on the GPU and
  on the API, and compare. Only then start the batch. Also time those items:
  the throughput on a T4 is not published, so measure it yourself.
- **Thinking mode:** it needs a vLLM "thinker" server, which does not fit
  beside the model on a T4. Use `think=False`, which the script does.
- **Library API:** `THX02.load(path, device="cuda")` loads the model.
  `.decide(state, questions, think=False)` returns `{"model", "answers"}`. A
  malformed question raises `RequestError`. A single question that does not
  fit the context raises `LengthError`; the script records that one per item
  and goes on.

## Input and output

`../scripts/thx_gpu.py` uses the same JSONL contract as `../scripts/thx.py`:

- input `entradas.jsonl`: one `{"id", "input"}` per line;
- questions `perguntas.json`: the `questions` object;
- output `saida.jsonl`: one `{"id", "answers", "erro"}` per line.

The output is resumable: ids already written are skipped. If a free session
dies, start a new one with the partial output and run again.

The script finds the files by environment:

| Environment | Input and questions                                  | Output                        |
| ----------- | ---------------------------------------------------- | ----------------------------- |
| Colab       | `/content/entradas.jsonl`, `/content/perguntas.json` | `/content/saida.jsonl`        |
| Kaggle      | first match under `/kaggle/input`                    | `/kaggle/working/saida.jsonl` |

The variables `THX_ENTRADAS`, `THX_PERGUNTAS`, `THX_SAIDA` and `THX_MODELO`
override these paths and the model.

## Colab T4 with the colab CLI

The colab CLI runs on Linux, macOS and WSL. On Windows, see the
[`free-gpu`](../../free-gpu/SKILL.md) skill. Use a named session, so that you can
send the inputs and collect the output:

```bash
C="uvx --from google-colab-cli colab"
$C new -s thx --gpu T4
$C install -s thx "thx02[local]"   # optional: the job installs it when missing
$C upload -s thx entradas.jsonl /content/entradas.jsonl
$C upload -s thx perguntas.json /content/perguntas.json
$C upload -s thx saida.jsonl /content/saida.jsonl   # only when resuming
$C exec -s thx -f thx/scripts/thx_gpu.py
$C download -s thx /content/saida.jsonl ./saida.jsonl
$C stop -s thx
```

- **Always run `stop`,** even after a failure: put the commands in a script
  with a cleanup trap.
- **Free Colab sessions are capped and can be reclaimed.** Download
  `saida.jsonl` between chunks of the input. To resume, upload it again and
  run `exec` once more.

## Kaggle GPU

Prefer Kaggle for long, unattended runs: a job runs to completion with no open
session, within a weekly GPU quota (check your account page). The job
needs internet to download the weights. The inputs travel as a **private**
dataset.

```bash
K="uvx --from kaggle kaggle"
mkdir -p thx-dados && cp entradas.jsonl perguntas.json thx-dados/
$K datasets init -p thx-dados          # edit the title and id in dataset-metadata.json
$K datasets create -p thx-dados        # private by default
uv run free-gpu/scripts/create_kaggle_job.py thx/scripts/thx_gpu.py \
  --owner USERNAME --slug thx-lote --output-dir .kaggle-thx --internet
```

Before pushing:

- In `.kaggle-thx/kernel-metadata.json`, set
  `"dataset_sources": ["USERNAME/<dataset-slug>"]`.
- Nothing else: the job installs `thx02[local]` when it is missing.

Then push, follow, and download the output:

```bash
$K kernels push -p .kaggle-thx --accelerator NvidiaTeslaT4
$K kernels status USERNAME/thx-lote
$K kernels output USERNAME/thx-lote -p ./saida
```

- Keep the dataset and the kernel private.
- To resume a run that was cut short, add the partial `saida.jsonl` to the
  dataset and set `THX_SAIDA` to a copy of it under `/kaggle/working`.

## Rules for both

- **Confirm the data may go to Google or Kaggle before uploading.** Never
  include cookies, signed URLs, session hashes or query values: send only
  source code.
- **Verify the GPU in code before the 9 GB download.** The script does this
  and exits when no CUDA device is present.
- **Record the provider, the GPU and the `thx02` version with each output,** so
  you can compare runs later.
