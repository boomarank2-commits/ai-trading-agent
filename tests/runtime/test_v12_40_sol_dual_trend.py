from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVE = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
CANDIDATE = (
    ROOT
    / "research"
    / "rejected_strategies"
    / "CompressionBreakout250V1240.py"
)
REPORT = ROOT / "research" / "V12_40_SOL_DUAL_TREND_COMBINATION_DE.md"


def test_v12_40_combines_fixed_sol_families_without_mutating_active() -> None:
    active = ACTIVE.read_text(encoding="utf-8")
    candidate = CANDIDATE.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in active
    assert "v12_40_sol_donchian_plus_supertrend14x3_5" not in active
    assert 'STRATEGY_VERSION = "V12.40"' in candidate
    assert 'if pair != "SOL/USDT"' in candidate
    assert "period=14, multiplier=3.5" in candidate
    assert 'dataframe["adx_4h"] >= 20' in candidate
    assert 'dataframe["momentum_30d_4h"] >= 0.05' in candidate
    assert 'dataframe["rsi"] <= 72' in candidate
    assert "~active_sol_signal" in candidate


def test_v12_40_routes_exits_and_preserves_risk_contract() -> None:
    candidate = CANDIDATE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")

    assert 'dataframe["exit_long"] = 0' in candidate
    assert '"v12_40_sol_supertrend_short_flip"' in candidate
    assert 'return "v12_17_slow_trend_exit"' in candidate
    assert "genau einem 80-USDT-Block" in report
    assert "drei gleichzeitig belegte 80-USDT-Plätze" in report
    assert "dry_run: true" in report
    assert "4154d49d65d9d1d5915578d918fd7f2c095ac6af63392ea1a09bf497cf2af985" in report
    assert "ABGELEHNT" in report
    assert "+63,800 USDT" in report
    assert "6,362 USDT" in report
