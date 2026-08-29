from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
REPORT = ROOT / "research" / "V12_38_SOL_LTC_NO_TRADE_DE.md"
LEDGER = ROOT / "research" / "trial_ledger.csv"


def test_v12_38_higher_total_did_not_override_eth_preservation_gate() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert "v12_38_sol_no_validated_edge" not in source
    assert "ERHALTUNGSHÜRDE FÜR ETH VERFEHLT" in report
    assert "+453,234 USDT" in report
    assert "1,662 USDT" in report
    assert "df57d11fb3c5cc4d993d59f15859fae36efaa14a7184377b05c70ef833289d02" in ledger


def test_v12_38_slot_lifetime_contract_remains_explicit() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "höchstens drei offene 80-USDT-Blöcke" in report
    assert "Plätze bis" in report
    assert "vollständigen Trade-Exit belegt" in report
    assert "erst nach dem endgültigen Exit" in report
