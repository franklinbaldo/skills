param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [string]$OutputPrefix,

    [string]$Session = "opf-anonymization",

    [string]$Gpu = "T4",

    [switch]$DriveCache
)

$ErrorActionPreference = "Stop"

$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
$extension = [IO.Path]::GetExtension($resolvedInput).ToLowerInvariant()
if ($extension -notin @(".md", ".txt")) {
    throw "Input must be Markdown or plain text."
}

$inputName = [IO.Path]::GetFileName($resolvedInput)
$inputStem = [IO.Path]::GetFileNameWithoutExtension($resolvedInput)
if (-not $OutputPrefix) {
    $OutputPrefix = Join-Path (Get-Location) $inputStem
}

$skillRoot = Split-Path -Parent $PSScriptRoot
$skillsRoot = Split-Path -Parent $skillRoot
$colabLauncher = Join-Path $skillsRoot "free-gpu\scripts\colab_windows.py"
$setupScript = Join-Path $PSScriptRoot "setup_colab_opf.py"
$opfScript = Join-Path $PSScriptRoot "anonimizar_opf.py"

foreach ($requiredPath in @($colabLauncher, $setupScript, $opfScript)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required script not found: $requiredPath"
    }
}

$outputDirectory = Split-Path -Parent $OutputPrefix
if ($outputDirectory) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$localOutputs = @(
    "$OutputPrefix.tagged.md",
    "$OutputPrefix.anon.md",
    "$OutputPrefix.opf-report.json",
    "$OutputPrefix.execution.ipynb"
)
foreach ($localOutput in $localOutputs) {
    if (Test-Path -LiteralPath $localOutput) {
        throw "Refusing to overwrite existing output: $localOutput"
    }
}

function Invoke-Colab {
    & uv run --no-project --with google-colab-cli python `
        $colabLauncher @args
    if ($LASTEXITCODE -ne 0) {
        throw "Colab CLI failed with exit code $LASTEXITCODE."
    }
}

$sessionStarted = $false
try {
    Invoke-Colab new -s $Session --gpu $Gpu
    $sessionStarted = $true

    if ($DriveCache) {
        Invoke-Colab drivemount -s $Session
    }

    Invoke-Colab exec -s $Session -f $setupScript --timeout 1200
    Invoke-Colab restart-kernel -s $Session
    Invoke-Colab upload -s $Session $resolvedInput "/content/input/$inputName"
    Invoke-Colab exec -s $Session -f $opfScript --timeout 3600
    Invoke-Colab download -s $Session `
        "/content/output/$inputStem.tagged.md" "$OutputPrefix.tagged.md"
    Invoke-Colab download -s $Session `
        "/content/output/$inputStem.anon.md" "$OutputPrefix.anon.md"
    Invoke-Colab download -s $Session `
        "/content/output/$inputStem.opf-report.json" `
        "$OutputPrefix.opf-report.json"
    Invoke-Colab log -s $Session -o "$OutputPrefix.execution.ipynb"
}
finally {
    if ($sessionStarted) {
        try {
            Invoke-Colab stop -s $Session
        }
        catch {
            Write-Warning "Could not stop Colab session '$Session': $_"
        }
    }
}

Write-Output "Tagged review copy: $OutputPrefix.tagged.md"
Write-Output "Anonymized copy: $OutputPrefix.anon.md"
Write-Output "Redaction report: $OutputPrefix.opf-report.json"
