[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "Dieser Integrationstest muss unter Windows laufen."
}

$supervisorScript = Join-Path $PSScriptRoot "run-testbot-supervised.ps1"
if (-not (Test-Path -LiteralPath $supervisorScript -PathType Leaf)) {
    throw "Supervisor-Skript fehlt: $supervisorScript"
}

$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("testbot-lifetime-" + [Guid]::NewGuid().ToString("N"))
[System.IO.Directory]::CreateDirectory($testRoot) | Out-Null
$childPidPath = Join-Path $testRoot "child.pid"
$heartbeatPath = Join-Path $testRoot "child.heartbeat"
$supervisor = $null
$childPid = $null

try {
    $supervisor = Start-Process powershell.exe -PassThru -WindowStyle Hidden -ArgumentList @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"' + $supervisorScript + '"'),
        "-LifetimeSelfTest",
        "-SelfTestDirectory", ('"' + $testRoot + '"')
    )

    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(15)
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        if ($supervisor.HasExited) {
            throw "Supervisor-Selbsttest wurde vorzeitig mit Code $($supervisor.ExitCode) beendet."
        }
        if (
            (Test-Path -LiteralPath $childPidPath -PathType Leaf) -and
            (Test-Path -LiteralPath $heartbeatPath -PathType Leaf)
        ) {
            break
        }
        Start-Sleep -Milliseconds 200
        $supervisor.Refresh()
    }

    if (-not (Test-Path -LiteralPath $childPidPath -PathType Leaf)) {
        throw "Der Dummy-Child wurde nicht rechtzeitig gestartet."
    }
    $childPid = [int](Get-Content -LiteralPath $childPidPath -Raw -Encoding ASCII).Trim()
    $child = Get-Process -Id $childPid -ErrorAction Stop

    $heartbeatBefore = (Get-Item -LiteralPath $heartbeatPath).LastWriteTimeUtc
    Start-Sleep -Milliseconds 700
    $heartbeatAfter = (Get-Item -LiteralPath $heartbeatPath).LastWriteTimeUtc
    if ($heartbeatAfter -le $heartbeatBefore) {
        throw "Der Dummy-Child war vor dem Supervisor-Abbruch nicht aktiv."
    }

    Write-Host "Erzwinge Supervisor-Abbruch (PID $($supervisor.Id)); Child PID ist $childPid."
    Stop-Process -Id $supervisor.Id -Force -ErrorAction Stop
    $supervisor.WaitForExit(5000) | Out-Null

    $killDeadline = [DateTimeOffset]::UtcNow.AddSeconds(5)
    do {
        $stillAlive = $null -ne (Get-Process -Id $childPid -ErrorAction SilentlyContinue)
        if (-not $stillAlive) {
            break
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTimeOffset]::UtcNow -lt $killDeadline)

    if ($stillAlive) {
        throw "SICHERHEITSFEHLER: Dummy-Child PID $childPid hat den Supervisor ueberlebt."
    }

    Write-Host "PASS: JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE hat den Child-Prozess beim Supervisor-Tod beendet." -ForegroundColor Green
}
finally {
    if ($null -ne $supervisor -and -not $supervisor.HasExited) {
        Stop-Process -Id $supervisor.Id -Force -ErrorAction SilentlyContinue
    }
    if ($null -ne $childPid) {
        Stop-Process -Id $childPid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
