[CmdletBinding(DefaultParameterSetName = "Once")]
param(
    [Parameter(ParameterSetName = "Once")]
    [switch]$Once,

    [Parameter(ParameterSetName = "Daemon")]
    [switch]$Daemon,

    [Parameter(ParameterSetName = "Status")]
    [switch]$Status,

    [string]$Role = "quant",
    [string]$ConfigPath
)

$ErrorActionPreference = "Stop"
$researchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $researchRoot ".."))
if (-not $ConfigPath) {
    $ConfigPath = Join-Path $researchRoot "desk.json"
}
$ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
$statePath = Join-Path $researchRoot "state.json"
$lockPath = Join-Path $researchRoot "desk.lock"
$inboxPath = Join-Path $researchRoot "inbox"
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) "daviddtech-local-research"

function Read-DeskConfig {
    $config = Get-Content -Raw -Encoding UTF8 -LiteralPath $ConfigPath | ConvertFrom-Json
    if ($config.schema_version -ne 1) {
        throw "Unsupported desk config schema: $($config.schema_version)"
    }
    if ([int]$config.max_cycle_minutes -lt 5 -or [int]$config.max_cycle_minutes -gt 120) {
        throw "max_cycle_minutes must be between 5 and 120."
    }
    if ([int64]$config.max_output_bytes -lt 1024 -or [int64]$config.max_output_bytes -gt 10485760) {
        throw "max_output_bytes must be between 1024 and 10485760."
    }
    $cutoff = [DateTimeOffset]::Parse([string]$config.holdout_cutoff_utc)
    if ($cutoff.Offset -ne [TimeSpan]::Zero) {
        throw "holdout_cutoff_utc must include the UTC timezone."
    }
    return $config
}

function Read-DeskState {
    if (-not (Test-Path -LiteralPath $statePath)) {
        return @{}
    }
    $data = Get-Content -Raw -Encoding UTF8 -LiteralPath $statePath | ConvertFrom-Json
    $result = @{}
    if ($null -ne $data) {
        $data.PSObject.Properties | ForEach-Object {
            $result[$_.Name] = $_.Value
        }
    }
    return $result
}

function Write-DeskState([hashtable]$State) {
    $temporary = "$statePath.tmp"
    $State | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 -LiteralPath $temporary
    Move-Item -Force -LiteralPath $temporary -Destination $statePath
}

function Resolve-Role($Config, [string]$Name) {
    $match = @($Config.roles | Where-Object { $_.name -eq $Name })
    if ($match.Count -ne 1) {
        throw "Unknown or duplicate role '$Name'."
    }
    return $match[0]
}

function Clear-ResearchEnvironment {
    # The child receives only operating-system paths needed to start Codex.
    # Exchange, cloud, CI and API credential variables are removed generically
    # instead of trying to maintain an incomplete secret-name denylist.
    $allowed = @(
        "ALLUSERSPROFILE", "APPDATA", "CODEX_HOME", "COMSPEC",
        "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "NUMBER_OF_PROCESSORS",
        "OS", "PATH", "PATHEXT", "PROCESSOR_ARCHITECTURE", "PROGRAMDATA",
        "PROGRAMFILES", "PROGRAMFILES(X86)", "SYSTEMDRIVE", "SYSTEMROOT",
        "TEMP", "TMP", "USERDOMAIN", "USERNAME", "USERPROFILE", "WINDIR"
    )
    Get-ChildItem Env: | Where-Object { $_.Name -notin $allowed } | ForEach-Object {
        Remove-Item -ErrorAction SilentlyContinue -LiteralPath "Env:$($_.Name)"
    }
}

