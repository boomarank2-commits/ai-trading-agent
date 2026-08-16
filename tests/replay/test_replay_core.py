from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from replay_core import MinuteBar, ReplayEngine, ReplayPolicy, StrategyDecision


def t(minutes: int = 0) -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minutes)


def bar(
    pair: str,
    minute: int,
    *,
    o: float = 100,
    h: float = 101,
    low: float = 99,
    close: float = 100,
) -> MinuteBar:
    return MinuteBar(
        pair=pair,
        open_time=t(minute),
        open=o,
        high=h,
        low=low,
        close=close,
        volume=1,
    )


def all_bars(minute: int, **btc):
    return {
        "BTC/USDT": bar("BTC/USDT", minute, **btc),
        "ETH/USDT": bar("ETH/USDT", minute, o=100, h=101, low=99, close=100),
        "SOL/USDT": bar("SOL/USDT", minute, o=100, h=101, low=99, close=100),
    }


def entry_decision(
    pair: str = "BTC/USDT", candle_minute: int = 0, price: float = 100
) -> StrategyDecision:
    return StrategyDecision(
        pair=pair,
        candle_open=t(candle_minute),
        reference_price=price,
        enter_long=True,
        enter_tag="golden",
        breakout_level=98,
        atr_4h=4,
    )


def test_signal_cannot_fill_before_15m_close_or_same_signal_candle() -> None:
    engine = ReplayEngine(start_time=t(0))
    decision = entry_decision(candle_minute=0)
    engine.submit_decision(decision)
    assert engine.state.now == t(15)
    assert not engine.state.positions
    engine.on_minute(all_bars(15))
    assert engine.state.positions["BTC/USDT"].opened_at == t(16)


def test_adverse_stop_wins_when_stop_and_roi_are_both_inside_same_detail_bar() -> None:
    engine = ReplayEngine(start_time=t(0), policy=ReplayPolicy(fee_per_side=0.0))
    engine.submit_decision(entry_decision())
    engine.on_minute(all_bars(15))
    assert "BTC/USDT" in engine.state.positions
    engine.on_minute(all_bars(16, o=100, h=160, low=90, close=120))
    assert engine.state.closed_trades[-1].exit_reason == "stop_loss"


def test_kill_switch_and_unhealthy_data_fail_closed_without_force_closing_position() -> None:
    engine = ReplayEngine(start_time=t(0), policy=ReplayPolicy(fee_per_side=0.0))
    engine.submit_decision(entry_decision("BTC/USDT"))
    engine.on_minute(all_bars(15))
    engine.set_kill_switch(True, t(16))
    assert "BTC/USDT" in engine.state.positions
    blocked = engine.entry_allowed("ETH/USDT", t(16), 80)
    assert not blocked.allowed and blocked.reason == "kill_switch"
    engine.set_kill_switch(False, t(16))
    engine.set_data_health(False, t(16), "stale")
    blocked = engine.entry_allowed("ETH/USDT", t(16), 80)
    assert not blocked.allowed and blocked.reason == "data_unhealthy"


def test_checkpoint_restart_is_deterministic(tmp_path: Path) -> None:
    policy = ReplayPolicy(fee_per_side=0.002)
    first = ReplayEngine(start_time=t(0), policy=policy)
    first.submit_decision(entry_decision())
    first.on_minute(all_bars(15))
    checkpoint = tmp_path / "checkpoint.json"
    first.save_checkpoint(checkpoint)
    expected_hash_before = first.checkpoint_hash()

    resumed = ReplayEngine.from_checkpoint(checkpoint, policy=policy)
    assert resumed.checkpoint_hash() == expected_hash_before
    for minute in range(16, 20):
        bars = all_bars(minute, o=100, h=101, low=99, close=100)
        first.on_minute(bars)
        resumed.on_minute(bars)
    assert first.checkpoint_hash() == resumed.checkpoint_hash()


def test_corrupt_checkpoint_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid replay checkpoint"):
        ReplayEngine.from_checkpoint(path)


def test_clock_must_be_monotone() -> None:
    engine = ReplayEngine(start_time=t(20))
    with pytest.raises(RuntimeError, match="moved backwards"):
        engine.entry_allowed("BTC/USDT", t(19), 80)
