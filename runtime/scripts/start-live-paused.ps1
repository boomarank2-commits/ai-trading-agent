[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z_][A-Za-z0-9_]*$')]
    [string]$Strategy,

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2147483647)]
    [int]$Version,

    [ValidateSet("CANARY", "PRODUCTION")]
    [string]$Target = "CANARY",

    [string]$Database
)

. (Join-Path $PSScriptRoot "_common.ps1")

$allowedFreqtradeVariables = @(
    "FREQTRADE__EXCHANGE__KEY",
    "FREQTRADE__EXCHANGE__SECRET"
)
Assert-NoFreqtradeOverrides -Allowed $allowedFreqtradeVariables

$apiKey = [Environment]::GetEnvironmentVariable(
    "FREQTRADE__EXCHANGE__KEY",
    [EnvironmentVariableTarget]::Process
)
$apiSecret = [Environment]::GetEnvironmentVariable(
    "FREQTRADE__EXCHANGE__SECRET",
    [EnvironmentVariableTarget]::Process
)
if ([string]::IsNullOrWhiteSpace($apiKey) -or [string]::IsNullOrWhiteSpace($apiSecret)) {
    throw "Set FREQTRADE__EXCHANGE__KEY and FREQTRADE__EXCHANGE__SECRET in this process first."
}

if ([string]::IsNullOrWhiteSpace($Database)) {
    $Database = Join-Path $script:RepoRoot "research\registry\strategies.sqlite3"
}
$databasePath = [System.IO.Path]::GetFullPath($Database)
$python = Join-Path $script:VenvPath "Scripts\python.exe"
$validator = Join-Path $script:RuntimeRoot "validate_runtime.py"
$lockedRunner = Join-Path $script:RuntimeRoot "locked_freqtrade.py"
$lockPath = Join-Path $script:RepoRoot "uv.lock"
$trustedArtifactsPath = Join-Path $script:RuntimeRoot "trusted-live-artifacts.json"
$killSwitchPath = Join-Path $script:UserDataPath "STOP_ENTRIES"
$instanceLockPath = Join-Path $script:UserDataPath "live-instance.lock"
$effectiveConfig = Join-Path $script:UserDataPath (
    ".effective-live-$([guid]::NewGuid().ToString('N')).json"
)

foreach ($requiredFile in @(
    $databasePath,
    $python,
    $validator,
    $lockedRunner,
    $lockPath,
    $trustedArtifactsPath,
    $script:LiveOverlayPath,
    $killSwitchPath
)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required paused-live file not found: $requiredFile"
    }
}
if (Test-Path Env:AI_TRADING_KILL_SWITCH_FILE) {
    throw "Remove inherited AI_TRADING_KILL_SWITCH_FILE before paused live recovery."
}

function Get-LowerSha256([System.IO.Stream]$Stream) {
    $Stream.Position = 0
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha.ComputeHash($Stream)
        return ([System.BitConverter]::ToString($digest)).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $Stream.Position = 0
        $sha.Dispose()
    }
}

function Request-Authorization {
    $result = & $python -m local_trader --db $databasePath authorize `
        --strategy $Strategy `
        --version $Version `
        --target $Target
    if ($LASTEXITCODE -ne 0) {
        throw "Registry authorization rejected this exact live artifact."
    }
    try {
        return (($result -join "`n") | ConvertFrom-Json -ErrorAction Stop)
    }
    catch {
        throw "Registry authorization returned invalid JSON."
    }
}

