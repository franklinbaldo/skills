# Windows without WSL or administrator rights

The official Colab CLI states that Windows is unsupported. Prefer Kaggle on
native Windows. Use the compatibility launcher only for non-interactive Colab
commands and revalidate it after every Colab CLI upgrade.

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

## Colab compatibility launcher

Validate the current package before authentication:

```powershell
uv run --no-project --with google-colab-cli python `
  <skill-dir>\scripts\colab_windows.py version
uv run --no-project --with google-colab-cli python `
  <skill-dir>\scripts\colab_windows.py run --help
```

Use the same prefix for supported non-interactive commands:

```powershell
uv run --no-project --with google-colab-cli python `
  <skill-dir>\scripts\colab_windows.py run --gpu T4 job.py
```

Do not use `console` or `ssh`; they require Unix terminal facilities. The
launcher does not patch the installed package and stores no credentials itself.

Official references:

- <https://docs.astral.sh/uv/getting-started/installation/>
- <https://github.com/googlecolab/google-colab-cli>
