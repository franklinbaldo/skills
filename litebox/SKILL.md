---
name: litebox
description: >-
  Adapt Linux-only CLI workflows to Windows x86-64 userland with Microsoft's experimental LiteBox
  when native execution, WSL, containers, virtual machines, or administrator installation are
  unavailable. Use when another skill points here, the user mentions LiteBox, or an agent must
  improvise around a Linux ELF on a locked-down Windows machine. Teaches the build-package-run-bridge
  workflow and application-level validation; it is not a support matrix.
---

# LiteBox escape hatch

Use LiteBox as an **adaptation lesson**: work out how to carry one bounded Linux
program across a constrained Windows environment. Do not treat it as a Linux
distribution or require a prebuilt bundle before attempting the task.

LiteBox currently describes itself as actively evolving, without a stable
release. Its Windows userland runner targets Windows x86-64, runs a rewritten
Linux ELF from an in-memory initial filesystem, and does not boot Linux,
Hyper-V, or WSL.

## Work the escape

1. **Map the constraint.** Establish:

   - Windows architecture;
   - why native execution, WSL, containers, a VM, and normal installation are
     unavailable;
   - the Linux entrypoint and its shared libraries;
   - required files, stdout/stderr, network, credentials, persistence, TTY, and
     GPU behavior.

   Continue when the workload boundary and every input/output channel are
   explicit. LiteBox is strongest for bounded CPU CLIs. A workload that needs
   local CUDA, kernel modules, namespaces, arbitrary host mounts, or a rich
   interactive terminal is a poor candidate.

2. **Pin the moving parts.** Read the current upstream source before copying
   commands. Record the LiteBox commit, target program version, architecture,
   and dependency source. Never build reproducible automation from floating
   `main` or an unpinned container tag.

3. **Design the bridges before packaging.** The Windows runner receives a TAR
   as its initial filesystem; do not assume that an arbitrary host path will
   appear inside it or that files written there will survive exit.

   Prefer, in order:

   - stdin/stdout for text;
   - base64 over stdout for small binary results;
   - an application-controlled HTTPS/object-storage transfer for large files;
   - packaging immutable input files into the initial TAR.

   Pass secrets at runtime through the narrowest supported channel. Never put a
   Drive credential, Hugging Face token, Colab token, Kaggle token, or private
   key into a reusable TAR, repository, CI artifact, log, or command transcript.

4. **Produce both sides of the bridge.**

   - On Linux, use `litebox_packager` to discover dependencies, rewrite ELF
     syscall sites, and create the initial TAR. It can package local ELF files
     or a public OCI image.
   - On Windows x86-64, build or obtain
     `litebox_runner_linux_on_windows_userland.exe`.

   When the Windows host has no Linux environment, use an authorized,
   disposable Linux builder such as an existing CI job or temporary cloud
   runtime, then download only the TAR. A Windows CI job can build the runner
   when the host also lacks a usable Rust/MSVC toolchain. Do not upload private
   task inputs merely to bootstrap the generic binaries.

   Read [the Windows userland workflow](references/windows-userland-workflow.md)
   before building or running either side.

5. **Run the smallest probe.** Start with `--version`, `--help`, or a
   deterministic one-line transformation. Then exercise, separately:
   filesystem reads, stdout, DNS/TLS, authentication, WebSockets, and output
   extraction as required by the real application. A successful process start
   proves only that the probe ran.

6. **Grow one capability at a time.** On failure, classify it before changing
   the package:

   - missing ELF/shared library or loader;
   - missing CA certificate, locale, font, profile, or data file;
   - unsupported syscall or kernel behavior;
   - incorrect path/environment;
   - absent input/output bridge;
   - application-level incompatibility.

   Repackage only the missing dependency or change one bridge at a time. Keep
   the smallest passing probe as a regression check.

7. **Validate the actual task.** Use the domain skill's completion criteria:
   veraPDF and page/text checks for PDF/A, OCR page coverage for PaddleOCR,
   session/upload/download/stop checks for Colab, or kernel push/status/output
   checks for Kaggle. Never report success from an exit code alone.

8. **Leave a trail.** Record the pinned inputs, build commands, hashes, probes,
   limitations, and validation result. Cache a working generic bundle when
   useful, but retain the method so the next agent can rebuild or adapt it.

## Choose the lesson, not a promise

- Try LiteBox even without a ready-made bundle when the user wants the agent to
  explore this escape hatch.
- Stop when evidence shows that the required syscall, local GPU, persistence,
  or I/O bridge cannot be supplied safely. Explain the exact boundary reached.
- Prefer a simpler native path when it exists, but do not mistake “not the
  default” for “not worth attempting.”
- Treat isolation strength on the Windows-userland runner as unverified for
  adversarial code unless a current threat model or security review establishes
  otherwise.

For task-shaped examples, read
[Ghostscript, Colab CLI, and Kaggle CLI recipes](references/task-recipes.md).

## Sources

- https://github.com/microsoft/litebox
- https://github.com/microsoft/litebox/tree/main/litebox_packager
- https://github.com/microsoft/litebox/tree/main/litebox_runner_linux_on_windows_userland

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
