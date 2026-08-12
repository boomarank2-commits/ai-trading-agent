[CmdletBinding()]
param(
    [string]$Timerange = ""
)

. (Join-Path $PSScriptRoot "_common.ps1")
Assert-NoFreqtradeOverrides

$commandArgs = @(
    "lookahead-analysis",
    "--config", $script:ConfigPath,
    "--config", $script:PublicOverlayPath,
    "--config", $script:AnalysisOverlayPath,
    "--userdir", $script:UserDataPath,
    "--strategy", $script:StrategyName,
    "--fee", "0.002",
    "--minimum-trade-amount", "10",
    "--targeted-trade-amount", "50"
)

if ($Timerange) {
    $commandArgs += @("--timerange", $Timerange)
}

$previousAnalysisCapital = [Environment]::GetEnvironmentVariable(
    "FREQTRADE__AVAILABLE_CAPITAL",
    [EnvironmentVariableTarget]::Process
)

try {
    # The lookahead diagnostic itself forces a 1bn simulated wallet, 10k stake
    # and unlimited pair concurrency.  available_capital would otherwise leave
    # it with only one analyzable trade.  This process can only execute the
    # fixed lookahead-analysis command above and receives no exchange key.
    $env:FREQTRADE__AVAILABLE_CAPITAL = "1000000000"
    Invoke-FreqtradeCommand -CommandArgs $commandArgs
}
finally {
    if ($null -eq $previousAnalysisCapital) {
        Remove-Item "Env:FREQTRADE__AVAILABLE_CAPITAL" -ErrorAction SilentlyContinue
    }
    else {
        $env:FREQTRADE__AVAILABLE_CAPITAL = $previousAnalysisCapital
    }
}
