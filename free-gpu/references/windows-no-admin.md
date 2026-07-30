# Windows without WSL or administrator rights

The directly installed `google-colab-cli` 0.6.0 is known to fail on Windows
while importing Unix-only `termios` and `tty`. Do not run `uvx colab` directly
as a discovery step. Prefer Kaggle natively or follow the sibling `litebox`
skill to host the Linux Colab client.

## Install uv in the user profile

Inspect the official installer before running it:

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | more"
```

Then run it with a process-scoped execution-policy bypass:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

This does not require administrator rights. Restart PowerShell if `uv` is not
immediately on `PATH`. The official installer also offers downloadable binaries
from GitHub Releases when policy blocks scripts.

## Kaggle native Windows

```powershell
uvx --from kaggle kaggle --version
uvx --from kaggle kaggle auth login
```

OAuth persists an access credential in the user profile. Do not paste it into
source files or command history.

## Deliberate Colab compatibility shim

The bundled shim has been verified only for `version` and non-interactive help;
an authenticated Windows resource run was not validated. Use it only when the
user explicitly chooses to evaluate that workaround, not as the default
Windows route:

```powershell
uv run --no-project --with google-colab-cli python `
  <skill-dir>\scripts\colab_windows.py version
uv run --no-project --with google-colab-cli python `
  <skill-dir>\scripts\colab_windows.py run --help
```

Only after that explicit choice, use the same prefix for a non-interactive
command:

```powershell
uv run --no-project --with google-colab-cli python `
  <skill-dir>\scripts\colab_windows.py run --gpu T4 job.py
```

Do not use `console` or `ssh`; they require Unix terminal facilities. The
launcher does not patch the installed package and stores no credentials itself.
Do not describe a successful help command as proof that OAuth, VM allocation,
WebSockets, upload, download, or cleanup work on Windows.

Official references:

- <https://docs.astral.sh/uv/getting-started/installation/>
- <https://github.com/googlecolab/google-colab-cli>
