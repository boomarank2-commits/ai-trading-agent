from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def _source() -> str:
    return STRATEGY.read_text(encoding="utf-8")


def test_v12_8_is_pair_local_champion_donchian_candidate() -> None:
    text = _source()
    assert 'STRATEGY_VERSION = "V12.8"' in text
    assert 'ALLOWED_PAIRS = {"BTC/USDT", "ETH/USDT", "SOL/USDT"}' in text
    assert "DONCHIAN_TREND" in text
    assert "PAIR_PROFILES" in text
    assert '"BTC/USDT"' in text
    assert '"ETH/USDT"' in text
    assert '"SOL/USDT"' in text
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text


def test_v12_8_uses_pair_specific_champion_entries() -> None:
    text = _source()
    assert "donchian_entry" in text
    assert "donchian_exit" in text
    assert "fresh_breakout_4h" in text
    assert 'if pair == "BTC/USDT"' in text
    assert 'pair_quality = dataframe["volume_ratio"] >= 1.00' in text
    assert 'elif pair == "ETH/USDT"' in text
    assert '"persistence_bars": 4' in text
    assert 'pair_quality = dataframe["volume"] > 0' in text
    assert "v12_8_{asset}_champion_donchian" in text


def test_v12_8_does_not_reintroduce_rejected_high_frequency_families() -> None:
    text = _source()
    assert "FAST_DONCHIAN_TREND" not in text
    assert "donchian_fast_60" not in text
    assert "donchian_fast_72" not in text
    assert "donchian_fast_84" not in text
    assert "fast_donchian" not in text
    assert "ORB_RETEST" not in text
    assert "ICHIMOKU_TREND" not in text
    assert "BOLLINGER_MR" not in text
    assert "orb_retest" not in text
    assert "_ichimoku" not in text
    assert "_bollinger_mr" not in text


def test_v12_8_tests_sol_only_profit_ratchet_without_profit_cap() -> None:
    text = _source()
    assert "use_custom_stoploss = True" in text
    assert "def custom_stoploss(" in text
    assert "stoploss_from_open" in text
    assert 'pair != "SOL/USDT" or current_profit < 0.05' in text
    assert "0.01," in text
    assert "roi_5pct" not in text
    assert "roi_2_5pct" not in text
    assert "roi_breakeven" not in text
    assert "minimal_roi: ClassVar[dict[str, float]] = {\"0\": 0.50}" in text


def test_v12_8_keeps_failed_breakout_exit_and_safety_contract() -> None:
    text = _source()
    assert "current_profit >= 0" in text
    assert "entry_breakout_level" in text
    assert "entry_atr_4h" in text
    assert "failed_breakout" in text
    assert "v12_8_slow_trend_exit" in text
    assert "position_adjustment_enable = False" in text
    assert "max_entry_position_adjustment = 0" in text
    assert '"only_per_pair": True' in text
    assert "MAX_STAKE_USDT = 80.0" in text
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in text
    assert "MAX_OPEN_POSITIONS = 3" in text
    assert "stoploss = -0.055" in text
    assert "can_short = False" in text
