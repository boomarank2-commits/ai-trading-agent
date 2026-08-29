from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVE = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
CANDIDATE = (
    ROOT
    / "research"
    / "rejected_strategies"
    / "CompressionBreakout250V1239.py"
)
REPORT = ROOT / "research" / "V12_39_XRP_7D_MOMENTUM_DE.md"


def test_v12_39_is_pair_local_and_does_not_mutate_active_v12_33() -> None:
    active = ACTIVE.read_text(encoding="utf-8")
    candidate = CANDIDATE.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in active
    assert "v12_39_xrp_7d_momentum" not in active
    assert 'STRATEGY_VERSION = "V12.39"' in candidate
    assert 'if pair != "XRP/USDT"' in candidate
    assert 'dataframe["xrp_momentum_7d"]' in candidate
    assert 'dataframe["adx_4h"] >= 18' in candidate
    assert "0.05" in candidate


def test_v12_39_preserves_capital_and_preregistration_contract() -> None:
    candidate = CANDIDATE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")

    assert "class CompressionBreakout250V1239(CompressionBreakout250)" in candidate
    assert "genau einen 80-USDT-Block" in report
    assert "drei gleichzeitig belegte 80-USDT-" in report
    assert "dry_run: true" in report
    assert "7d12e06a96d6286fa7730204bdcf937b8490a94e7424a5ea53b0dc8a7339e480" in report
    assert "ABGELEHNT" in report
    assert "18,459 USDT" in report
    assert "c24bac1eaf7a3710697be21de864312949b6aa58dc97835a205462bdfc96cd35" in report
