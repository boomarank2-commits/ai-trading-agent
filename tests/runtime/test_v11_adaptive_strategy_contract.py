from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def _source() -> str:
    return STRATEGY.read_text(encoding="utf-8")


def test_v12_7_is_pair_local_slow_donchian_failure_control() -> None:
    text = _source()
    assert 'STRATEGY_VERSION = "V12.7"' in text
    assert 'ALLOWED_PAIRS = {"BTC/USDT", "ETH/USDT", "SOL/USDT"}' in text
    assert "DONCHIAN_TREND" in text
    assert "PAIR_PROFILES" in text
    assert '"BTC/USDT"' in text
    assert '"ETH/USDT"' in text
    assert '"SOL/USDT"' in text
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text


def test_v12_7_removes_rejected_fast_donchian_family() -> None:
    text = _source()
    assert "donchian_entry" in text
    assert "donchian_exit" in text
    assert "fresh_breakout_4h" in text
    assert "FAST_DONCHIAN_TREND" not in text
    assert "donchian_fast_60" not in text
    assert "donchian_fast_72" not in text
    assert "donchian_fast_84" not in text
    assert "fast_donchian" not in text


def test_v12_7_does_not_reintroduce_failed_v11_families() -> None:
    text = _source()
    assert "ORB_RETEST" not in text
    assert "ICHIMOKU_TREND" not in text
    assert "BOLLINGER_MR" not in text
    assert "orb_retest" not in text
    assert "_ichimoku" not in text
    assert "_bollinger_mr" not in text


def test_v12_7_pair_profiles_are_deliberately_different() -> None:
    text = _source()
    assert '"volume_min": 1.00' in text
    assert '"volume_override_adx": 24' in text
    assert '"persistence_bars": 4' in text
    assert '"failure_atr": 0.45' in text
    assert '"persistence_bars": 6' in text
    assert '"failure_atr": 0.35' in text
    assert '"failure_hours": 24' in text


def test_v12_7_keeps_winners_uncapped_and_uses_pair_failure_exit() -> None:
    text = _source()
    assert "roi_5pct" not in text
    assert "roi_2_5pct" not in text
    assert "roi_breakeven" not in text
    assert "current_profit >= 0" in text
    assert "entry_breakout_level" in text
    assert "entry_atr_4h" in text
    assert "failed_breakout" in text
    assert "v12_7_slow_trend_exit" in text


def test_v12_7_keeps_safety_and_pair_local_protections() -> None:
    text = _source()
    assert "position_adjustment_enable = False" in text
    assert "max_entry_position_adjustment = 0" in text
    assert '"only_per_pair": True' in text
    assert "MAX_STAKE_USDT = 80.0" in text
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in text
    assert "MAX_OPEN_POSITIONS = 3" in text
    assert "stoploss = -0.055" in text
    assert "can_short = False" in text
