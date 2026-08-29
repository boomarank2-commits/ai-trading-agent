from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def test_v12_22_adds_only_the_registered_sol_adx_quality_branch() -> None:
    source = STRATEGY.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert 'elif pair == "SOL/USDT":' in source
    assert 'self.PAIR_PROFILES[pair]["adx_min"]' in source
    assert 'elif pair in self.BROAD_CORE_PAIRS:' in source


def test_v12_22_keeps_v12_20_capital_and_pyramiding_contracts() -> None:
    source = STRATEGY.read_text(encoding="utf-8")

    assert 'MAX_STAKE_USDT = 80.0' in source
    assert 'MAX_TOTAL_CAPITAL_USDT = 250.0' in source
    assert 'MAX_TOTAL_EXPOSURE_USDT = 240.0' in source
    assert 'MAX_OPEN_POSITIONS = 3' in source
    assert 'PYRAMIDING_PAIRS: ClassVar[set[str]]' in source
