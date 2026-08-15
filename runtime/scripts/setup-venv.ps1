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

# FreqUI is an optional Freqtrade component. Install it only when the local
# frontend is genuinely missing, so normal later starts stay fast and do not
# contact the network just to refresh the UI.
$freqUiIndex = [string](& $venvPython -c "from pathlib import Path; import freqtrade; print(Path(freqtrade.__file__).resolve().parent / 'rpc' / 'api_server' / 'ui' / 'installed' / 'index.html')")
$freqUiIndex = $freqUiIndex.Trim()
if ([string]::IsNullOrWhiteSpace($freqUiIndex)) {
    throw "FreqUI installation path could not be resolved."
}
if (-not (Test-Path -LiteralPath $freqUiIndex -PathType Leaf)) {
    Write-Host "FreqUI fehlt; installiere die offizielle Freqtrade-Weboberflaeche einmalig."
    & $freqtradeExe install-ui
    if ($LASTEXITCODE -ne 0) {
        throw "FreqUI installation failed with code $LASTEXITCODE."
    }
}
if (-not (Test-Path -LiteralPath $freqUiIndex -PathType Leaf)) {
    throw "FreqUI installation completed without creating the expected frontend: $freqUiIndex"
}

# FreqUI itself lives inside .venv and is not tracked in Git. Apply the tiny,
# idempotent repository-owned hook on every setup so a fresh clone gets the
# Backtest navigation automatically and a future FreqUI reinstall is repaired.
$patchFreqUi = Join-Path $runtimeRoot "patch_frequi.py"
if (-not (Test-Path -LiteralPath $patchFreqUi -PathType Leaf)) {
    throw "Testbot FreqUI patcher is missing: $patchFreqUi"
}
& $venvPython $patchFreqUi
if ($LASTEXITCODE -ne 0) {
    throw "Installing the Testbot Backtest UI hook failed with code $LASTEXITCODE."
}
