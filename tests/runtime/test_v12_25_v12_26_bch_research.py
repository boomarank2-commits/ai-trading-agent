from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
LEDGER = ROOT / "research" / "trial_ledger.csv"


def test_bch_research_versions_are_documented_but_inactive() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.25"' not in source
    assert 'STRATEGY_VERSION = "V12.26"' not in source
    assert "v12_26_bch_ema30_80_trend" not in source
    assert '"V12.25-BCH-EMA30-80-MACRO100"' in ledger
    assert '"V12.26-BCH-EMA30-80-MACRO100-FIX"' in ledger
    assert '"ABORTED_TECHNICAL_PRE_SIMULATION"' in ledger
    assert '"REJECT_BACKTEST_SYSTEM_GATE"' in ledger


def test_bch_reports_preserve_technical_abort_and_exact_financial_result() -> None:
    v12_25 = (ROOT / "research" / "V12_25_BCH_EMA_TREND_DE.md").read_text(
        encoding="utf-8"
    )
    v12_26 = (ROOT / "research" / "V12_26_BCH_EMA_TREND_FIX_DE.md").read_text(
        encoding="utf-8"
    )

    assert "TECHNISCH ABGEBROCHEN" in v12_25
    assert "keine Ergebniskennzahlen" in v12_25
    assert "+317,451 USDT" in v12_26
    assert "16,47 %" in v12_26
    assert "REJECT_DO_NOT_PROMOTE" in v12_26
