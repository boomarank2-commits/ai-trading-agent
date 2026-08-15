[CmdletBinding()]
param(
    [switch]$LifetimeSelfTest,
    [string]$SelfTestDirectory = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "Der Testbot-Supervisor wird nur unter Windows unterstuetzt."
}

# Keep this job handle alive for the complete lifetime of this PowerShell
# process. Windows closes all process handles when this supervisor exits - even
# after a forced console close or taskkill. JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
# then terminates every process in the job, including Freqtrade/Python children.
#
# IMPORTANT: Do not CloseHandle/Dispose this handle during normal script cleanup.
# The operating system must be the component that closes the last handle when
# the visible supervisor process actually dies.
if ($null -eq ("DaviddTechBotLifetimeJob" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;

public static class DaviddTechBotLifetimeJob
{
    private const int JobObjectExtendedLimitInformation = 9;
    private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;

    [StructLayout(LayoutKind.Sequential)]
    private struct JOBOBJECT_BASIC_LIMIT_INFORMATION
    {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct IO_COUNTERS
    {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetInformationJobObject(
        IntPtr hJob,
        int JobObjectInfoClass,
        IntPtr lpJobObjectInfo,
        uint cbJobObjectInfoLength);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

    public static IntPtr CreateKillOnCloseForCurrentProcess()
    {
        IntPtr job = CreateJobObject(IntPtr.Zero, null);
        if (job == IntPtr.Zero)
        {
            throw new Win32Exception(Marshal.GetLastWin32Error(), "CreateJobObject failed");
        }

        JOBOBJECT_EXTENDED_LIMIT_INFORMATION info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        int length = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
        IntPtr buffer = Marshal.AllocHGlobal(length);
        try
        {
            Marshal.StructureToPtr(info, buffer, false);
            if (!SetInformationJobObject(job, JobObjectExtendedLimitInformation, buffer, (uint)length))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "SetInformationJobObject failed");
            }
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }

        Process current = Process.GetCurrentProcess();
        if (!AssignProcessToJobObject(job, current.Handle))
        {
            int error = Marshal.GetLastWin32Error();
            throw new Win32Exception(
                error,
                "AssignProcessToJobObject failed. The bot will not start without a working fail-closed lifetime boundary.");
        }

        return job;
    }
}
"@
}

function Find-TestbotBrowser {
    $candidates = New-Object System.Collections.Generic.List[string]
    $edgeCommand = Get-Command msedge.exe -ErrorAction SilentlyContinue
    if ($null -ne $edgeCommand) {
        $candidates.Add($edgeCommand.Source)
    }
    $chromeCommand = Get-Command chrome.exe -ErrorAction SilentlyContinue
    if ($null -ne $chromeCommand) {
        $candidates.Add($chromeCommand.Source)
    }

    foreach ($root in @(
        ${env:ProgramFiles(x86)},
        $env:ProgramFiles,
        $env:LOCALAPPDATA
    )) {
        if ([string]::IsNullOrWhiteSpace($root)) {
            continue
        }
        $candidates.Add((Join-Path $root "Microsoft\Edge\Application\msedge.exe"))
        $candidates.Add((Join-Path $root "Google\Chrome\Application\chrome.exe"))
    }

    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }
    return $null
}

$script:LifetimeJobHandle = [DaviddTechBotLifetimeJob]::CreateKillOnCloseForCurrentProcess()
if ($script:LifetimeJobHandle -eq [IntPtr]::Zero) {
    throw "Der Windows-Lebenszeitschutz konnte nicht aktiviert werden."
}

Write-Host "SICHERHEIT: Bot-Prozessbaum ist an dieses STARTBOT-Fenster gebunden." -ForegroundColor Green
Write-Host "Wird dieses Fenster geschlossen oder der Supervisor beendet, beendet Windows auch den Bot." -ForegroundColor Green
Write-Host ""

if ($LifetimeSelfTest) {
    if ([string]::IsNullOrWhiteSpace($SelfTestDirectory)) {
        throw "SelfTestDirectory ist fuer den Lebenszeit-Selbsttest erforderlich."
    }
    $directory = [System.IO.Path]::GetFullPath($SelfTestDirectory)
    [System.IO.Directory]::CreateDirectory($directory) | Out-Null
    $childPidPath = Join-Path $directory "child.pid"
    $heartbeatPath = Join-Path $directory "child.heartbeat"
    Remove-Item -LiteralPath $childPidPath, $heartbeatPath -Force -ErrorAction SilentlyContinue

    $childPidLiteral = $childPidPath.Replace("'", "''")
    $heartbeatLiteral = $heartbeatPath.Replace("'", "''")
    $childCommand = @"
Set-Content -LiteralPath '$childPidLiteral' -Value `$PID -Encoding ASCII
while (`$true) {
    Set-Content -LiteralPath '$heartbeatLiteral' -Value ([DateTimeOffset]::UtcNow.ToString('o')) -Encoding ASCII
    Start-Sleep -Milliseconds 200
}
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($childCommand))
    $child = Start-Process powershell.exe -PassThru -WindowStyle Hidden -ArgumentList @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", $encoded
    )
    Write-Host "Lifetime-Selbsttest aktiv. Child PID: $($child.Id)"
    while (-not $child.HasExited) {
        Start-Sleep -Milliseconds 250
        $child.Refresh()
    }
    exit $child.ExitCode
}

