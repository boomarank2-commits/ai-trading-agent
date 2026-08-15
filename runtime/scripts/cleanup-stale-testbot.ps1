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

$owners = @(Get-PortOwners)
if ($owners.Count -eq 0) {
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

Write-Host "SICHERHEIT: Alte Testbot-Runtime wurde vollstaendig entfernt; Port 8080 ist frei." -ForegroundColor Green
exit 0
