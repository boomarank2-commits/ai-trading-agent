[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runtimeRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $runtimeRoot ".."))
$venvPath = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$uvCommand = Get-Command "uv" -ErrorAction SilentlyContinue
if ($null -eq $uvCommand) {
    throw "uv is required to install the exact locked environment. Install uv, then run this script again."
}

Push-Location -LiteralPath $repoRoot
try {
    # uv creates .venv when missing and can provision the requested Python.
    # This avoids silently using an arbitrary `py -3` interpreter on a fresh PC.
    & $uvCommand.Source sync --frozen --all-extras --python 3.12
    if ($LASTEXITCODE -ne 0) {
        throw "Synchronizing the frozen project environment failed with code $LASTEXITCODE."
    }
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw "uv completed without creating the expected environment: $venvPython"
    }
    & $uvCommand.Source sync --check --frozen --all-extras --python $venvPython
    if ($LASTEXITCODE -ne 0) {
        throw "The installed environment does not match uv.lock."
    }
}
finally {
    Pop-Location
}

$freqtradeExe = Join-Path $venvPath "Scripts\freqtrade.exe"
& $freqtradeExe --version
if ($LASTEXITCODE -ne 0) {
    throw "Freqtrade installation verification failed with code $LASTEXITCODE."
}
