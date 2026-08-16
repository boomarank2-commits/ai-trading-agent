[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_common.ps1")

$setupScript = Join-Path $PSScriptRoot "setup-venv.ps1"
$exportScript = Join-Path $PSScriptRoot "export-dryrun-report.ps1"
$logsRoot = Join-Path $script:UserDataPath "logs"
$sessionsRoot = Join-Path $logsRoot "sessions"
$instanceLockPath = Join-Path $logsRoot "testbot-instance.lock"
$entryStopPath = Join-Path $script:UserDataPath "DRYRUN_STOP_ENTRIES"
$databasePath = Join-Path $script:UserDataPath "tradesv8.dryrun.sqlite"
$databaseUrl = "sqlite:///user_data/tradesv8.dryrun.sqlite"
$strategyPath = Join-Path $script:UserDataPath "strategies\CompressionBreakout250.py"
$strategyDirectory = Split-Path -Parent $strategyPath
$lockFilePath = Join-Path $script:RepoRoot "uv.lock"
$dryRunValidator = Join-Path $script:RuntimeRoot "validate_dryrun_config.py"
$lockedRunner = Join-Path $script:RuntimeRoot "locked_freqtrade.py"
$pythonExe = Join-Path $script:VenvPath "Scripts\python.exe"
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Write-JsonAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Value
    )

    $absolutePath = [System.IO.Path]::GetFullPath($Path)
    $directory = [System.IO.Path]::GetDirectoryName($absolutePath)
    $filename = [System.IO.Path]::GetFileName($absolutePath)
    $uniqueSuffix = "$PID.$([Guid]::NewGuid().ToString('N'))"
    $temporary = Join-Path $directory ".$filename.tmp.$uniqueSuffix"
    $backup = Join-Path $directory ".$filename.bak.$uniqueSuffix"
    $content = ($Value | ConvertTo-Json -Depth 20) + [Environment]::NewLine
    try {
        [System.IO.File]::WriteAllText($temporary, $content, $utf8NoBom)
        if (Test-Path -LiteralPath $absolutePath -PathType Leaf) {
            # Windows PowerShell 5 / .NET Framework rejects a null backup path.
            # File.Replace remains atomic because temp, target and the unique
            # short-lived backup all live in the target directory.
            [System.IO.File]::Replace($temporary, $absolutePath, $backup)
        }
        else {
            [System.IO.File]::Move($temporary, $absolutePath)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) {
            Remove-Item -LiteralPath $temporary -Force
        }
        if (Test-Path -LiteralPath $backup -PathType Leaf) {
            Remove-Item -LiteralPath $backup -Force
        }
    }
}

function Write-SupervisorLog {
    param([Parameter(Mandatory = $true)][string]$Message)

    $line = "[$([DateTimeOffset]::UtcNow.ToString('o'))] $Message"
    Write-Host $line
    if (-not [string]::IsNullOrWhiteSpace($script:SupervisorLogPath)) {
        [System.IO.File]::AppendAllText(
            $script:SupervisorLogPath,
            $line + [Environment]::NewLine,
            $utf8NoBom
        )
    }
}

