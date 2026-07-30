# Kaggle CLI GPU jobs

Kaggle Kernels run asynchronously and work well from native Windows.

## Authentication

Prefer browser OAuth:

```powershell
uvx --from kaggle kaggle auth login
```

Alternatives are `KAGGLE_API_TOKEN`, `~/.kaggle/access_token`, or the legacy
`~/.kaggle/kaggle.json`. Never commit these. Kaggle workload secrets must be
created in the web notebook editor; the CLI does not create them.

## Job directory

The directory must contain one script/notebook and `kernel-metadata.json`.
Important fields:

- `id`: `owner/slug`
- `code_file`: local code filename
- `kernel_type`: `script` or `notebook`
- `is_private`: keep `true` unless publication is intentional
- `enable_gpu`: `true`
- `machine_shape`: requested accelerator, such as `NvidiaTeslaT4`
- `enable_internet`: enable only when the workload needs downloads

The bundled `create_kaggle_job.py` creates a private script job safely.

## Run and retrieve

```powershell
uvx --from kaggle kaggle kernels push -p .kaggle-job `
  --accelerator NvidiaTeslaT4
uvx --from kaggle kaggle kernels status USERNAME/gpu-job
uvx --from kaggle kaggle kernels files USERNAME/gpu-job
uvx --from kaggle kaggle kernels output USERNAME/gpu-job -p .\output
```

Poll status with a reasonable interval; do not busy-loop. On failure, inspect
the Kernel in Kaggle and preserve the error evidence. Files intended for
download must be written under `/kaggle/working`.

Accelerator names and eligibility change. Read current CLI help and provider
documentation rather than assuming that a listed A100/H100 is available to the
account.

Official references:

- <https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md>
- <https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md>
