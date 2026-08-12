[CmdletBinding()]
param(
    [string]$Timerange = ""
)

. (Join-Path $PSScriptRoot "_common.ps1")
Assert-NoFreqtradeOverrides

$commandArgs = @(
    "recursive-analysis",
    "--config", $script:ConfigPath,
    "--config", $script:PublicOverlayPath,
    "--userdir", $script:UserDataPath,
    "--strategy", $script:StrategyName,
    "--pairs", "BTC/USDT",
    "--startup-candle", "199", "399", "799", "1599"
)

if ($Timerange) {
    $commandArgs += @("--timerange", $Timerange)
}

Invoke-FreqtradeCommand -CommandArgs $commandArgs