# An open handle with FileShare.None is an automatically crash-released,
# per-account/per-database process lock.  A stale file is harmless; only the
# live handle represents ownership.
$instanceLock = $null
try {
    $instanceLock = [System.IO.File]::Open(
        $instanceLockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
}
catch {
    throw "Another live recovery process already owns $instanceLockPath"
}

$sourceLock = $null
$configLock = $null
$dependencyLock = $null
$runnerLock = $null
$trustedArtifactsLock = $null
$savedEnvironment = @{}
$environmentWasMinimized = $false

# No Python preflight child receives exchange credentials.  They are restored
# only for the final, exact Freqtrade child after every check has passed.
Remove-Item "Env:FREQTRADE__EXCHANGE__KEY" -ErrorAction SilentlyContinue
Remove-Item "Env:FREQTRADE__EXCHANGE__SECRET" -ErrorAction SilentlyContinue

try {
    $payload = Request-Authorization
    if (-not $payload.ok -or $payload.command -ne "authorize" -or $null -eq $payload.authorization) {
        throw "Registry authorization response has the wrong contract."
    }
    $authorization = $payload.authorization
    if (
        $authorization.strategy -cne $Strategy -or
        [int]$authorization.version -ne $Version -or
        $authorization.target -cne $Target -or
        $authorization.lifecycle -cne $Target -or
        $authorization.source_root -cne "promoted"
    ) {
        throw "Registry authorization does not match the requested strategy/version/target."
    }

    $promotedRoot = [System.IO.Path]::GetFullPath(
        (Join-Path $script:UserDataPath "strategies\promoted")
    )
    $promotedPrefix = $promotedRoot.TrimEnd("\", "/") + "\"
    $sourcePath = [System.IO.Path]::GetFullPath([string]$authorization.source_path)
    if (-not $sourcePath.StartsWith($promotedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Authorized source is outside the promoted strategy root."
    }
    if ([System.IO.Path]::GetExtension($sourcePath) -cne ".py") {
        throw "Authorized source is not a Python strategy file."
    }

    $sourceLock = [System.IO.File]::Open(
        $sourcePath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    $sourceHash = Get-LowerSha256 $sourceLock
    if ($sourceHash -cne [string]$authorization.artifact_sha256) {
        throw "Authorized strategy changed before it could be locked."
    }
    if ($sourceLock.Length -ne [int64]$authorization.artifact_size) {
        throw "Authorized strategy size changed before it could be locked."
    }

    # Registry approval is necessary but not sufficient for arbitrary Python.
    # Live code also needs a separately tracked, exact-hash source audit.
    $trustedArtifactsLock = [System.IO.File]::Open(
        $trustedArtifactsPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    $trustedReader = [System.IO.StreamReader]::new(
        $trustedArtifactsLock,
        [System.Text.Encoding]::UTF8,
        $true,
        4096,
        $true
    )
    try {
        $trustedArtifacts = $trustedReader.ReadToEnd() | ConvertFrom-Json -ErrorAction Stop
    }
    finally {
        $trustedReader.Dispose()
    }
    if ($trustedArtifacts.schema_version -ne 1) {
        throw "Unsupported trusted-live-artifacts schema."
    }
    $trustedMatch = @($trustedArtifacts.artifacts | Where-Object {
        $_.strategy -ceq $Strategy -and
        $_.artifact_sha256 -ceq $sourceHash -and
        $_.decision -ceq "APPROVED" -and
        -not [string]::IsNullOrWhiteSpace([string]$_.reviewed_by) -and
        -not [string]::IsNullOrWhiteSpace([string]$_.reviewed_at_utc)
    })
    if ($trustedMatch.Count -ne 1) {
        throw "Exact strategy hash has no independent APPROVED source audit; live remains blocked."
    }

    $manifest = $authorization.deployment_manifest
    if ($null -eq $manifest) {
        throw "Authorization has no deployment manifest."
    }
    $riskPolicyJson = $authorization.risk_policy | ConvertTo-Json -Compress
    $preflightResult = & $python $validator `
        --config $script:ConfigPath `
        --overlay $script:LiveOverlayPath `
        --strategy $sourcePath `
        --strategy-name $Strategy `
        --expected-strategy-sha256 ([string]$authorization.artifact_sha256) `
        --expected-config-sha256 ([string]$manifest.config_sha256) `
        --lock $lockPath `
        --expected-lock-sha256 ([string]$manifest.lock_sha256) `
        --expected-imports-sha256 ([string]$manifest.imports_sha256) `
        --expected-freqtrade-version ([string]$manifest.freqtrade_version) `
        --risk-policy-json $riskPolicyJson `
        --write-effective-config $effectiveConfig
    if ($LASTEXITCODE -ne 0) {
        throw "Live recovery preflight rejected the frozen execution bundle."
    }
    try {
        $preflight = ($preflightResult -join "`n") | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "Live recovery preflight returned invalid JSON."
    }
    if (-not $preflight.ok -or $preflight.strategy_sha256 -cne $sourceHash) {
        throw "Live recovery preflight did not verify the authorized strategy."
    }

    # Hold exact code/config/lock/bootstrap handles for the complete child lifetime.
    $configLock = [System.IO.File]::Open(
        $effectiveConfig,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    if ((Get-LowerSha256 $configLock) -cne [string]$manifest.config_sha256) {
        throw "Frozen effective configuration changed before it could be locked."
    }
    $dependencyLock = [System.IO.File]::Open(
        $lockPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    if ((Get-LowerSha256 $dependencyLock) -cne [string]$manifest.lock_sha256) {
        throw "Dependency lock changed before it could be locked."
    }
    $runnerLock = [System.IO.File]::Open(
        $lockedRunner,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )

    # Re-authorize immediately before launch.  The Registry intentionally
    # remains writable so emergency DEGRADED/PAUSED events are not blocked.
    $secondPayload = Request-Authorization
    $secondAuthorization = $secondPayload.authorization
    if (
        $secondAuthorization.artifact_sha256 -cne $authorization.artifact_sha256 -or
        $secondAuthorization.lifecycle -cne $authorization.lifecycle -or
        $secondAuthorization.target -cne $authorization.target
    ) {
        throw "Registry authorization changed during preflight."
    }

    # Minimize the final child's environment.  It necessarily receives the
    # Binance key, but not unrelated cloud/CI/API credentials from this shell.
    $environmentAllowlist = @(
        "ALLUSERSPROFILE", "APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH",
        "LOCALAPPDATA", "NUMBER_OF_PROCESSORS", "OS", "PATH", "PATHEXT",
        "PROCESSOR_ARCHITECTURE", "PROGRAMDATA", "PROGRAMFILES",
        "PROGRAMFILES(X86)", "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP",
        "USERDOMAIN", "USERNAME", "USERPROFILE", "WINDIR"
    )
    Get-ChildItem Env: | ForEach-Object {
        $savedEnvironment[$_.Name] = $_.Value
        if ($_.Name -notin $environmentAllowlist) {
            Remove-Item -ErrorAction SilentlyContinue -LiteralPath "Env:$($_.Name)"
        }
    }
    $environmentWasMinimized = $true
    $env:FREQTRADE__EXCHANGE__KEY = $apiKey
    $env:FREQTRADE__EXCHANGE__SECRET = $apiSecret
    $env:FREQTRADE__INITIAL_STATE = "paused"
    $env:AI_TRADING_KILL_SWITCH_FILE = $killSwitchPath

    # The bootstrap compiles the already-hashed bytes directly and replaces
    # Freqtrade's directory resolver, so no competing .py or parameter JSON can
    # win a lookup race.
    $commandArgs = @(
        $lockedRunner,
        "--strategy-source", $sourcePath,
        "--strategy-sha256", $sourceHash,
        "--strategy-class", $Strategy,
        "--",
        "trade",
        "--config", $effectiveConfig,
        "--userdir", $script:UserDataPath,
        "--strategy", $Strategy,
        "--logfile", (Join-Path $script:UserDataPath "logs\freqtrade-live.log")
    )
    Push-Location -LiteralPath $script:RuntimeRoot
    try {
        & $python @commandArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Locked Freqtrade runtime exited with code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($environmentWasMinimized) {
        Get-ChildItem Env: | ForEach-Object {
            Remove-Item -ErrorAction SilentlyContinue -LiteralPath "Env:$($_.Name)"
        }
        foreach ($name in $savedEnvironment.Keys) {
            [Environment]::SetEnvironmentVariable(
                $name,
                [string]$savedEnvironment[$name],
                [EnvironmentVariableTarget]::Process
            )
        }
        $env:FREQTRADE__EXCHANGE__KEY = $apiKey
        $env:FREQTRADE__EXCHANGE__SECRET = $apiSecret
    }
    else {
        $env:FREQTRADE__EXCHANGE__KEY = $apiKey
        $env:FREQTRADE__EXCHANGE__SECRET = $apiSecret
    }
    foreach ($stream in @(
        $trustedArtifactsLock,
        $runnerLock,
        $dependencyLock,
        $configLock,
        $sourceLock,
        $instanceLock
    )) {
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
    # Delete only the exact generated file.  Never recursively clean a temp path.
    if (Test-Path -LiteralPath $effectiveConfig -PathType Leaf) {
        Remove-Item -Force -LiteralPath $effectiveConfig
    }
}
