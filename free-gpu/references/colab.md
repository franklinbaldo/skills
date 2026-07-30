# Colab CLI workflow

## Supported host

The official CLI supports Linux and macOS. On Windows, prefer WSL:

```powershell
wsl -d Debian -- bash -lc 'uvx --from google-colab-cli colab version'
```

Without WSL, use the compatibility launcher documented in
`windows-no-admin.md`, limited to non-interactive commands.

## Authentication

The first resource command launches the configured Google OAuth flow. Keep the
CLI state under the user's profile. Do not export refresh tokens to notebooks,
Colab Secrets or Google Drive.

Check state before allocating:

```bash
uvx --from google-colab-cli colab sessions
```

## One-shot versus named session

Use `colab run --gpu T4 job.py` when the script can stream its result and needs
no separate uploads/downloads. It creates, executes and releases the VM.

Use a named session for dependencies and artifacts:

```bash
colab new -s job --gpu T4
colab install -s job -r requirements.txt
colab upload -s job input.bin /content/input.bin
colab exec -s job -f job.py
colab download -s job /content/output.bin ./output.bin
colab log -s job -o execution.ipynb
colab stop -s job
```

In automation, put `colab stop` in a cleanup handler. Verify both
`torch.cuda.is_available()` and the reported device name inside the workload.

GPU names exposed by the current CLI include T4, L4, G4, H100 and A100, but
availability depends on the user's Colab plan, quota and current capacity.

Official reference:

- <https://github.com/googlecolab/google-colab-cli>
