from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
REPORT = ROOT / "research" / "V12_32_LTC_ROUTE_COMBINATION_DE.md"
LEDGER = ROOT / "research" / "trial_ledger.csv"


def test_v12_32_ltc_combination_is_recorded_as_rejected() -> None:
    report = REPORT.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert "V12.32-DOGE-BCH-LTC-FIXED-ROUTE-COMBINATION" in report
    assert "VERWORFEN" in report
    assert "NICHT IN DEN PAPERBOT" in report
    assert "+369,822" in report
    assert "50,035 USDT" in report
    assert '"REJECT_BACKTEST_SYSTEM_GATE"' in ledger
    assert '"REJECT_DO_NOT_PROMOTE"' in ledger


def test_rejected_v12_32_did_not_replace_active_v12_31() -> None:
    source = STRATEGY.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.31"' in source
    assert "v12_32_ltc_ema30_80_trend" not in source
    assert "ltc_ema_macro_rising_12" not in source
