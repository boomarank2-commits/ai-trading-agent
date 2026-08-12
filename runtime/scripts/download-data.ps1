[CmdletBinding()]
param(
    [ValidateRange(30, 3650)]
    [int]$Days = 730
)

. (Join-Path $PSScriptRoot "_common.ps1")
Assert-NoFreqtradeOverrides

$commandArgs = @(
    "download-data",
    "--config", $script:ConfigPath,
    "--config", $script:PublicOverlayPath,
    "--userdir", $script:UserDataPath,
    "--timeframes", "15m",
    "--pairs", "BTC/USDT", "ETH/USDT", "SOL/USDT",
    "--trading-mode", "spot",
    "--days", $Days.ToString()
)

Invoke-FreqtradeCommand -CommandArgs $commandArgs
