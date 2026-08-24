from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
REPORT = ROOT / "research" / "V12_36_SOL_SUPERTREND_IMPULSE_FIX_DE.md"
LEDGER = ROOT / "research" / "trial_ledger.csv"


def test_v12_36_is_an_implementation_abort_not_a_financial_reject() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert "v12_36_sol_supertrend14x3_5_impulse" not in source
    assert "UNGÜLTIGER LAUF" in report
    assert "ABORT_IMPLEMENTATION_MISMATCH" in report
    assert "d50e84dbc49689ad41346c8350b3a19512b26930340f1bf5dbd3dfcdbcf41724" in ledger


def test_v12_36_documents_why_the_old_exit_was_wrong() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "v12_17_sol_failed_breakout" in report
    assert "Exit nur per Supertrend-Shortflip" in report
    assert "endgültigen Trade-Exit" in report