function New-IsolatedWorkspace($Config, $RoleConfig, [string]$Stamp) {
    $workspaceName = "$Stamp-$($RoleConfig.name)-$PID-$([guid]::NewGuid().ToString('N'))"
    $workspace = [System.IO.Path]::GetFullPath((Join-Path $temporaryRoot $workspaceName))
    $temporaryPrefix = [System.IO.Path]::GetFullPath($temporaryRoot).TrimEnd("\", "/") + "\"
    if (-not $workspace.StartsWith($temporaryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Temporary research workspace escaped its root."
    }

    $strategyPath = Join-Path $workspace "runtime\user_data\strategies"
    $dataPath = Join-Path $workspace "runtime\user_data\data"
    $outputPath = Join-Path $workspace "output\candidates"
    New-Item -ItemType Directory -Force -Path $strategyPath, $dataPath, $outputPath | Out-Null

    Copy-Item -LiteralPath (Join-Path $repoRoot $RoleConfig.file) -Destination (Join-Path $workspace "role.md")
    Copy-Item -LiteralPath (Join-Path $repoRoot "AGENTS.md") -Destination (Join-Path $workspace "AGENTS.md")
    Copy-Item -LiteralPath (Join-Path $repoRoot "local-prompts\research-cycle.md") -Destination (Join-Path $workspace "research-cycle.md")
    Copy-Item -LiteralPath (Join-Path $repoRoot "local-prompts\candidate-contract.md") -Destination (Join-Path $workspace "candidate-contract.md")
    Copy-Item -LiteralPath (Join-Path $repoRoot "runtime\user_data\strategies\CompressionBreakout250.py") -Destination $strategyPath
    Copy-Item -LiteralPath (Join-Path $repoRoot "runtime\user_data\config.json") -Destination (Join-Path $workspace "runtime\user_data\config.json")
    Copy-Item -LiteralPath (Join-Path $repoRoot "runtime\user_data\config-public.json") -Destination (Join-Path $workspace "runtime\user_data\config-public.json")

    $registrySnapshot = Join-Path $workspace "registry-snapshot.json"
    $registryDatabase = Join-Path $repoRoot "research\registry\strategies.sqlite3"
    $registryPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    $marketData = Join-Path $repoRoot "runtime\user_data\data\binance"
    $dataStager = Join-Path $researchRoot "stage_market_data.py"
    if (-not (Test-Path -LiteralPath $marketData -PathType Container)) {
        throw "Public market data is missing. Run runtime\scripts\download-data.ps1 first."
    }
    & $registryPython $dataStager `
        --source $marketData `
        --destination $dataPath `
        --holdout-cutoff-utc ([string]$Config.holdout_cutoff_utc) | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the pre-holdout market-data staging copy."
    }

    if ((Test-Path -LiteralPath $registryDatabase -PathType Leaf) -and (Test-Path -LiteralPath $registryPython -PathType Leaf)) {
        & $registryPython -m local_trader --db $registryDatabase list | Set-Content -Encoding UTF8 -LiteralPath $registrySnapshot
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create the read-only registry snapshot."
        }
    }
    else {
        '{"ok":true,"strategies":[]}' | Set-Content -Encoding UTF8 -LiteralPath $registrySnapshot
    }
    return $workspace
}

function Invoke-ResearchCycle($RoleConfig) {
    $roleFile = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $RoleConfig.file))
    $repoPrefix = $repoRoot.TrimEnd("\", "/") + "\"
    if (-not $roleFile.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Role path escapes the repository."
    }
    if (-not (Test-Path -LiteralPath $roleFile -PathType Leaf)) {
        throw "Role file not found: $roleFile"
    }

    $codex = Get-Command "codex.cmd" -ErrorAction Stop
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $workspace = New-IsolatedWorkspace $config $RoleConfig $stamp
    $workspaceOutput = Join-Path $workspace "output"
    $report = Join-Path $workspaceOutput "report.md"
    $freqtrade = Join-Path $repoRoot ".venv\Scripts\freqtrade.exe"
    $collector = Join-Path $researchRoot "collect_output.py"
    $registryPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

    Clear-ResearchEnvironment
    $prompt = @"
Run exactly one OFFLINE research cycle for the local AI trading desk.

Read role.md, research-cycle.md, candidate-contract.md, AGENTS.md, and
registry-snapshot.json completely before acting.

The external runner must provide OS-level isolation; this is only its staged workspace. Write only below output/. Put at most
one new candidate pair below output/candidates/. Do not access or modify the original repository,
registry, live overlay, home directory, or credentials. Do not start dry-run or live trading. Do
not place orders or promote any lifecycle. The available deterministic executable is $freqtrade.
Use only the copied pre-holdout public OHLCV data and copied configs. The host must make all other
data physically unreadable. The holdout begins at $($config.holdout_cutoff_utc) UTC and is omitted
from staging. Never try to locate, infer, request,
or access it. Change one major idea, persist failures
honestly, and finish with a structured report including exact commands, artifact hash,
assumptions, metrics, weaknesses, verdict, and the next single experiment.
"@

    Write-Host "Starting isolated offline role '$($RoleConfig.name)'. Workspace: $workspace"
    $promptPath = Join-Path $workspace "research-prompt.txt"
    $stdoutPath = Join-Path $workspace "codex.stdout.tmp"
    $stderrPath = Join-Path $workspace "codex.stderr.tmp"
    $prompt | Set-Content -Encoding UTF8 -LiteralPath $promptPath
    $codexArguments = @(
        "exec",
        "--cd", "`"$workspace`"",
        "--sandbox", "workspace-write",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--color", "never",
        "--output-last-message", "`"$report`"",
        "-"
    )
    $process = Start-Process `
        -FilePath $codex.Source `
        -ArgumentList $codexArguments `
        -RedirectStandardInput $promptPath `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -WindowStyle Hidden `
        -PassThru
    $deadline = (Get-Date).AddMinutes([int]$config.max_cycle_minutes)
    while (-not $process.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 1
        $process.Refresh()
    }
    if (-not $process.HasExited) {
        & taskkill.exe /PID $process.Id /T /F | Out-Null
        throw "Research cycle exceeded $($config.max_cycle_minutes) minutes. Workspace retained: $workspace"
    }
    if ($process.ExitCode -ne 0) {
        $diagnostic = Get-Content -Tail 20 -ErrorAction SilentlyContinue -LiteralPath $stderrPath
        Write-Warning ($diagnostic -join [Environment]::NewLine)
        throw "Research cycle failed with exit code $($process.ExitCode). Workspace retained: $workspace"
    }

    $destination = Join-Path $inboxPath "$stamp-$($RoleConfig.name)"
    New-Item -ItemType Directory -Force -Path $inboxPath | Out-Null
    & $registryPython $collector `
        --source $workspaceOutput `
        --destination $destination `
        --maximum-bytes ([int64]$config.max_output_bytes) `
        --cleanup-root $workspace `
        --cleanup-parent $temporaryRoot | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Research output validation failed. Workspace retained: $workspace"
    }
    Write-Host "Staged result for human review: $destination"
    return (Join-Path $destination "report.md")
}

function Acquire-DeskLock {
    try {
        $script:deskLockStream = [System.IO.File]::Open(
            $lockPath,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    }
    catch {
        throw "Research desk is already running; could not acquire $lockPath"
    }
    $pidBytes = [System.Text.Encoding]::ASCII.GetBytes([string]$PID)
    $script:deskLockStream.SetLength(0)
    $script:deskLockStream.Write($pidBytes, 0, $pidBytes.Length)
    $script:deskLockStream.Flush($true)
}

$config = Read-DeskConfig
if ($Status) {
    $state = Read-DeskState
    $config.roles | ForEach-Object {
        [pscustomobject]@{
            Name = $_.name
            Enabled = $_.enabled
            IntervalMinutes = $_.interval_minutes
            LastRunUtc = $state[$_.name]
        }
    } | Format-Table -AutoSize
    exit 0
}

# Hard fail-closed boundary.  Codex workspace-write limits writes, not reads,
# and a same-user Windows process can still inspect the real repository/home.
# Do not replace this with a flag: execution belongs in a separately
# provisioned low-privilege account, VM, or container that mounts only the
# staged inputs and a host-controlled result channel.
throw "AUTONOMOUS_RESEARCH_DISABLED: run -Status only. Use a separate low-privilege VM/container before enabling cycles."

Acquire-DeskLock
try {
    if (-not $Daemon) {
        $selected = Resolve-Role $config $Role
        Invoke-ResearchCycle $selected | Out-Null
        exit 0
    }

    Write-Host "Offline research desk running. Press Ctrl+C to stop. No live orders are permitted."
    while ($true) {
        $state = Read-DeskState
        $now = (Get-Date).ToUniversalTime()
        $due = @($config.roles | Where-Object {
            if (-not $_.enabled) { return $false }
            $lastText = $state[$_.name]
            if (-not $lastText) { return $true }
            $last = [DateTime]::Parse($lastText).ToUniversalTime()
            return $now -ge $last.AddMinutes([double]$_.interval_minutes)
        } | Select-Object -First 1)

        if ($due.Count -eq 1) {
            try {
                Invoke-ResearchCycle $due[0] | Out-Null
            }
            catch {
                Write-Warning "Role '$($due[0].name)' failed: $($_.Exception.Message)"
            }
            finally {
                $state[$due[0].name] = (Get-Date).ToUniversalTime().ToString("o")
                Write-DeskState $state
            }
        }
        Start-Sleep -Seconds ([int]$config.poll_seconds)
    }
}
finally {
    if ($null -ne $script:deskLockStream) {
        $script:deskLockStream.Dispose()
    }
    if (Test-Path -LiteralPath $lockPath -PathType Leaf) {
        Remove-Item -Force -LiteralPath $lockPath
    }
}
