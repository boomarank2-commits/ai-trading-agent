[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$outputRoot = Join-Path $repoRoot "research\reports"
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$archivePath = Join-Path $outputRoot "DEEP_RESEARCH_10_COINS_V12_31_$timestamp.zip"
$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "ai-trading-deep-research-" + [guid]::NewGuid().ToString("N")
)

$requiredFiles = @(
    "RESEARCH_MASTERPLAN_DE.md",
    "BACKTEST_ANLEITUNG.md",
    "START_HERE_DE.md",
    "research\trial_ledger.csv",
    "research\executed_test_fingerprints.csv",
    "research\V12_20_SELECTIVE_PYRAMID_DE.md",
    "research\V12_22_SOL_ADX21_DE.md",
    "research\V12_23_LTC_EMA_TREND_DE.md",
    "research\V12_24_LTC_SLOT_RESERVE_DE.md",
    "research\V12_26_BCH_EMA_TREND_FIX_DE.md",
    "research\V12_28_TRX_SINGLE_BLOCK_DE.md",
    "research\V12_29_BNB_DONCHIAN80_DE.md",
    "research\V12_30_DOGE_SUPERTREND_DE.md",
    "research\V12_31_DOGE_BCH_COMBINATION_DE.md",
    "research\V12_32_LTC_ROUTE_COMBINATION_DE.md",
    "research\PAIR_SCREEN_V2_SOL_LTC_REJECTED_DE.md",
    "research\CAUSAL_SCREEN_V2_BOUNDARY_FIX_DE.md",
    "runtime\user_data\strategies\CompressionBreakout250.py",
    "runtime\user_data\config-public.json",
    "runtime\locked_backtest_freqtrade.py",
    "runtime\ten_pair_backtest_api.py",
    "research\causal_pair_route_screen.py",
    "tests\test_testbot_backtest_api.py",
    "tests\runtime\test_locked_freqtrade.py",
    "tests\runtime\test_v12_17_ten_pair_research_contract.py",
    "tests\runtime\test_v12_22_sol_adx_gate.py",
    "tests\runtime\test_v12_23_v12_24_rejected.py",
    "tests\runtime\test_v12_25_v12_26_bch_research.py",
    "tests\runtime\test_v12_28_trx_single_block.py",
    "tests\runtime\test_v12_29_bnb_donchian80.py",
    "tests\runtime\test_v12_30_doge_supertrend.py",
    "tests\runtime\test_v12_31_bch_doge_combination.py",
    "tests\runtime\test_v12_32_ltc_combination_rejected.py"
)

function Copy-RelativeFile {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    $source = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Pflichtdatei fehlt: $RelativePath"
    }
    $destination = Join-Path $stageRoot $RelativePath
    $destinationParent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination
}

New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null

try {
    $bundleDocsDestination = Join-Path $stageRoot (
        "research\deep_research_10_coins"
    )
    New-Item -ItemType Directory -Path (
        Split-Path -Parent $bundleDocsDestination
    ) -Force | Out-Null
    Copy-Item -LiteralPath (
        Join-Path $repoRoot "research\deep_research_10_coins"
    ) -Destination $bundleDocsDestination -Recurse

    foreach ($relativePath in $requiredFiles) {
        Copy-RelativeFile -RelativePath $relativePath
    }

    $historicalRoot = Join-Path $stageRoot "HISTORISCH_V12_20_NICHT_AKTUELL"
    $pairHistorySource = Join-Path $repoRoot (
        "runtime\user_data\backtest_results\ui\_PAIR_HISTORIEN"
    )
    if (Test-Path -LiteralPath $pairHistorySource -PathType Container) {
        New-Item -ItemType Directory -Path $historicalRoot -Force | Out-Null
        Copy-Item -LiteralPath $pairHistorySource -Destination (
            Join-Path $historicalRoot "PAIR_HISTORIEN"
        ) -Recurse
    }

    $batchResultSource = Join-Path $repoRoot (
        "runtime\user_data\backtest_results\_BATCHES\" +
        "20260824T102507Z-921d9cd2\batch-result.json"
    )
    if (Test-Path -LiteralPath $batchResultSource -PathType Leaf) {
        New-Item -ItemType Directory -Path $historicalRoot -Force | Out-Null
        Copy-Item -LiteralPath $batchResultSource -Destination (
            Join-Path $historicalRoot "batch-result-v12.20.json"
        )
    }

    $hashLines = Get-ChildItem -LiteralPath $stageRoot -Recurse -File |
        Where-Object { $_.Name -ne "_DATEILISTE_SHA256.txt" } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($stageRoot.Length + 1)
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            "$hash  $relative"
        }
    $hashLines | Set-Content -LiteralPath (
        Join-Path $stageRoot "_DATEILISTE_SHA256.txt"
    ) -Encoding UTF8

    Compress-Archive -Path (Join-Path $stageRoot "*") -DestinationPath (
        $archivePath
    ) -CompressionLevel Optimal

    Write-Output $archivePath
}
finally {
    if (
        (Test-Path -LiteralPath $stageRoot) -and
        $stageRoot.StartsWith([System.IO.Path]::GetTempPath())
    ) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
