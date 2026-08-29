from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
REPORT = ROOT / "research" / "V12_34_SOL_RANGE_REVERSION_DE.md"
LEDGER = ROOT / "research" / "trial_ledger.csv"


def test_v12_34_rejection_is_immutable_and_not_active() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert "v12_34_sol_range_overreaction_reversion" not in source
    assert "VERWORFEN" in report
    assert "4,055 USDT" in report
    assert "Profit-Faktor **0,44**" in report
    assert "a640fec71c2a7a44f9993d848ce74fac8ae6762eebea2fe42cc01bc33ed898a6" in ledger


def test_v12_34_preserved_the_preregistered_slot_gate() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "+421,9152 USDT" in report
    assert "mindestens 2,4530" in report
    assert "höchstens 12,1794 Prozent" in report
    assert "erst nach dem endgültigen Exit" in report
