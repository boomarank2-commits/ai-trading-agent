[CmdletBinding()]
param(
    [string]$Database
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUTF8 = "1"
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
if ([string]::IsNullOrWhiteSpace($Database)) {
    $Database = Join-Path $repoRoot "research\registry\strategies.sqlite3"
}
$databasePath = [System.IO.Path]::GetFullPath($Database)
$candidateRoot = Join-Path $repoRoot "runtime\user_data\strategies\candidates"
$promotedRoot = Join-Path $repoRoot "runtime\user_data\strategies\promoted"

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Python environment not found at '$pythonPath'. Run runtime\scripts\setup-venv.ps1 first."
}
if (Test-Path -LiteralPath $databasePath) {
    throw "Refusing to overwrite existing registry: $databasePath"
}

& $pythonPath -m local_trader --db $databasePath init `
    --candidate-root $candidateRoot `
    --promoted-root $promotedRoot
if ($LASTEXITCODE -ne 0) {
    throw "Registry initialization failed with exit code $LASTEXITCODE"
}
