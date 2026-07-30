# Windows userland workflow

Use this reference when carrying a particular Linux ELF into Windows. Verify
the live LiteBox CLI before execution: the project is pre-release and these
interfaces can change.

## Two build environments

LiteBox's current workflow has two artifacts:

| Artifact | Build side | Purpose |
| --- | --- | --- |
| Initial filesystem TAR | Linux | Contains rewritten ELF files, dependencies, and staged data |
| Windows runner EXE | Windows x86-64 | Loads that TAR and executes its Linux entrypoint |

This split is the bootstrap answer when the target Windows machine has neither
WSL nor administrator access: build the TAR in an authorized disposable Linux
environment and the EXE in an authorized Windows CI environment, then download
the artifacts into the user's workspace.

## Pin and build LiteBox

Use the same pinned commit on both builders:

```bash
git clone https://github.com/microsoft/litebox.git
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
.\litebox_runner_linux_on_windows_userland.exe `
  --initial-files .\program-litebox.tar `
  --env "LANG=C.UTF-8" `
  /usr/bin/PROGRAM --help
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
