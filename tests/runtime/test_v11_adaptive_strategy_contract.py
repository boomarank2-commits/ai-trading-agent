from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def _source() -> str:
    return STRATEGY.read_text(encoding="utf-8")


def test_v12_6_is_pair_local_donchian_core_plus_fast_challenger() -> None:
    text = _source()
    assert 'STRATEGY_VERSION = "V12.6"' in text
    assert 'ALLOWED_PAIRS = {"BTC/USDT", "ETH/USDT", "SOL/USDT"}' in text
    assert "DONCHIAN_TREND" in text
    assert "FAST_DONCHIAN_TREND" in text
    assert "PAIR_PROFILES" in text
    assert '"BTC/USDT"' in text
    assert '"ETH/USDT"' in text
    assert '"SOL/USDT"' in text
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text


def test_v12_6_keeps_slow_core_and_adds_separate_fast_tags() -> None:
    text = _source()
    assert "donchian_entry" in text
    assert "donchian_exit" in text
    assert "donchian_fast_60" in text
    assert "donchian_fast_72" in text
    assert "donchian_fast_84" in text
    assert "slow_donchian" in text
    assert "fast_donchian" in text
    assert "fresh_breakout_4h" in text
    assert "fresh_fast_" in text


def test_v12_6_does_not_reintroduce_failed_v11_families() -> None:
    text = _source()
    assert "ORB_RETEST" not in text
    assert "ICHIMOKU_TREND" not in text
    assert "BOLLINGER_MR" not in text
    assert "orb_retest" not in text
    assert "_ichimoku" not in text
    assert "_bollinger_mr" not in text


def test_v12_6_does_not_clip_profitable_trends() -> None:
    text = _source()
    assert "roi_5pct" not in text
    assert "roi_2_5pct" not in text
    assert "roi_breakeven" not in text
    assert "current_profit >= 0" in text
    assert "v12_6_failed_fast_breakout" in text
    assert "v12_6_failed_slow_breakout" in text
    assert "v12_6_slow_trend_exit" in text


def test_v12_6_pair_profiles_are_deliberately_different() -> None:
    text = _source()
    assert '"fast_channel": "donchian_fast_72_4h"' in text
    assert '"fast_channel": "donchian_fast_84_4h"' in text
    assert '"fast_channel": "donchian_fast_60_4h"' in text
    assert '"fast_volume_ratio_min": 1.00' in text
    assert '"fast_volume_ratio_min": 1.05' in text
    assert '"fast_volume_ratio_min": 1.15' in text


def test_v12_6_keeps_safety_and_pair_local_protections() -> None:
    text = _source()
    assert "position_adjustment_enable = False" in text
    assert "max_entry_position_adjustment = 0" in text
    assert '"only_per_pair": True' in text
    assert "MAX_STAKE_USDT = 80.0" in text
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in text
    assert "MAX_OPEN_POSITIONS = 3" in text
    assert "stoploss = -0.055" in text
    assert "can_short = False" in text
