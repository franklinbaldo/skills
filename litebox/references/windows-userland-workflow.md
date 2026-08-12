# Windows userland workflow

Use this reference when carrying a particular Linux ELF into Windows. Verify
the live LiteBox CLI before execution: the project is pre-release and these
interfaces can change.

## Contents

- [Build topology](#build-topology)
- [Validated Windows source-only route](#validated-windows-source-only-route)
- [Build core components from source](#build-core-components-from-source)
- [Package a Linux program](#package-a-linux-program)
- [Run on Windows](#run-on-windows)
- [Bridge files deliberately](#bridge-files-deliberately)
- [Completion record](#completion-record)

## Build topology

LiteBox's current workflow has two artifacts:

| Artifact | Build side | Purpose |
| --- | --- | --- |
| Initial filesystem TAR | Linux, or Windows OCI mode | Contains rewritten ELF files, dependencies, and staged data |
| Windows runner EXE | Windows x86-64 | Loads that TAR and executes its Linux entrypoint |

The packager's host-ELF mode remains Linux-only. Its OCI mode works on Windows
x86-64, so a locked-down client with a user-owned Rust toolchain can now build
both artifacts locally without WSL, Docker, a VM, administrator rights, or a
prebuilt EXE. Use a disposable builder only when local compilation is blocked.

## Validated Windows source-only route

The repository includes:

- `../scripts/build-codex-windows.ps1`: pinned, end-to-end Codex example;
- `https://github.com/franklinbaldo/litebox`: maintained fork containing the
  generic `litebox` launcher and the Windows allocator adjustment;
- `../scripts/litebox-tools`: TAR synchronizer only.

The original runner validation used upstream LiteBox commit
`7af6242f0729c1f0224161c7cec0afc114994cf6`. The current recipe pins fork
commit `e8aa71226bc316fcec17bce3a50d82d6224adb78`, which contains that lineage
plus the launcher and Windows allocation work. The remaining validated inputs
are Windows x86-64, Rust
`1.97.1-x86_64-pc-windows-gnullvm`, LLVM-MinGW 20260616, Alpine 3.22.1 at
manifest digest `sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1`,
and Codex 0.147.0. Re-check upstream before updating any pin. Build locally:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File <skill-dir>\scripts\build-codex-windows.ps1
```

The script downloads source/artifacts, verifies published SHA-256 values,
installs and compiles the pinned launcher, runner, rewriter, and packager with
`uv tool install` and static CRT, creates a Linux rootfs TAR, writes
`.litebox/build-record.json`, and probes `codex --version`. Generated EXEs are
local build products; distribute source and let each client compile.

For repeated use, install a pinned fork commit once:

```powershell
uv tool install `
  git+https://github.com/franklinbaldo/litebox@e8aa71226bc316fcec17bce3a50d82d6224adb78
litebox --help
```

Use `uvx` instead when the command should exist only for one invocation:

```powershell
uvx --from `
  git+https://github.com/franklinbaldo/litebox@e8aa71226bc316fcec17bce3a50d82d6224adb78 `
  litebox --help
```

Run any entrypoint through the installed command:

```powershell
litebox run `
  --env HOME=/tmp --env LANG=C.UTF-8 `
  .\.litebox\codex-litebox.tar `
  /usr/local/bin/codex --version
```

Do not use `--forward-env`. Pass only explicit `--env NAME=VALUE` entries.

### Synchronize a Windows folder into the TAR

The runner filesystem is read-only TAR plus an ephemeral in-memory layer; it
does not expose a host mount or write changes back. Before a run, create a new
TAR whose selected subtree mirrors a Windows directory:

```powershell
cargo run --release `
  --manifest-path <skill-dir>\scripts\litebox-tools\Cargo.toml `
  --bin litebox-tar-sync -- `
  --input .\.litebox\codex-litebox.tar `
  --output .\.litebox\codex-workspace.tar `
  --host . `
  --target workspace/project
```

This is deliberate one-way synchronization from Windows to a new TAR. The tool
never overwrites the input TAR. Exclude secrets from the host directory before
syncing. Changes made during LiteBox execution remain in memory and cannot be
recovered unless the application emits them through stdout or another explicit
bridge.

For repeated work, use a restart cycle: synchronize Windows to a new TAR, run
the process, stop it, synchronize again, and restart. The current runner accepts
one `--initial-files` TAR and has no live attach/detach or writable-layer export
API. Multiple TAR layers and host synchronization on detach are plausible
future runner features, not current behavior; do not simulate bidirectional
sync by assuming the in-memory layer was persisted.

### Export changes from inside LiteBox

Bidirectional snapshots are possible at the application layer. Package a Linux
wrapper that launches the workload, watches the chosen directory, creates a TAR
snapshot or delta inside LiteBox, hashes it, and sends it through an explicit
bridge. Use framed base64 on stdout only for small results; keep diagnostics on
stderr. Prefer an authorized HTTPS/object-storage upload for large or periodic
snapshots. A Windows receiver must verify the declared length and SHA-256,
extract to a temporary directory, reject traversal/symlink escapes, and apply
changes only after validation.

This wrapper can export once on clean shutdown or periodically while the
workload runs. It does not create a host mount: LiteBox still cannot see the
Windows directory directly, and Windows must explicitly receive and apply each
snapshot. Validate process spawning, concurrent writes, binary stdout, network
transport, interruption recovery, and conflict policy before calling the bridge
reliable. Never mix an unframed TAR stream with interactive terminal output.

## Build core components from source

Do not clone the repository to install or run the tools. `uv tool install` and
`uvx` fetch and build the launcher, runner, rewriter, and packager automatically.
Clone a pinned source checkout only for LiteBox core development:

```bash
git clone https://github.com/franklinbaldo/litebox.git
cd litebox
git checkout <FULL_COMMIT>
```

On Linux, build the packager:

```bash
cargo build --locked --release -p litebox_packager
```

On Windows x86-64, build the runner:

```powershell
cargo build --locked --release `
  -p litebox_runner_linux_on_windows_userland
```

If local build tools are unavailable, reproduce these commands in temporary CI
jobs. Download artifacts before the job expires and record SHA-256 hashes.
Never put credentials in the workflow, source tree, or artifacts.

## Package a Linux program

For a local ELF on the Linux builder:

```bash
./target/release/litebox-packager \
  /usr/bin/PROGRAM \
  --output program-litebox.tar \
  --verbose
```

The packager invokes `ldd`, adds discovered shared libraries, and rewrites ELF
syscall sites. Add non-ELF runtime data explicitly:

```bash
./target/release/litebox-packager \
  /usr/bin/PROGRAM \
  --include /path/config:/work/config \
  --include /path/input:/work/input \
  --output program-litebox.tar
```

It can also start from a public OCI image:

```bash
./target/release/litebox-packager \
  --oci-image docker.io/OWNER/IMAGE:PINNED_TAG \
  --output program-litebox.tar
```

Inspect the TAR before transfer. Confirm that the ELF loader, every `.so`, CA
certificates, locales, fonts, profiles, Python packages, and application data
required by the chosen entrypoint are present.

## Run on Windows

Confirm the exact entrypoint path inside the TAR, then:

```powershell
litebox run --env "LANG=C.UTF-8" `
  .\program-litebox.tar /usr/bin/PROGRAM --help
```

Use `--env` only for values that are safe to expose in the local process
environment. Avoid `--forward-env`: forwarding the entire Windows environment
can disclose unrelated credentials.

## Bridge files deliberately

The current runner builds an in-memory filesystem from the TAR. Treat it as
ephemeral and do not assume host mounts.

- Text input/output: stdin and stdout.
- Small binary output: emit base64 text and decode it on Windows.
- Large binary input/output: use an authorized HTTPS/object-storage handoff or
  a purpose-built streaming wrapper.
- Immutable input: include it in the TAR, accepting that the Linux packager
  must rebuild that TAR when the input changes.
- Mutable configuration: construct it at process start from runtime values;
  do not bake credentials into the TAR.

Capture stdout and stderr separately when correctness depends on clean output.
Test binary roundtrips by hash before trusting the bridge.

## Completion record

Record:

- LiteBox commit and Rust toolchain;
- program/container version;
- exact package and runner commands;
- SHA-256 for EXE and TAR;
- passing probes;
- input/output bridge;
- domain validation;
- observed incompatibilities.
