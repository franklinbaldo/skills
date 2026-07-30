---
name: free-gpu
description: Execute Python, OCR, ML, inference, or training workloads on Google Colab or Kaggle GPUs from a local terminal. Use when the local machine lacks a GPU, including Windows machines without WSL or administrator rights, and the agent must install CLIs with uv, authenticate securely, upload code or data, monitor remote execution, retrieve artifacts, and release resources.
---

# Free GPU

Offload bounded GPU jobs to Colab or Kaggle. Do not promise a specific
accelerator or uninterrupted availability: quotas, account eligibility and
capacity vary.

## Route by environment

| Local environment | Preferred route |
| --- | --- |
| Linux or macOS | Colab CLI for one-shot or interactive jobs |
| Windows with WSL | Colab CLI inside WSL |
| Windows without WSL/admin | Kaggle nativo; launcher Colab não interativo; LiteBox somente com artefato previamente validado |
| Long asynchronous job | Kaggle Kernel |
| Fast iteration and file transfer | Named Colab session |

The official Colab CLI currently supports Linux and macOS, not Windows. The
bundled `scripts/colab_windows.py` only bypasses its unconditional Unix TTY
imports for non-interactive commands; it is a compatibility layer, not official
Windows support. Fall back to Kaggle if it breaks after a CLI update.
LiteBox can host packaged Linux programs in Windows userland, but it does not
provide a GPU: it would only host the local Colab client while computation
remains remote. Read [references/litebox.md](references/litebox.md) before
considering that experimental route.

## Install without administrator rights

Use `uvx` so tools live in an isolated user cache:

```powershell
uvx --from kaggle kaggle --version
```

On supported Colab platforms:

```bash
uvx --from google-colab-cli colab version
```

If `uv` is missing, read [references/windows-no-admin.md](references/windows-no-admin.md)
before installing it in the user profile. Never request administrator rights
just to install these Python CLIs.

## Colab workflow

Prefer one-shot execution when the script writes no artifact that must be
downloaded separately:

```bash
uvx --from google-colab-cli colab run --gpu T4 job.py
```

Use a named session when dependencies, uploads or downloads are required:

```bash
uvx --from google-colab-cli colab new -s gpu-job --gpu T4
uvx --from google-colab-cli colab install -s gpu-job -r requirements.txt
uvx --from google-colab-cli colab upload -s gpu-job input.pdf /content/input.pdf
uvx --from google-colab-cli colab exec -s gpu-job -f job.py
uvx --from google-colab-cli colab download -s gpu-job /content/output.zip ./output.zip
uvx --from google-colab-cli colab log -s gpu-job -o execution.ipynb
uvx --from google-colab-cli colab stop -s gpu-job
```

Wrap named-session automation in cleanup so failures still call `colab stop`.
Do not use `--keep` unless the user explicitly wants a persistent session.
Read [references/colab.md](references/colab.md) for Windows/WSL commands,
authentication and the compatibility launcher.

## Kaggle workflow

Create a private script Kernel directory:

```powershell
uv run --no-project python <skill-dir>\scripts\create_kaggle_job.py `
  job.py --owner USERNAME --slug gpu-job --output-dir .kaggle-job
```

Authenticate once, push the job with a GPU, monitor it, and download artifacts:

```powershell
uvx --from kaggle kaggle auth login
uvx --from kaggle kaggle kernels push -p .kaggle-job --accelerator NvidiaTeslaT4
uvx --from kaggle kaggle kernels status USERNAME/gpu-job
uvx --from kaggle kaggle kernels output USERNAME/gpu-job -p .\output
```

The job must write artifacts under `/kaggle/working`. Keep the Kernel private
unless publication is intentional. Read
[references/kaggle.md](references/kaggle.md) for metadata, secrets, datasets
and status handling.

## Security and lifecycle

- Confirm that source data may be uploaded to Google or Kaggle before transfer.
- Use browser OAuth or provider secret stores. Never commit tokens, credential
  files, notebooks containing secrets or downloaded private data.
- Colab Secrets and Kaggle Secrets are for workload secrets, not for storing
  Drive OAuth credentials.
- Treat remote logs and notebook histories as potentially sensitive artifacts.
- Verify the remote GPU in code before expensive work.
- Download outputs, record the provider and accelerator, then stop Colab
  sessions. Kaggle jobs terminate automatically when the run finishes.
- Report live validation honestly. CLI help or a dry run does not prove that
  account quota or GPU allocation succeeded.

Official references:

- <https://github.com/googlecolab/google-colab-cli>
- <https://github.com/Kaggle/kaggle-cli>
- <https://docs.astral.sh/uv/getting-started/installation/>
