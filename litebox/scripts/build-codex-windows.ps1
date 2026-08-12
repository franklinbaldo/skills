[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path (Get-Location) '.litebox'),
    [switch]$SkipProbe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$LiteBoxCommit = '1870778c9d5a4ddfb0bce91c4d6f63a2c01f798b'
$LiteBoxRepository = 'https://github.com/franklinbaldo/litebox.git'
$CodexVersion = '0.147.0'
$CodexSha256 = '0246e2e773834e07f0fb5249ed6ebad12e4591e608f8c7bb97dd6a9690544c36'
$CodexUrl = "https://github.com/openai/codex/releases/download/rust-v$CodexVersion/codex-x86_64-unknown-linux-musl.tar.gz"
$LlvmVersion = '20260616'
$LlvmSha256 = 'b9b68a4d276e16fa25802aaba458e4638f64b3884c290aaccdc2d87083b6ca35'
$LlvmUrl = "https://github.com/mstorsjo/llvm-mingw/releases/download/$LlvmVersion/llvm-mingw-$LlvmVersion-ucrt-x86_64.zip"
$RustToolchain = '1.97.1-x86_64-pc-windows-gnullvm'
$RootfsImage = 'docker.io/library/alpine@sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1'

$Downloads = Join-Path $OutputDirectory 'downloads'
$LlvmRoot = Join-Path $OutputDirectory "llvm-mingw-$LlvmVersion-ucrt-x86_64"
$LlvmArchive = Join-Path $Downloads "llvm-mingw-$LlvmVersion-ucrt-x86_64.zip"
$CodexArchive = Join-Path $Downloads "codex-$CodexVersion-linux-x64.tar.gz"
$Stage = Join-Path $OutputDirectory 'stage'
$Tar = Join-Path $OutputDirectory 'codex-litebox.tar'

function Invoke-Checked([string]$Command, [string[]]$Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Command" }
}

function Get-Verified([string]$Uri, [string]$Destination, [string]$Sha256) {
    if (Test-Path $Destination) {
        $hash = (Get-FileHash -Algorithm SHA256 $Destination).Hash.ToLowerInvariant()
        if ($hash -ne $Sha256) { Remove-Item -LiteralPath $Destination -Force }
    }
    if (-not (Test-Path $Destination)) { Invoke-WebRequest $Uri -OutFile $Destination }
    $hash = (Get-FileHash -Algorithm SHA256 $Destination).Hash.ToLowerInvariant()
    if ($hash -ne $Sha256) { throw "SHA-256 mismatch for $Destination" }
    $hash
}

if (-not [Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([Runtime.InteropServices.OSPlatform]::Windows) -or
    [Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne 'X64') {
    throw 'Requires Windows x86-64.'
}
foreach ($command in 'rustup', 'tar', 'uv') {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Missing command: $command" }
}
New-Item -ItemType Directory -Force $OutputDirectory, $Downloads | Out-Null

if (-not (Test-Path (Join-Path $LlvmRoot 'bin\dlltool.exe'))) {
    [void](Get-Verified $LlvmUrl $LlvmArchive $LlvmSha256)
    Expand-Archive $LlvmArchive -DestinationPath $OutputDirectory -Force
}
$env:PATH = (Join-Path $LlvmRoot 'bin') + [IO.Path]::PathSeparator + $env:PATH
Invoke-Checked rustup @('toolchain', 'install', $RustToolchain, '--profile', 'minimal')
$previousRustFlags = $env:RUSTFLAGS
$env:RUSTFLAGS = '-C target-feature=+crt-static'
$previousRustupToolchain = $env:RUSTUP_TOOLCHAIN
$previousCargoBuildTarget = $env:CARGO_BUILD_TARGET
$env:RUSTUP_TOOLCHAIN = $RustToolchain
$env:CARGO_BUILD_TARGET = 'x86_64-pc-windows-gnullvm'
Invoke-Checked uv @('tool', 'install', '--force', "git+$LiteBoxRepository@$LiteBoxCommit")
if ($null -eq $previousRustupToolchain) { Remove-Item Env:RUSTUP_TOOLCHAIN } else { $env:RUSTUP_TOOLCHAIN = $previousRustupToolchain }
if ($null -eq $previousCargoBuildTarget) { Remove-Item Env:CARGO_BUILD_TARGET } else { $env:CARGO_BUILD_TARGET = $previousCargoBuildTarget }
if ($null -eq $previousRustFlags) { Remove-Item Env:RUSTFLAGS } else { $env:RUSTFLAGS = $previousRustFlags }
$uvToolBin = (& uv tool dir --bin).Trim()
$Launcher = Join-Path $uvToolBin 'litebox.exe'
$Runner = Join-Path $uvToolBin 'litebox-runner.exe'
$rewriter = Join-Path $uvToolBin 'litebox-rewriter.exe'
$packager = Join-Path $uvToolBin 'litebox-packager.exe'
foreach ($installedTool in $Launcher, $Runner, $rewriter, $packager) {
    if (-not (Test-Path $installedTool)) { throw "uv did not install expected tool: $installedTool" }
}

$codexHash = Get-Verified $CodexUrl $CodexArchive $CodexSha256
if (Test-Path $Stage) {
    $resolvedOutput = [IO.Path]::GetFullPath($OutputDirectory).TrimEnd('\') + '\'
    $resolvedStage = [IO.Path]::GetFullPath($Stage)
    if (-not $resolvedStage.StartsWith($resolvedOutput, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe staging path: $resolvedStage"
    }
    Remove-Item -LiteralPath $resolvedStage -Recurse -Force
}
New-Item -ItemType Directory -Force (Join-Path $Stage 'usr\local\bin') | Out-Null
Invoke-Checked tar @('-xzf', $CodexArchive, '-C', $Stage)
$downloaded = Get-ChildItem $Stage -Recurse -File | Where-Object Name -eq 'codex-x86_64-unknown-linux-musl' | Select-Object -First 1
if ($null -eq $downloaded) {
    throw 'Expected codex-x86_64-unknown-linux-musl not found in the pinned archive.'
}
Invoke-Checked $rewriter @($downloaded.FullName, '--output', (Join-Path $Stage 'usr\local\bin\codex'))
if (Test-Path $Tar) { Remove-Item -LiteralPath $Tar -Force }
Invoke-Checked $packager @('--oci-image', $RootfsImage, '--output', $Tar)
Invoke-Checked tar @('--format', 'ustar', '-rf', $Tar, '-C', $Stage, 'usr/local/bin/codex')

[ordered]@{
    litebox_commit = $LiteBoxCommit
    rust_toolchain = (& rustc "+$RustToolchain" -V)
    rootfs_image = $RootfsImage
    windows_allocator_order = 31
    codex_version = $CodexVersion
    codex_archive_sha256 = $codexHash
    runner_sha256 = (Get-FileHash -Algorithm SHA256 $Runner).Hash.ToLowerInvariant()
    launcher_sha256 = (Get-FileHash -Algorithm SHA256 $Launcher).Hash.ToLowerInvariant()
    initial_files_sha256 = (Get-FileHash -Algorithm SHA256 $Tar).Hash.ToLowerInvariant()
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'build-record.json')

if (-not $SkipProbe) {
    Invoke-Checked $Launcher @('--runner', $Runner, '--initial-files', $Tar, '--env', 'HOME=/tmp', '--env', 'LANG=C.UTF-8', '--program', '/usr/local/bin/codex', '--', '--version')
}
