from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def _source() -> str:
    return STRATEGY.read_text(encoding="utf-8")


def test_v12_5_is_pair_local_donchian_only() -> None:
    text = _source()
    assert 'STRATEGY_VERSION = "V12.5"' in text
    assert 'ALLOWED_PAIRS = {"BTC/USDT", "ETH/USDT", "SOL/USDT"}' in text
    assert "DONCHIAN_TREND" in text
    assert "fresh_breakout_4h" in text
    assert "donchian_entry" in text
    assert "donchian_exit" in text
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text


def test_v12_5_removed_failed_v11_entry_families() -> None:
    text = _source()
    assert "ORB_RETEST" not in text
    assert "ICHIMOKU_TREND" not in text
    assert "BOLLINGER_MR" not in text
    assert "orb_retest" not in text
    assert "_ichimoku" not in text
    assert "_bollinger_mr" not in text


def test_v12_5_defaults_to_no_trade_until_fresh_confirmed_breakout() -> None:
    text = _source()
    assert 'dataframe["regime_state"] = self.REGIME_NO_TRADE' in text
    assert 'dataframe["route_family"] = self.FAMILY_NO_TRADE' in text
    assert '"wait_fresh_4h_donchian"' in text
    assert '"wait_execution_gate"' in text
    assert 'dataframe.loc[signal, "route_family"] = self.FAMILY_DONCHIAN' in text


def test_v12_5_does_not_clip_profitable_trends_in_custom_exit() -> None:
    text = _source()
    assert "v12_4_roi_5pct" not in text
    assert "v12_4_roi_2_5pct" not in text
    assert "v12_4_roi_breakeven" not in text
    assert "v12_5_roi_5pct" not in text
    assert "v12_5_roi_2_5pct" not in text
    assert "v12_5_roi_breakeven" not in text
    assert "current_profit >= 0" in text
    assert "v12_5_failed_4h_breakout" in text
    assert "v12_5_slow_trend_exit" in text


def test_v12_5_keeps_safety_and_pair_local_protections() -> None:
    text = _source()
    assert "position_adjustment_enable = False" in text
    assert "max_entry_position_adjustment = 0" in text
    assert '"only_per_pair": True' in text
    assert "MAX_STAKE_USDT = 80.0" in text
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in text
    assert "MAX_OPEN_POSITIONS = 3" in text
    assert "stoploss = -0.055" in text
    assert "can_short = False" in text