$browserExe = Find-TestbotBrowser
if ([string]::IsNullOrWhiteSpace($browserExe)) {
    throw "Kein unterstuetzter lokaler Browser gefunden. Fuer den sicheren UI-Lebenszeitschutz wird Microsoft Edge oder Google Chrome benoetigt."
}

$localApplicationData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
if ([string]::IsNullOrWhiteSpace($localApplicationData)) {
    throw "Der lokale Windows-Anwendungsdatenordner konnte nicht ermittelt werden."
}
$browserProfile = Join-Path $localApplicationData "DaviddTech\AiTradingAgent\browser-profile"
[System.IO.Directory]::CreateDirectory($browserProfile) | Out-Null
$browserProcessName = [System.IO.Path]::GetFileName($browserExe)

Write-Host "UI-Lebenszeitschutz: $browserProcessName wird als eigene Testbot-App ueberwacht." -ForegroundColor Green
Write-Host "Wird das Testbot-UI-Fenster geschlossen, wird auch der Bot beendet." -ForegroundColor Green
Write-Host ""

# The helper waits for the API, launches a dedicated app-mode browser instance
# with its own profile, and monitors exactly that profile. If the UI disappears,
# it force-terminates this supervisor. Closing the supervisor closes the Job
# Object, which then kills the entire bot process tree fail-closed.
$browserExeLiteral = $browserExe.Replace("'", "''")
$browserProfileLiteral = $browserProfile.Replace("'", "''")
$browserProcessNameLiteral = $browserProcessName.Replace("'", "''")
$supervisorPid = $PID
$browserHelperCommand = @"
`$ErrorActionPreference = 'Stop'
`$url = 'http://127.0.0.1:8080'
`$ping = `$url + '/api/v1/ping'
`$browserExe = '$browserExeLiteral'
`$profile = '$browserProfileLiteral'
`$browserName = '$browserProcessNameLiteral'
`$supervisorPid = $supervisorPid

for (`$i = 0; `$i -lt 180; `$i++) {
    if (`$null -eq (Get-Process -Id `$supervisorPid -ErrorAction SilentlyContinue)) { exit 0 }
    try {
        `$response = Invoke-RestMethod -Uri `$ping -TimeoutSec 2
        if (`$response.status -eq 'pong') { break }
    }
    catch {
    }
    Start-Sleep -Seconds 1
}

try {
    `$response = Invoke-RestMethod -Uri `$ping -TimeoutSec 2
    if (`$response.status -ne 'pong') { throw 'API ist nicht bereit.' }
}
catch {
    Stop-Process -Id `$supervisorPid -Force -ErrorAction SilentlyContinue
    exit 2
}

Start-Process -FilePath `$browserExe -ArgumentList @(
    ('--app=' + `$url),
    ('--user-data-dir=' + `$profile),
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-mode'
) | Out-Null

`$seen = `$false
`$startupDeadline = [DateTimeOffset]::UtcNow.AddSeconds(20)
while ([DateTimeOffset]::UtcNow -lt `$startupDeadline) {
    if (`$null -eq (Get-Process -Id `$supervisorPid -ErrorAction SilentlyContinue)) { exit 0 }
    `$instances = @(
        Get-CimInstance Win32_Process -Filter ("Name='" + `$browserName + "'") -ErrorAction SilentlyContinue |
            Where-Object { `$_.CommandLine -and `$_.CommandLine.Contains(`$profile) }
    )
    if (`$instances.Count -gt 0) {
        `$seen = `$true
        break
    }
    Start-Sleep -Milliseconds 250
}

if (-not `$seen) {
    Stop-Process -Id `$supervisorPid -Force -ErrorAction SilentlyContinue
    exit 3
}

while (`$true) {
    if (`$null -eq (Get-Process -Id `$supervisorPid -ErrorAction SilentlyContinue)) { exit 0 }
    `$instances = @(
        Get-CimInstance Win32_Process -Filter ("Name='" + `$browserName + "'") -ErrorAction SilentlyContinue |
            Where-Object { `$_.CommandLine -and `$_.CommandLine.Contains(`$profile) }
    )
    if (`$instances.Count -eq 0) {
        Stop-Process -Id `$supervisorPid -Force -ErrorAction SilentlyContinue
        exit 0
    }
    Start-Sleep -Milliseconds 500
}
"@
$browserHelperEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($browserHelperCommand))
[void](Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-NoLogo",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-EncodedCommand", $browserHelperEncoded
))

$launcher = Join-Path $PSScriptRoot "start-testbot-24x7.ps1"
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "Testbot-Launcher fehlt: $launcher"
}

# Run in this supervisor process so that all subsequently created Python/
# Freqtrade processes automatically inherit the Windows Job Object membership.
# Normal Ctrl+C continues to use the launcher's existing graceful cleanup and
# report path. A forced window/UI close is fail-closed: no bot child may survive.
& $launcher
exit $LASTEXITCODE
