from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def _source() -> str:
    return STRATEGY.read_text(encoding="utf-8")


def _literal_assignment(name: str):
    tree = ast.parse(_source())
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"assignment {name!r} not found")


def test_v11_has_three_pair_local_profiles_and_no_cross_pair_regime_callback() -> None:
    profiles = _literal_assignment("PAIR_PROFILES")
    assert set(profiles) == {"BTC/USDT", "ETH/USDT", "SOL/USDT"}
    assert profiles["BTC/USDT"] != profiles["ETH/USDT"]
    assert profiles["ETH/USDT"] != profiles["SOL/USDT"]

    text = _source()
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text
    assert "btc_close_4h" not in text
    assert "btc_ema" not in text


def test_v11_router_contains_all_regimes_families_and_no_trade_fallback() -> None:
    text = _source()
    for value in (
        "TREND/BREAKOUT",
        "RANGE/MEAN_REVERSION",
        "NO_TRADE",
        "ORB_RETEST",
        "ICHIMOKU_TREND",
        "BOLLINGER_MR",
        "regime_unclear",
        "trend_wait_setup",
        "range_wait_setup",
        "cost_gate",
    ):
        assert value in text


def test_v11_cost_gate_requires_more_than_stressed_roundtrip_fee() -> None:
    profiles = _literal_assignment("PAIR_PROFILES")
    stressed_roundtrip_fee = 0.002 * 2.0 * 1.50
    for profile in profiles.values():
        assert profile["min_gross_move"] > stressed_roundtrip_fee

    text = _source()
    assert "ROUNDTRIP_COST_STRESS" in text
    assert "mr_projected_move" in text
    assert "orb_projected_move" in text
    assert "ichi_projected_move" in text


def test_v11_ichimoku_is_causal_and_contains_no_negative_shift() -> None:
    text = _source()
    assert ".shift(-" not in text
    assert 'dataframe["cloud_a"] = projected_a.shift(26)' in text
    assert 'dataframe["cloud_b"] = projected_b.shift(26)' in text
    assert 'dataframe["close"] > dataframe["high"].shift(26)' in text
    assert 'frame.loc[frame["date"] <= current_time]' in text


def test_v11_orb_uses_completed_utc_opening_range_before_entries() -> None:
    text = _source()
    assert "minutes_utc < 60" in text
    assert "minutes_utc >= 60" in text
    assert "orb_breakout_recent" in text
    assert "orb_retest_atr" in text


def test_v11_family_specific_exits_are_bound_to_entry_tag() -> None:
    text = _source()
    assert "use_exit_signal = False" in text
    assert '"_bollinger_mr" in tag' in text
    assert '"_orb_retest" in tag' in text
    assert '"_ichimoku" in tag' in text
    assert "mr_midband" in text
    assert "orb_invalidation" in text
    assert "ichi_local_break" in text


def test_v11_keeps_pair_local_risk_and_no_position_stacking() -> None:
    text = _source()
    assert "position_adjustment_enable = False" in text
    assert "max_entry_position_adjustment = 0" in text
    assert '"only_per_pair": True' in text
    assert "MAX_STAKE_USDT = 80.0" in text
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in text
    assert "MAX_OPEN_POSITIONS = 3" in text
