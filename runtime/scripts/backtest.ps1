[CmdletBinding()]
param(
    [string]$Timerange = ""
)

. (Join-Path $PSScriptRoot "_common.ps1")
Assert-NoFreqtradeOverrides

$commandArgs = @(
    "backtesting",
    "--config", $script:ConfigPath,
    "--config", $script:PublicOverlayPath,
    "--userdir", $script:UserDataPath,
    "--strategy", $script:StrategyName,
    "--fee", "0.002",
    "--enable-protections",
    "--cache", "none",
    "--export", "trades",
    "--backtest-directory", (Join-Path $script:UserDataPath "backtest_results"),
    "--breakdown", "month"
)

if ($Timerange) {
    $commandArgs += @("--timerange", $Timerange)
}

Invoke-FreqtradeCommand -CommandArgs $commandArgs
