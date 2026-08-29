from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
REPORT = ROOT / "research" / "V12_37_SOL_SUPERTREND_EXIT_ISOLATION_DE.md"
LEDGER = ROOT / "research" / "trial_ledger.csv"


def test_v12_37_positive_but_too_small_sample_is_rejected() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert "v12_37_sol_supertrend14x3_5_impulse" not in source
    assert "VERWORFEN" in report
    assert "+31,960 USDT" in report
    assert "10 Trades statt mindestens 12" in report
    assert "56ad3d2263795828ad3280b1937e1e794aeea8b1caa5849bb114b2752abcbcf2" in ledger


def test_v12_37_did_not_open_later_gates_after_first_gate_failed() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "Jüngstes Jahr, Kosten- und" in report
    assert "Shared-Gate werden nicht nachgeschoben" in report
    assert "Freigabe erst nach dem endgültigen" in report
