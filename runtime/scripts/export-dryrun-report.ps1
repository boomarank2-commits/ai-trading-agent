[CmdletBinding()]
param(
    [Alias("session-start-utc")]
    [string]$SessionStartUtc = "",

    [Alias("session-end-utc")]
    [string]$SessionEndUtc = "",

    [string]$OutputDirectory = "",
    [string]$SessionId = "",
    [string]$DatabasePath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runtimeRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $runtimeRoot ".."))
$userDataPath = [System.IO.Path]::GetFullPath((Join-Path $runtimeRoot "user_data"))
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

# Old supervisors do not know the newer -DatabasePath parameter. When they
# finish, bind their session report to the database already recorded in that
# session's manifest instead of silently switching to the current strategy DB.
if ([string]::IsNullOrWhiteSpace($DatabasePath)) {
    $sessionManifestPath = Join-Path $OutputDirectory "session-manifest.json"
    if (Test-Path -LiteralPath $sessionManifestPath -PathType Leaf) {
        $sessionManifest = Get-Content -LiteralPath $sessionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $DatabasePath = [string]$sessionManifest.database.path
        if ([string]::IsNullOrWhiteSpace($DatabasePath)) {
            throw "Das Sitzungsmanifest enthaelt keinen Datenbankpfad; Bericht wird nicht vermischt."
        }
    }
    else {
        $DatabasePath = Join-Path $userDataPath "tradesv3.paper-trend-breakout-250-v1.sqlite"
    }
}
$DatabasePath = [System.IO.Path]::GetFullPath($DatabasePath)
$userDataPrefix = $userDataPath.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
if (
    -not $DatabasePath.StartsWith($userDataPrefix, [StringComparison]::OrdinalIgnoreCase) -or
    [System.IO.Path]::GetExtension($DatabasePath) -ne ".sqlite"
) {
    throw "Der Berichts-Datenbankpfad muss eine SQLite-Datei innerhalb von runtime/user_data sein."
}

$reportArgs = @(
    $reporterPath,
    "--database", $DatabasePath,
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
