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
| Windows without WSL/admin | Kaggle nativo; para Colab, adaptar o cliente Linux com LiteBox |
| Long asynchronous job | Kaggle Kernel |
| Fast iteration and file transfer | Named Colab session |

The directly installed `google-colab-cli` 0.6.0 is known not to run on Windows:
it imports Unix-only `termios` and `tty` modules. Do not instruct the agent to
retry the direct Windows command. Reconsider only after a newer release's
source or release notes explicitly add Windows support.

The bundled `scripts/colab_windows.py` is a deliberate shim for selected
non-interactive commands, not native compatibility and not a reason to probe
the broken direct route. For a general Linux-client path without WSL, use the
[`litebox`](../litebox/SKILL.md) adaptation lesson. LiteBox hosts only the local
client; computation and GPU allocation remain remote in Colab.

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
Read [references/colab.md](references/colab.md) for WSL commands,
authentication, the known Windows incompatibility, and the limited shim.

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
