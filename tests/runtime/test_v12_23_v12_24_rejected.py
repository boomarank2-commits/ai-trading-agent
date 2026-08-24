from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
LEDGER = ROOT / "research" / "trial_ledger.csv"


def test_rejected_ltc_experiments_remain_documented_and_inactive() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.23"' not in source
    assert 'STRATEGY_VERSION = "V12.24"' not in source
    assert "v12_23_ltc_ema30_80_trend" not in source
    assert '"V12.23-LTC-EMA30-80-MACRO200"' in ledger
    assert '"V12.24-LTC-EMPTY-PORTFOLIO-ENTRY"' in ledger
    assert ledger.count('"REJECT_BACKTEST_SYSTEM_GATE"') >= 3
    assert ledger.count('"REJECT_DO_NOT_PROMOTE"') >= 3


def test_rejected_experiment_reports_preserve_exact_shared_results() -> None:
    v12_23 = (ROOT / "research" / "V12_23_LTC_EMA_TREND_DE.md").read_text(
        encoding="utf-8"
    )
    v12_24 = (ROOT / "research" / "V12_24_LTC_SLOT_RESERVE_DE.md").read_text(
        encoding="utf-8"
    )

    assert "+232,037 USDT" in v12_23
    assert "18,86 %" in v12_23
    assert "+223,457 USDT" in v12_24
    assert "18,47 %" in v12_24
