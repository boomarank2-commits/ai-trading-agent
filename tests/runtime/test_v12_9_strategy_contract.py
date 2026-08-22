from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from runtime.user_data.strategies.CompressionBreakout250 import CompressionBreakout250

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
CURRENT_GUIDES = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "START_HERE_DE.md",
    REPO_ROOT / "BACKTEST_ANLEITUNG.md",
    REPO_ROOT / "TESTBOT_ANLEITUNG.md",
    REPO_ROOT / "runtime" / "README.md",
)


def _source() -> str:
    return STRATEGY.read_text(encoding="utf-8")


def test_current_guides_identify_v12_15_as_active_dry_run_candidate() -> None:
    for guide in CURRENT_GUIDES:
        text = guide.read_text(encoding="utf-8")
        assert "V12.15" in text, guide
        assert 'STRATEGY_VERSION = "V11"' not in text, guide


def test_v12_15_keeps_pair_local_champion_donchian_paths() -> None:
    text = _source()
    assert 'STRATEGY_VERSION = "V12.15"' in text
    for pair in ("BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT", "DOGE/USDT"):
        assert f'"{pair}"' in text
    assert 'FAMILY_DONCHIAN = "DONCHIAN_TREND"' in text
    assert "PAIR_PROFILES" in text
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text
    assert 'champion_quality = dataframe["volume_ratio"] >= 1.00' in text
    assert "v12_15_{asset}_champion_donchian" in text


def test_v12_15_keeps_only_the_preregistered_broad_core_pairs() -> None:
    text = _source()
    broad_core = text.split("BROAD_CORE_PAIRS", maxsplit=1)[1].split(
        "buy_momentum_30d", maxsplit=1
    )[0]
    assert '"SOL/USDT"' in broad_core
    assert '"XRP/USDT"' in broad_core
    assert '"BNB/USDT"' in broad_core
    assert '"DOGE/USDT"' in broad_core
    assert '"BTC/USDT"' not in broad_core
    assert '"ETH/USDT"' not in broad_core
    assert "elif pair in self.BROAD_CORE_PAIRS:" in text


def test_v12_15_keeps_v12_12_btc_and_eth_reclaims() -> None:
    text = _source()
    assert 'FAMILY_RECLAIM = "TREND_RECLAIM"' in text
    assert "RECLAIM_PROFILES" in text
    assert '"BTC/USDT": {' in text
    assert "pullback_touch_recent" in text
    assert "ema20_reclaim" in text
    assert "ema_exec_rising" in text
    assert 'if pair in self.RECLAIM_PROFILES:' in text
    assert "v12_15_{asset}_trend_reclaim" in text
    reclaim_block = (
        text.split("RECLAIM_PROFILES", maxsplit=1)[1]
        .split("REGIME_TREND", maxsplit=1)[0]
    )
    assert '"BTC/USDT"' in reclaim_block
    assert '"ETH/USDT"' in reclaim_block
    assert '"SOL/USDT"' not in reclaim_block
    assert '"XRP/USDT"' not in reclaim_block
    assert '"BNB/USDT"' not in reclaim_block
    assert '"DOGE/USDT"' not in reclaim_block


def test_v12_15_reclaim_is_causal_and_has_bounded_failure_logic() -> None:
    text = _source()
    assert ").shift(1)" in text
    assert "rolling(12, min_periods=1)" in text
    assert "shift(-" not in text
    assert 'if "_trend_reclaim" in enter_tag:' in text
    assert "age_hours <= 24.0" in text
    assert "entry_ema_fast_15m" in text
    assert "entry_atr_15m" in text
    assert "reclaim_failed" in text
    assert "age_hours >= 48.0" in text
    assert "reclaim_time_stop" in text


def test_v12_15_adds_only_the_preregistered_late_champion_ratchet() -> None:
    text = _source()
    assert "use_custom_stoploss = True" in text
    assert "def custom_stoploss(" in text
    assert '"_champion_donchian" not in enter_tag' in text
    assert "current_profit < 0.30" in text
    assert "stoploss_from_open(" in text
    assert "0.05," in text
    assert "current_profit < 0.05" not in text
    assert "roi_5pct" not in text
    assert "roi_2_5pct" not in text
    assert "roi_breakeven" not in text
    assert "minimal_roi: ClassVar[dict[str, float]] = {\"0\": 0.50}" in text


def test_v12_15_late_ratchet_ignores_reclaims_and_sub_30pct_champions() -> None:
    strategy = CompressionBreakout250.__new__(CompressionBreakout250)
    now = datetime(2026, 8, 22, tzinfo=UTC)
    champion = SimpleNamespace(
        enter_tag="v12_15_bnb_champion_donchian",
        is_short=False,
        leverage=1.0,
    )
    reclaim = SimpleNamespace(
        enter_tag="v12_15_btc_trend_reclaim",
        is_short=False,
        leverage=1.0,
    )

    assert strategy.custom_stoploss("BNB/USDT", champion, now, 130.0, 0.299, False) is None
    assert strategy.custom_stoploss("BTC/USDT", reclaim, now, 130.0, 0.40, False) is None
    assert strategy.custom_stoploss(
        "BNB/USDT", champion, now, 130.0, 0.30, False
    ) == pytest.approx(1 - (1.05 / 1.30))


def test_v12_15_restores_v12_12_pair_loss_wall() -> None:
    text = _source()
    assert '"method": "LowProfitPairs"' in text
    assert '"lookback_period_candles": 1344' in text
    assert '"trade_limit": 2' in text
    assert '"stop_duration_candles": 288' in text
    assert '"required_profit": 0.0' in text
    assert '"only_per_pair": True' in text


def test_v12_15_does_not_reintroduce_rejected_high_frequency_families() -> None:
    text = _source()
    assert "FAST_DONCHIAN_TREND" not in text
    assert "fast_donchian" not in text
    assert "ORB_RETEST" not in text
    assert "ICHIMOKU_TREND" not in text
    assert "BOLLINGER_MR" not in text
    assert "orb_retest" not in text
    assert "_ichimoku" not in text
    assert "_bollinger_mr" not in text


def test_v12_15_keeps_failed_breakout_and_execution_safety_contract() -> None:
    text = _source()
    assert "current_profit >= 0" in text
    assert "entry_breakout_level" in text
    assert "entry_atr_4h" in text
    assert "failed_breakout" in text
    assert "v12_15_slow_trend_exit" in text
    assert "position_adjustment_enable = False" in text
    assert "max_entry_position_adjustment = 0" in text
    assert "MAX_STAKE_USDT = 80.0" in text
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in text
    assert "MAX_OPEN_POSITIONS = 3" in text
    assert "stoploss = -0.055" in text
    assert "can_short = False" in text
