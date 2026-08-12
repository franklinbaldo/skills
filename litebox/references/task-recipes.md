# Task recipes

These are adaptation sketches, not support declarations. Read the relevant
domain skill first; its validation rules remain authoritative.

## Ghostscript for PDF/A

**Check for a native Windows binary before starting this exercise at all.**
Ghostscript already ships an official Windows build (an NSIS installer);
extracting it with `7z x gs<version>w64.exe -o<dest>` (no admin, no UAC)
yields a working `gswin64c.exe` in seconds — see the "No admin rights on
Windows?" note in
[`convert-to-pdfa/SKILL.md`](../../convert-to-pdfa/SKILL.md#dependencies).
That is almost always faster and simpler than the LiteBox route below, which
is for the genuinely locked-down case where extracting an archive isn't an
option either (no 7-Zip or equivalent available, no way to run it). A prior
session skipped this check, assumed no admin-free Windows path existed, and
spent real effort packaging a Linux Ghostscript build through
`litebox_packager` + the Windows-userland runner before discovering the
extraction trick.

Ghostscript is a promising LiteBox exercise when the native-binary route is
genuinely unavailable — it's a bounded CPU CLI, but PDF/A conversion needs
more than the executable.

1. Package `gs`, its shared libraries, Resource tree, fonts required by the
   source, `PDFA_def.ps`, and the selected ICC profile.
2. Stage the source PDF in the initial TAR or provide it through a deliberate
   input bridge.
3. Configure Ghostscript to send the PDF to a clean binary-output bridge.
   Base64 stdout is safer than native PowerShell text redirection for a small
   proof; use a streaming/network bridge for large PDFs.
4. Keep diagnostics off the PDF byte stream.
5. Verify page count, dimensions, searchable text, XMP, OutputIntent, and
   Ghostscript parse. Require veraPDF when normative compliance matters.

See `../../convert-to-pdfa/SKILL.md`. LiteBox changes how Ghostscript runs, not
what makes the resulting PDF conformant.

## Colab CLI

The directly installed `google-colab-cli` 0.6.0 is known not to run on Windows:
it imports Unix-only `termios` and `tty` modules. Do not tell the agent to try
the direct Windows command again unless a newer version's release notes or
source explicitly add Windows support.

LiteBox hosts the Linux client; the GPU remains in Google's remote runtime.

1. Package CPython, `google-colab-cli`, Python dependencies, CA certificates,
   locale data, and a small wrapper entrypoint.
2. Keep OAuth/token material out of the TAR. Perform the copy/paste OAuth flow
   at runtime or construct ephemeral credential files from a runtime secret
   channel.
3. Probe in this order: version/help, authentication, list/create session,
   execute a trivial command, upload, download, log, and stop.
4. Exercise HTTPS and WebSockets explicitly.
5. Bridge uploaded and downloaded files: the LiteBox filesystem is not the
   Windows workspace. For small files use base64/stdout; for larger artifacts
   use an authorized transfer endpoint.
6. Always stop the remote Colab session after failure as well as success.

Interactive console and SSH are later probes, not prerequisites for a useful
noninteractive agent workflow.

## Kaggle CLI

The currently verified Kaggle CLI works natively on Windows through
`uvx kaggle`. Use that route unless it is concretely blocked or the exercise
itself is to adapt the Linux CLI.

1. Package CPython, Kaggle CLI, dependencies, CA certificates, locale data,
   and a wrapper entrypoint.
2. Inject credentials only at runtime using the mechanism supported by the
   pinned Kaggle CLI version.
3. Probe version/help and authenticated listing before kernel operations.
4. Stage kernel metadata and source files through the TAR or a transfer bridge.
5. Push a minimal disposable kernel, observe its status/output, download the
   result, and clean up only resources created for the probe.

LiteBox supplies a local Linux userland path; Kaggle supplies the remote
compute. Local GPU passthrough is not part of this workflow.
