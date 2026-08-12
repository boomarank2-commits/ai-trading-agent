[CmdletBinding()]
param(
    [switch]$EnableEntries
)

. (Join-Path $PSScriptRoot "_common.ps1")
Assert-NoFreqtradeOverrides

if ($EnableEntries) {
    throw (
        "Direkte Dry-run-Entries sind deaktiviert. Fuer simulierte Entries " +
        "ausschliesslich STARTBOT.bat verwenden; dort gelten Doppelstart-Lock, " +
        "exakte Konfigurationspruefung und Sitzungsprotokollierung."
    )
}

$previousInitialState = [Environment]::GetEnvironmentVariable(
    "FREQTRADE__INITIAL_STATE",
    [EnvironmentVariableTarget]::Process
)
$previousDryRun = [Environment]::GetEnvironmentVariable(
    "FREQTRADE__DRY_RUN",
    [EnvironmentVariableTarget]::Process
)

try {
    # Default invocation is deliberately stopped.  The opt-in only affects
    # this process and still uses the dry-run configuration.
    $env:FREQTRADE__DRY_RUN = "true"
    $env:FREQTRADE__INITIAL_STATE = if ($EnableEntries) { "running" } else { "stopped" }

    $commandArgs = @(
        "trade",
        "--config", $script:ConfigPath,
        "--config", $script:PublicOverlayPath,
        "--userdir", $script:UserDataPath,
        "--strategy", $script:StrategyName,
        "--logfile", (Join-Path $script:UserDataPath "logs\freqtrade-dryrun.log")
    )
    Invoke-FreqtradeCommand -CommandArgs $commandArgs
}
finally {
    if ($null -eq $previousInitialState) {
        Remove-Item "Env:FREQTRADE__INITIAL_STATE" -ErrorAction SilentlyContinue
    }
    else {
        $env:FREQTRADE__INITIAL_STATE = $previousInitialState
    }
    if ($null -eq $previousDryRun) {
        Remove-Item "Env:FREQTRADE__DRY_RUN" -ErrorAction SilentlyContinue
    }
    else {
        $env:FREQTRADE__DRY_RUN = $previousDryRun
    }
}
