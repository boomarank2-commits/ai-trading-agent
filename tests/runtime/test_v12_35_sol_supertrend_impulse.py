from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
REPORT = ROOT / "research" / "V12_35_SOL_SUPERTREND_IMPULSE_DE.md"
LEDGER = ROOT / "research" / "trial_ledger.csv"


def test_v12_35_technical_abort_is_recorded_without_financial_claim() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert "v12_35_sol_supertrend14x3_5_impulse" not in source
    assert "TECHNISCH ABGEBROCHEN" in report
    assert "keine Trades, kein PnL" in report
    assert "a1d032d293ea6a94886c58ac39ac0fef9ec8b547f947f095b3f2c07ab2753f79" in ledger


def test_v12_35_preregistered_capital_contract_is_retained() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "250-USDT-Wallet" in report
    assert "drei Plätze" in report
    assert "80 USDT je Platz" in report
    assert "vom Fill bis zum endgültigen Exit belegt" in report
