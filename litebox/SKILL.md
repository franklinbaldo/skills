---
name: litebox
description: >-
  Guidance on when and how to consider Microsoft's LiteBox (github.com/microsoft/litebox) — an
  experimental, MIT-licensed Rust library OS for sandboxing Linux apps and running unmodified Linux
  ELF binaries on Windows userland (no full Linux VM), plus SEV-SNP/OP-TEE/LVBS targets. Use when a
  Linux-only CLI tool needs to run on Windows without installing WSL/Hyper-V, when reducing a Linux
  app's attack surface matters, or when the user mentions LiteBox by name. Always treats it as a
  conditional, verify-before-trusting fallback, not a default path — WSL2/Hyper-V/containers remain
  the default for anything that doesn't specifically need LiteBox's properties.
---

# LiteBox

## Overview

[LiteBox](https://github.com/microsoft/litebox) is a Microsoft-published, MIT-licensed **library OS**
written in Rust. Instead of a full kernel, an application links against LiteBox, which exposes a
Linux/rustix-like syscall interface on its "North" side and maps that onto one of several "South"
platform backends:

- **`litebox_runner_linux_on_windows_userland`** — runs unmodified Linux x86-64 ELF binaries directly
  on Windows, in ordinary Windows userland (Win32 APIs), without booting a Linux kernel or a full
  Linux VM.
- Sandboxing Linux applications on Linux itself (reduced syscall surface vs. the host kernel).
- Running on AMD SEV-SNP confidential-compute hardware.
- Hosting OP-TEE trusted applications.
- Running within Linux Virtualization Based Security (LVBS).
- **`litebox_packager`** — the tool that prepares/rewrites a target ELF binary and its dependencies
  for one of these runners.

**Maturity: pre-release and evolving.** As of this writing LiteBox has not declared a stable release;
the project's own docs state APIs and interfaces may change as the design matures. Treat every command,
flag, and exact component name here as a starting point to re-verify against the live repo, not as a
frozen interface — this file will go stale faster than the code does.

**Security-boundary caveat:** LiteBox is marketed broadly as a "security-focused library OS," but that
framing applies most strongly to its hardware/hypervisor-backed targets (SEV-SNP, LVBS). The plain
Windows-userland runner maps Linux syscalls onto ordinary Win32 APIs with no hypervisor or hardware
isolation underneath — do not treat it as a hard security boundary equivalent to a VM, and do not use
it as a substitute for one when running genuinely untrusted code.

## When to consider it

- A Linux-only CLI tool (a compiled binary, not source you can rebuild for Windows) needs to run on a
  Windows host, and installing WSL2 or enabling Hyper-V is undesirable — e.g. a locked-down or
  minimal-footprint machine, an environment where virtualization features are disabled by policy, or a
  CI runner where spinning up a VM per job is too slow/expensive.
- The workload is small and syscall-simple (a single-purpose encoder/converter/CLI tool is a much
  better fit than a full application stack) — narrow syscall surface means fewer chances of hitting an
  unimplemented syscall.
- Reducing a Linux app's attack surface matters more than raw compatibility, and one of LiteBox's
  hardware-backed targets (SEV-SNP, LVBS) is actually in play — that's where its security framing is
  strongest.
- The user explicitly asks about LiteBox, or asks to run a specific Linux binary on Windows without a
  VM.

## When *not* to use it

- WSL2, Hyper-V, or a container already work and there's no concrete reason (footprint, policy,
  latency) to avoid them — those are mature, broadly-compatible, and don't require pre-verifying
  syscall coverage per binary.
- The target binary is large, syscall-diverse, or depends on kernel features (namespaces, complex
  networking, GPU access, etc.) that a userland syscall-rewriting layer is unlikely to cover completely.
- Production-critical stability is required and the "no stable release yet, APIs may change" caveat
  above is disqualifying on its own.
- The task needs a genuine security boundary against untrusted/adversarial code and only the
  Windows-userland runner is available (see caveat above) — use a real VM or container sandbox instead.
- ARM64 Windows, or any architecture other than x86-64, is a hard requirement — this was not confirmed
  as supported during this skill's research; check the current repo before assuming otherwise.

## How to use it (general workflow)

LiteBox's own docs are the source of truth for exact commands — this is the shape of the workflow, not
a copy-pasteable script:

1. **Identify the target binary and its shared-library dependencies** (`ldd <binary>` on Linux gives
   you the dependency closure).
2. **Package it** with `litebox_packager`, which rewrites the ELF's syscall instructions so they can be
   intercepted and routed through LiteBox's compatibility layer, bundling the binary with whatever
   shared libraries it needs.
