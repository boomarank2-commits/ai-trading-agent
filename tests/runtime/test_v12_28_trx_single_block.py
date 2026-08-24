import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def test_rejected_v12_28_is_not_left_active() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    pyramid_set = source.split("PYRAMIDING_PAIRS", 1)[1].split("}", 1)[0]

    assert 'STRATEGY_VERSION = "V12.28"' not in source
    assert '"v12_27_trx_donchian40_trend"' not in source
    assert '"v12_27_trx_donchian40_exit"' not in source
    assert '"TRX/USDT",' in pyramid_set
    assert '"BTC/USDT",' in pyramid_set
    assert '"ETH/USDT",' in pyramid_set
    assert '"LINK/USDT",' in pyramid_set


def test_v12_22_sol_and_capital_contracts_remain_active() -> None:
    source = STRATEGY.read_text(encoding="utf-8")

    assert 'elif pair == "SOL/USDT":' in source
    assert 'self.PAIR_PROFILES[pair]["adx_min"]' in source
    assert "MAX_STAKE_USDT = 80.0" in source
    assert "MAX_TOTAL_CAPITAL_USDT = 250.0" in source
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in source
    assert "MAX_OPEN_POSITIONS = 3" in source


def test_v12_28_rejection_is_permanently_recorded() -> None:
    ledger = ROOT / "research" / "trial_ledger.csv"
    with ledger.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    row = next(
        item
        for item in rows
        if item["experiment_id"] == "V12.28-TRX40-SINGLE-BLOCK"
    )

    assert row["status"] == "REJECT_BACKTEST_SYSTEM_GATE"
    assert row["decision"] == "REJECT_DO_NOT_PROMOTE"
    assert row["net_return"] == "271.929"
