[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "Stale-Testbot-Pruefung wird nur unter Windows unterstuetzt."
}

function Get-PortOwners {
    return @(
        Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
}

function Get-ProcessInfo {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    return Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
}

function Close-StaleSessionManifests {
    $runtimeRoot = Split-Path -Parent $PSScriptRoot
    $sessionsRoot = Join-Path $runtimeRoot "user_data\logs\sessions"
    if (-not (Test-Path -LiteralPath $sessionsRoot -PathType Container)) {
        return
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    foreach ($manifestPath in Get-ChildItem -LiteralPath $sessionsRoot -Filter "session-manifest.json" -File -Recurse) {
        try {
            $manifest = Get-Content -LiteralPath $manifestPath.FullName -Raw | ConvertFrom-Json
            if (([string]$manifest.status) -notin @("starting", "running")) {
                continue
            }

            $sessionId = [string]$manifest.session_id
            $match = [regex]::Match($sessionId, "-pid-(\d+)$")
            if ($match.Success) {
                $supervisorPid = [int]$match.Groups[1].Value
                if ($null -ne (Get-Process -Id $supervisorPid -ErrorAction SilentlyContinue)) {
                    continue
                }
            }

            $manifest.status = "interrupted"
            $manifest.ended_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
            if ([string]$manifest.report_status -eq "pending") {
                $manifest.report_status = "not_created_for_forced_shutdown"
            }
            $content = ($manifest | ConvertTo-Json -Depth 20) + [Environment]::NewLine
            [System.IO.File]::WriteAllText($manifestPath.FullName, $content, $utf8NoBom)
            Write-Host "STATUS: Unterbrochene alte Sitzung markiert: $sessionId" -ForegroundColor Yellow
        }
        catch {
            throw "Altes Sitzungsmanifest konnte nicht sicher bereinigt werden: $($manifestPath.FullName): $($_.Exception.Message)"
        }
    }
}

$owners = @(Get-PortOwners)
if ($owners.Count -eq 0) {
    Close-StaleSessionManifests
    exit 0
}

$foreign = New-Object System.Collections.Generic.List[string]
$stale = New-Object System.Collections.Generic.List[int]

foreach ($ownerPid in $owners) {
    $info = Get-ProcessInfo -ProcessId $ownerPid
    if ($null -eq $info) {
        $foreign.Add("PID $ownerPid (Prozessdetails nicht lesbar)")
        continue
    }

    $commandLine = [string]$info.CommandLine
    $normalized = $commandLine.ToLowerInvariant()
    $looksLikeThisBot = (
        $normalized.Contains("ai-trading-agent") -and
        (
            $normalized.Contains("locked_freqtrade.py") -or
            $normalized.Contains("freqtrade") -or
            $normalized.Contains("start-testbot-24x7.ps1")
        )
    )

    if ($looksLikeThisBot) {
        $stale.Add([int]$ownerPid)
    }
    else {
        $foreign.Add("PID $ownerPid ($($info.Name))")
    }
}

if ($foreign.Count -gt 0) {
    throw (
        "Port 8080 ist bereits durch ein fremdes Programm belegt: " +
        ($foreign -join ", ") +
        ". Aus Sicherheitsgruenden wird nichts fremdes beendet und der Testbot startet nicht."
    )
}

foreach ($stalePid in $stale) {
    Write-Host "SICHERHEIT: Verwaiste alte Testbot-Instanz erkannt (PID $stalePid). Beende sie jetzt." -ForegroundColor Yellow
    Stop-Process -Id $stalePid -Force -ErrorAction SilentlyContinue
}

$deadline = [DateTimeOffset]::UtcNow.AddSeconds(8)
do {
    Start-Sleep -Milliseconds 250
    $remaining = @(Get-PortOwners)
} while ($remaining.Count -gt 0 -and [DateTimeOffset]::UtcNow -lt $deadline)

if ($remaining.Count -gt 0) {
    throw "Port 8080 ist nach dem Sicherheits-Cleanup weiterhin belegt. Testbot startet nicht."
}

Close-StaleSessionManifests
Write-Host "SICHERHEIT: Alte Testbot-Runtime wurde vollstaendig entfernt; Port 8080 ist frei." -ForegroundColor Green
exit 0
