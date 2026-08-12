[CmdletBinding()]
param(
    [Alias("session-start-utc")]
    [string]$SessionStartUtc = "",

    [Alias("session-end-utc")]
    [string]$SessionEndUtc = "",

    [string]$OutputDirectory = "",
    [string]$SessionId = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runtimeRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $runtimeRoot ".."))
$databasePath = Join-Path $runtimeRoot "user_data\tradesv3.dryrun.sqlite"
$reporterPath = Join-Path $runtimeRoot "export_dryrun_report.py"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $reporterPath -PathType Leaf)) {
    throw "Dry-run reporter not found: $reporterPath"
}

if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $pythonCommand = $venvPython
    $pythonPrefixArgs = @()
}
else {
    throw "Die gesperrte lokale Python-Umgebung fehlt. Zuerst STARTBOT.bat ausfuehren."
}

$generatedAt = [DateTimeOffset]::UtcNow
if ([string]::IsNullOrWhiteSpace($SessionId)) {
    $SessionId = "manual-$($generatedAt.ToString('yyyyMMddTHHmmssfffZ'))-pid-$PID"
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $runtimeRoot "user_data\logs\reports"
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)

$reportArgs = @(
    $reporterPath,
    "--database", $databasePath,
    "--output-dir", $OutputDirectory,
    "--starting-wallet", "250",
    "--session-id", $SessionId
)
if (-not [string]::IsNullOrWhiteSpace($SessionStartUtc)) {
    $reportArgs += @("--session-start-utc", $SessionStartUtc)
}
if (-not [string]::IsNullOrWhiteSpace($SessionEndUtc)) {
    $reportArgs += @("--session-end-utc", $SessionEndUtc)
}

$rawResult = @(& $pythonCommand @pythonPrefixArgs @reportArgs)
if ($LASTEXITCODE -ne 0) {
    throw "Dry-run reporter exited with code $LASTEXITCODE"
}
if ($rawResult.Count -eq 0) {
    throw "Dry-run reporter returned no result"
}

$result = ([string]$rawResult[-1]) | ConvertFrom-Json
Write-Host ""
Write-Host "Testbot-Auswertung erstellt (ausschliesslich simulierte Trades)."
Write-Host "  JSON             : $($result.json_report)"
Write-Host "  Lesbarer Bericht : $($result.markdown_report)"
Write-Host "  Datenbankstatus  : $($result.database_status)"