function Get-LowerSha256 {
    param([Parameter(Mandatory = $true)][System.IO.Stream]$Stream)

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

Assert-NoFreqtradeOverrides
[System.IO.Directory]::CreateDirectory($sessionsRoot) | Out-Null

$instanceLock = $null
$sleepPreventionActive = $false
$previousDryRun = [Environment]::GetEnvironmentVariable(
    "FREQTRADE__DRY_RUN",
    [EnvironmentVariableTarget]::Process
)
$previousInitialState = [Environment]::GetEnvironmentVariable(
    "FREQTRADE__INITIAL_STATE",
    [EnvironmentVariableTarget]::Process
)
$previousKillSwitch = [Environment]::GetEnvironmentVariable(
    "AI_TRADING_KILL_SWITCH_FILE",
    [EnvironmentVariableTarget]::Process
)
$script:SupervisorLogPath = ""
$manifestPath = ""
$reportJsonPath = ""
$reportMarkdownPath = ""
$startedAtUtc = $null
$failureMessage = ""
$botExitCode = $null
$manifest = $null
$savedEnvironment = @{}
$environmentWasMinimized = $false
$sourceLock = $null
$configLock = $null
$publicOverlayLock = $null
$runnerLock = $null
$dependencyLock = $null

try {
    try {
        $instanceLock = [System.IO.File]::Open(
            $instanceLockPath,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    }
    catch [System.IO.IOException] {
        throw "Der Testbot laeuft bereits. Ein zweiter Start wurde sicher blockiert."
    }

    $sessionCreatedAt = [DateTimeOffset]::UtcNow
    $sessionId = "$($sessionCreatedAt.ToString('yyyyMMddTHHmmssZ'))-pid-$PID"
    $sessionPath = Join-Path $sessionsRoot $sessionId
    [System.IO.Directory]::CreateDirectory($sessionPath) | Out-Null
    $script:SupervisorLogPath = Join-Path $sessionPath "supervisor.log"
    $freqtradeLogPath = Join-Path $sessionPath "freqtrade.log"
    $manifestPath = Join-Path $sessionPath "session-manifest.json"
    $reportJsonPath = Join-Path $sessionPath "dryrun-report-$sessionId.json"
    $reportMarkdownPath = Join-Path $sessionPath "dryrun-report-$sessionId.md"

    Write-SupervisorLog "Testbot-Supervisor gestartet. Sitzungs-ID: $sessionId"

    if (-not (Test-Path -LiteralPath $script:FreqtradeExe -PathType Leaf)) {
        Write-SupervisorLog "Lokale Umgebung fehlt; fuehre das erste Setup aus."
    }
    else {
        Write-SupervisorLog "Pruefe die lokale Umgebung gegen uv.lock."
    }
    try {
        & $setupScript
    }
    catch {
        throw "Setup oder Pruefung der lokalen Umgebung ist fehlgeschlagen: $($_.Exception.Message)"
    }
    Assert-RuntimeLayout
    foreach ($requiredFile in @($dryRunValidator, $lockedRunner, $strategyPath, $lockFilePath)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Erforderliche Testbot-Datei fehlt: $requiredFile"
        }
    }

    # Lock every execution input before resolving and validating the effective
    # configuration.  Read sharing lets Freqtrade consume the files, while
    # writes, replacement and deletion remain blocked for the whole session.
    $sourceLock = [System.IO.File]::Open(
        $strategyPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    $configLock = [System.IO.File]::Open(
        $script:ConfigPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    $publicOverlayLock = [System.IO.File]::Open(
        $script:PublicOverlayPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    $runnerLock = [System.IO.File]::Open(
        $lockedRunner,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    $dependencyLock = [System.IO.File]::Open(
        $lockFilePath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    $strategyHash = Get-LowerSha256 -Stream $sourceLock
    $configHash = Get-LowerSha256 -Stream $configLock
    $publicOverlayHash = Get-LowerSha256 -Stream $publicOverlayLock
    $dependencyHash = Get-LowerSha256 -Stream $dependencyLock

    $previousValidationDryRun = [Environment]::GetEnvironmentVariable(
        "FREQTRADE__DRY_RUN",
        [EnvironmentVariableTarget]::Process
    )
    $previousValidationState = [Environment]::GetEnvironmentVariable(
        "FREQTRADE__INITIAL_STATE",
        [EnvironmentVariableTarget]::Process
    )
    try {
        $env:FREQTRADE__DRY_RUN = "true"
        $env:FREQTRADE__INITIAL_STATE = "running"
        $showConfigOutput = @(
            & $script:FreqtradeExe show-config `
                --config $script:ConfigPath `
                --config $script:PublicOverlayPath `
                --userdir $script:UserDataPath
        ) | ForEach-Object { $_.ToString() }
        if ($LASTEXITCODE -ne 0) {
            throw "Freqtrade konnte die wirksame Dry-run-Konfiguration nicht aufloesen."
        }
        $showConfigText = $showConfigOutput -join [Environment]::NewLine
        $jsonStart = $showConfigText.IndexOf("{")
        if ($jsonStart -lt 0) {
            throw "Freqtrade lieferte keine wirksame JSON-Konfiguration."
        }
        $effectiveConfigJson = $showConfigText.Substring($jsonStart)
        $validationOutput = $effectiveConfigJson | & $pythonExe $dryRunValidator `
            --strategy-directory $strategyDirectory
        if ($LASTEXITCODE -ne 0) {
            throw "Die wirksame Dry-run-Konfiguration verletzt den Testbot-Vertrag."
        }
        $effectiveSettings = ($validationOutput -join "`n") | ConvertFrom-Json
    }
    finally {
        if ($null -eq $previousValidationDryRun) {
            Remove-Item "Env:FREQTRADE__DRY_RUN" -ErrorAction SilentlyContinue
        }
        else {
            $env:FREQTRADE__DRY_RUN = $previousValidationDryRun
        }
        if ($null -eq $previousValidationState) {
            Remove-Item "Env:FREQTRADE__INITIAL_STATE" -ErrorAction SilentlyContinue
        }
        else {
            $env:FREQTRADE__INITIAL_STATE = $previousValidationState
        }
    }
    if (-not $effectiveSettings.ok) {
        throw "Die wirksame Dry-run-Konfiguration wurde nicht autorisiert."
    }
    Write-SupervisorLog "Wirksame Dry-run-Konfiguration exakt geprueft."

    try {
        if ($null -eq ("DaviddTechTestBotPower" -as [type])) {
            Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class DaviddTechTestBotPower {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
        }
        $executionState = [DaviddTechTestBotPower]::SetThreadExecutionState(
            [uint32]2147483649
        )
        if ($executionState -ne 0) {
            $sleepPreventionActive = $true
            Write-SupervisorLog "Windows-Energiesparmodus ist fuer diese Sitzung blockiert."
        }
        else {
            Write-SupervisorLog "WARNUNG: Energiesparmodus konnte nicht blockiert werden."
        }
    }
    catch {
        Write-SupervisorLog "WARNUNG: Energiesparmodus konnte nicht blockiert werden: $($_.Exception.Message)"
    }

    $manifest = [ordered]@{
        schema_version = 1
        session_id = $sessionId
        started_at_utc = $sessionCreatedAt.ToString("o")
        ended_at_utc = $null
        status = "starting"
        dry_run = $true
        real_orders_possible = $false
        strategy = [ordered]@{
            name = $script:StrategyName
            path = [System.IO.Path]::GetFullPath($strategyPath)
            sha256 = $strategyHash
        }
        config = [ordered]@{
            path = [System.IO.Path]::GetFullPath($script:ConfigPath)
            sha256 = $configHash
            public_overlay_path = [System.IO.Path]::GetFullPath($script:PublicOverlayPath)
            public_overlay_sha256 = $publicOverlayHash
        }
        dependency_lock = [ordered]@{
            path = [System.IO.Path]::GetFullPath($lockFilePath)
            sha256 = $dependencyHash
        }
        settings = [ordered]@{
            capital_usdt = [double]$effectiveSettings.capital_usdt
            stake_per_trade_usdt = [double]$effectiveSettings.stake_per_trade_usdt
            max_open_positions = [int]$effectiveSettings.max_open_positions
            maximum_exposure_usdt = [double]$effectiveSettings.maximum_exposure_usdt
            pairs = @($effectiveSettings.pairs)
        }
        database = [ordered]@{
            path = [System.IO.Path]::GetFullPath($databasePath)
            persistent = $true
            continued_existing_database = Test-Path -LiteralPath $databasePath -PathType Leaf
        }
        entry_stop_file = [ordered]@{
            path = [System.IO.Path]::GetFullPath($entryStopPath)
            active_at_start = Test-Path -LiteralPath $entryStopPath -PathType Leaf
        }
        artifacts = [ordered]@{
            session_directory = [System.IO.Path]::GetFullPath($sessionPath)
            supervisor_log = [System.IO.Path]::GetFullPath($script:SupervisorLogPath)
            freqtrade_log = [System.IO.Path]::GetFullPath($freqtradeLogPath)
            report_json = [System.IO.Path]::GetFullPath($reportJsonPath)
            report_markdown = [System.IO.Path]::GetFullPath($reportMarkdownPath)
            manifest = [System.IO.Path]::GetFullPath($manifestPath)
        }
        freqtrade_exit_code = $null
        report_status = "pending"
    }
    Write-JsonAtomic -Path $manifestPath -Value $manifest
    $startedAtUtc = [DateTimeOffset]::Parse([string]$manifest.started_at_utc)

    Write-Host ""
    Write-Host "================================================================"
    Write-Host " TESTBETRIEB - KEIN ECHTGELD - AUSSCHLIESSLICH DRY-RUN"
    Write-Host "================================================================"
    Write-Host " Virtuelle Wallet  : 250 USDT"
    Write-Host " Position          : maximal 80 USDT"
    Write-Host " Gleichzeitig      : maximal 3 Positionen"
    Write-Host " Paare             : BTC/USDT, ETH/USDT, SOL/USDT"
    Write-Host " Datenbank         : $databasePath"
    Write-Host " Sitzung           : $sessionPath"
    if ($manifest.database.continued_existing_database) {
        Write-Host " Datenstatus        : vorhandene Test-Datenbank wird fortgesetzt"
    }
    else {
        Write-Host " Datenstatus        : neue persistente Test-Datenbank"
    }
    if ($manifest.entry_stop_file.active_at_start) {
        Write-Host " Entries            : GESPERRT durch STOP_NEUE_TESTTRADES.bat"
    }
    else {
        Write-Host " Entries            : fuer simulierte Trades freigegeben"
    }
    Write-Host " Beenden            : Strg+C"
    Write-Host "================================================================"
    Write-Host " HINWEIS: 0 Trades in 24 Stunden kann bei dieser selten handelnden"
    Write-Host " Strategie normal sein. Fuer Bericht und sauberes Ende Strg+C nutzen."
    Write-Host " Das direkte Schliessen des Fensters kann den Bericht ueberspringen;"
    Write-Host " TESTBOT_AUSWERTUNG.bat kann jederzeit separat ausgewertet werden."
    Write-Host "================================================================"
    Write-Host ""

    # Generated strategy code runs inside Freqtrade.  Give that child only the
    # Windows runtime variables it needs, not unrelated cloud/API credentials
    # inherited from the shell.  Dry-run needs no exchange secret at all.
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
    $env:FREQTRADE__DRY_RUN = "true"
    $env:FREQTRADE__INITIAL_STATE = "running"
    $env:AI_TRADING_KILL_SWITCH_FILE = [System.IO.Path]::GetFullPath($entryStopPath)
    $manifest.status = "running"
    Write-JsonAtomic -Path $manifestPath -Value $manifest

    $commandArgs = @(
        $lockedRunner,
        "--strategy-source", $strategyPath,
        "--strategy-sha256", $manifest.strategy.sha256,
        "--strategy-class", $script:StrategyName,
        "--",
        "trade",
        "--config", $script:ConfigPath,
        "--config", $script:PublicOverlayPath,
        "--userdir", $script:UserDataPath,
        "--strategy", $script:StrategyName,
        "--db-url", $databaseUrl,
        "--logfile", $freqtradeLogPath
    )

    Push-Location -LiteralPath $script:RuntimeRoot
    try {
        & $pythonExe @commandArgs
        $botExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if ($botExitCode -notin @(0, 130, -1073741510)) {
        throw "Freqtrade wurde mit Code $botExitCode beendet."
    }
}
catch [System.Management.Automation.PipelineStoppedException] {
    $botExitCode = 130
    if (-not [string]::IsNullOrWhiteSpace($script:SupervisorLogPath)) {
        Write-SupervisorLog "Strg+C empfangen; Testbot wird kontrolliert beendet."
    }
}
catch {
    $failureMessage = $_.Exception.Message
    if (-not [string]::IsNullOrWhiteSpace($script:SupervisorLogPath)) {
        Write-SupervisorLog "FEHLER: $failureMessage"
    }
    else {
        Write-Host "FEHLER: $failureMessage" -ForegroundColor Red
    }
}
finally {
    $endedAtUtc = [DateTimeOffset]::UtcNow

    if (
        $null -ne $manifest -and
        $null -ne $startedAtUtc -and
        -not [string]::IsNullOrWhiteSpace($reportJsonPath)
    ) {
        try {
            Write-SupervisorLog "Erzeuge automatische Sitzungs-Auswertung."
            & $exportScript `
                -SessionStartUtc $startedAtUtc.ToString("o") `
                -SessionEndUtc $endedAtUtc.ToString("o") `
                -OutputDirectory (Split-Path -Parent $reportJsonPath) `
                -SessionId $manifest.session_id
            $manifest.report_status = "created"
        }
        catch {
            $manifest.report_status = "failed: $($_.Exception.Message)"
            Write-SupervisorLog "WARNUNG: Auswertung fehlgeschlagen: $($_.Exception.Message)"
        }

        $manifest.ended_at_utc = $endedAtUtc.ToString("o")
        $manifest.freqtrade_exit_code = $botExitCode
        $manifest.status = if ([string]::IsNullOrWhiteSpace($failureMessage)) {
            "stopped"
        } else {
            "failed"
        }
        Write-JsonAtomic -Path $manifestPath -Value $manifest
        Write-SupervisorLog "Sitzung beendet. Manifest: $manifestPath"
    }

    if ($sleepPreventionActive) {
        [void][DaviddTechTestBotPower]::SetThreadExecutionState([uint32]2147483648)
    }

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
    }
    else {
        if ($null -eq $previousDryRun) {
            Remove-Item "Env:FREQTRADE__DRY_RUN" -ErrorAction SilentlyContinue
        }
        else {
            $env:FREQTRADE__DRY_RUN = $previousDryRun
        }
        if ($null -eq $previousInitialState) {
            Remove-Item "Env:FREQTRADE__INITIAL_STATE" -ErrorAction SilentlyContinue
        }
        else {
            $env:FREQTRADE__INITIAL_STATE = $previousInitialState
        }
        if ($null -eq $previousKillSwitch) {
            Remove-Item "Env:AI_TRADING_KILL_SWITCH_FILE" -ErrorAction SilentlyContinue
        }
        else {
            $env:AI_TRADING_KILL_SWITCH_FILE = $previousKillSwitch
        }
    }

    if ($null -ne $instanceLock) {
        $instanceLock.Dispose()
    }
    foreach ($stream in @(
        $dependencyLock,
        $runnerLock,
        $publicOverlayLock,
        $configLock,
        $sourceLock
    )) {
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($failureMessage)) {
    throw $failureMessage
}
