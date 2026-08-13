[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runtimeRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $runtimeRoot ".."))
$venvPath = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$expectedFreqtradeVersion = "2026.7"
$expectedFreqUiVersion = "3.1.1"
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
$installedFreqtradeVersion = [string](& $venvPython -c `
    "from importlib.metadata import version; print(version('freqtrade'))")
if ($LASTEXITCODE -ne 0) {
    throw "Freqtrade version could not be resolved."
}
$installedFreqtradeVersion = $installedFreqtradeVersion.Trim()
if ($installedFreqtradeVersion -ne $expectedFreqtradeVersion) {
    throw "Expected Freqtrade $expectedFreqtradeVersion, found $installedFreqtradeVersion."
}

# FreqUI is not part of uv.lock. Pin it separately through Freqtrade's official
# installer and verify its own version marker. Matching installations stay
# offline during normal starts; missing or mismatched files are repaired.
$freqUiDirectory = [string](& $venvPython -c `
    "from pathlib import Path; import freqtrade; print(Path(freqtrade.__file__).resolve().parent / 'rpc' / 'api_server' / 'ui' / 'installed')")
if ($LASTEXITCODE -ne 0) {
    throw "FreqUI installation path could not be resolved."
}
$freqUiDirectory = $freqUiDirectory.Trim()
if ([string]::IsNullOrWhiteSpace($freqUiDirectory)) {
    throw "FreqUI installation path could not be resolved."
}
$freqUiIndex = Join-Path $freqUiDirectory "index.html"
$freqUiVersionPath = Join-Path $freqUiDirectory ".uiversion"
$installedFreqUiVersion = ""
if (Test-Path -LiteralPath $freqUiVersionPath -PathType Leaf) {
    $installedFreqUiVersion = [System.IO.File]::ReadAllText($freqUiVersionPath).Trim()
}
if (
    -not (Test-Path -LiteralPath $freqUiIndex -PathType Leaf) -or
    $installedFreqUiVersion -ne $expectedFreqUiVersion
) {
    Write-Host "Installiere die festgelegte offizielle FreqUI-Version $expectedFreqUiVersion."
    & $freqtradeExe install-ui --ui-version $expectedFreqUiVersion
    if ($LASTEXITCODE -ne 0) {
        throw "FreqUI installation failed with code $LASTEXITCODE."
    }
}
if (-not (Test-Path -LiteralPath $freqUiIndex -PathType Leaf)) {
    throw "FreqUI installation completed without creating the expected frontend: $freqUiIndex"
}
if (-not (Test-Path -LiteralPath $freqUiVersionPath -PathType Leaf)) {
    throw "FreqUI installation completed without a .uiversion marker."
}
$installedFreqUiVersion = [System.IO.File]::ReadAllText($freqUiVersionPath).Trim()
if ($installedFreqUiVersion -ne $expectedFreqUiVersion) {
    throw "Expected FreqUI $expectedFreqUiVersion, found $installedFreqUiVersion."
}

Write-Host "Verified Freqtrade $installedFreqtradeVersion with FreqUI $installedFreqUiVersion."
