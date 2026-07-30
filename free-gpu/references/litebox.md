# LiteBox as a Windows compatibility route

LiteBox can run packaged Linux ELF programs in Windows userland without WSL or
Hyper-V. It does not create a local GPU. For this skill, it could host a Linux
Colab CLI client that provisions a remote Colab GPU.

## Current status

Treat this as an evaluation path, not an operational default. There is no
checked-in, pinned LiteBox artifact for `google-colab-cli` in this repository.
The client includes CPython, OAuth, TLS, WebSockets, Jupyter kernel traffic and
filesystem state; that dependency and syscall surface is much broader than a
small standalone CLI.

Use native Kaggle on Windows or the bundled non-interactive Colab launcher
before building a LiteBox package solely for this purpose.

## Requirements before using it

1. Pin a LiteBox commit, Python version, `google-colab-cli` version and every
   Linux shared-library dependency.
2. Package the Python interpreter, Colab CLI modules, certificates and required
   shared libraries with `litebox_packager`.
3. Keep OAuth/session state in an explicit Windows-mounted directory with
   restrictive permissions. Never bake credentials into the artifact.
4. Validate `version`, OAuth login, `new --gpu T4`, `exec`, WebSocket traffic,
   upload, download, log export and `stop`.
5. Test cleanup after a failed execution so no Colab session remains active.
6. Reject raw `console`/SSH until terminal behavior is independently tested.
7. Record the packaged artifact SHA-256 and repeat the tests after any upgrade.

If any step fails, use Kaggle natively or WSL on a machine where WSL is
available. LiteBox is actively evolving and its own documentation warns that
interfaces may change before a stable release.

Official reference:

- <https://github.com/microsoft/litebox>