3. **Run it** through the appropriate runner crate for your target platform (e.g.
   `litebox_runner_linux_on_windows_userland` for the Windows-without-Hyper-V case).
4. **Verify application-level correctness**, not just "it ran without crashing." Syscall coverage may
   be incomplete — confirm the actual output is correct for your use case (see the worked example
   below for a concrete, bit-exact way to do this for a deterministic encoder).
5. **Always keep a native/mature fallback path** or exit code and fall back to it on any packaging,
   execution, or verification failure. Don't let a LiteBox failure become a hard error in a pipeline
   that has a perfectly good non-LiteBox path.

## Worked example: jbig2enc on Windows without Hyper-V

This scenario motivated writing this skill, and illustrates the decision tree concretely. The
[`pdf-compression`](../pdf-compression/SKILL.md) skill's `--jbig2` flag calls the `jbig2` Linux binary
for lossless bitonal PDF compression (see `pdf-compression/references/jbig2enc-licensing.md`). On Linux
and macOS that's a normal package-manager install; on Windows, without WSL/Hyper-V, LiteBox is a
plausible experimental path — but it is **not currently wired into `compress.py`**, and shouldn't be
until proven out per the checklist below.

```
1. Try the native `jbig2` encoder first (Debian/Ubuntu apt, Homebrew, or a native Windows build if one
   exists) — that remains the primary path everywhere, including Windows.
2. Only if on Windows x86-64 AND no native install is viable AND enabling Hyper-V/WSL is undesirable,
   evaluate LiteBox.
3. Use it only if the jbig2enc Linux ELF and *all* its shared-library dependencies (Leptonica, libpng,
   libjpeg, libtiff, libwebp, openjpeg, zlib, ...) can actually be packaged and run through
   litebox_packager + litebox_runner_linux_on_windows_userland.
4. Mandatory: the resulting JBIG2 stream must still pass the same bit-exact MuPDF roundtrip check the
   native path uses (see pdf-compression/scripts/compress.py's _verify_and_measure_jbig2).
5. On any packaging, execution, or verification failure, fall back to CCITT G4 — same as the native
   path already does when the binary is simply missing.
6. Do not install or enable Hyper-V to make this work — the point of the Windows-userland runner is
   that it doesn't need it; if Hyper-V ends up required, WSL2 is the simpler choice instead of LiteBox.
```

**Why this isn't shipped yet:** there is no ready-made LiteBox artifact bundling jbig2enc today.
Instructing an agent to *evaluate* LiteBox when it looks viable is reasonable; instructing it to
assemble the whole packaging chain from scratch on every run would trade portability for variability —
one run's packaged binary might behave differently from another's. This needs a **pinned, reproducible
build** before it's an operational fallback rather than a hint:

- Pinned Dockerfile/OCI image used to build the jbig2enc ELF and its dependency closure.
- Pinned LiteBox commit (given the "APIs may change" caveat, floating on `main` is not acceptable here).
- A checked-in packaging script (calling `litebox_packager` with fixed arguments).
- The SHA-256 of the resulting packaged artifact, checked into the repo or a release, so "the same
  jbig2 you tested is the jbig2 that runs" is verifiable.
- A real test run on Windows *without* Hyper-V enabled.
- A real test proving both the bit-exact roundtrip **and** that the final embedded size actually beats
  the CCITT G4 fallback (mirroring `pdf-compression`'s own `_g4_embedded_size` comparison) — Windows
  syscall-translation overhead is a plausible source of behavioral drift that a "did it run" check alone
  wouldn't catch.

Until that exists, treat LiteBox-for-jbig2enc as something to *suggest and evaluate*, not something to
wire up as an automatic code path.

## Limitations (general)

- Pre-1.0, evolving API — pin a specific commit for anything beyond one-off experimentation.
- The Windows-userland runner needs the target ELF pre-processed by `litebox_packager`; you can't just
  point it at an arbitrary Linux binary with zero preparation.
- Syscall coverage is not guaranteed to be complete — verify the actual application output, not just
  successful execution.
- Not a hard security boundary in userland mode (see caveat above).
- x86-64 Windows was the only architecture found described in this skill's research; other
  architectures (ARM64) were not confirmed either way — check the current repo.
- Should never fully replace a working native install or a mature virtualization path (WSL2, Hyper-V,
  containers) — it's a narrow-case fallback, not a general substitute.

## References

- Canonical source, always check for current specifics: https://github.com/microsoft/litebox
- Worked-example context: [`pdf-compression/references/jbig2enc-licensing.md`](../pdf-compression/references/jbig2enc-licensing.md)
