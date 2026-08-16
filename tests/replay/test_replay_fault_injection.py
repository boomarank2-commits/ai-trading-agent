from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from replay_core import MinuteBar, ReplayEngine, ReplayPolicy, StrategyDecision


def _bar(pair: str, open_time: datetime, price: float = 100.0) -> MinuteBar:
    return MinuteBar(
        pair=pair,
        open_time=open_time,
        open=price,
        high=price + 1.0,
        low=price - 1.0,
        close=price,
        volume=1.0,
    )


def test_stale_or_failed_market_data_blocks_new_entries() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    engine = ReplayEngine(start_time=now, policy=ReplayPolicy())
    engine.set_data_health(False, now, "simulated websocket timeout")
    decision = engine.entry_allowed("BTC/USDT", now, 80)
    assert not decision.allowed
    assert decision.reason == "data_unhealthy"
    engine.set_data_health(True, now, "reconciled")
    assert engine.entry_allowed("BTC/USDT", now, 80).allowed


def test_kill_switch_is_fail_closed_and_recoverable() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    engine = ReplayEngine(start_time=now, policy=ReplayPolicy())
    engine.set_kill_switch(True, now)
    blocked = engine.entry_allowed("BTC/USDT", now, 80)
    assert not blocked.allowed
    assert blocked.reason == "kill_switch"
    engine.set_kill_switch(False, now)
    assert engine.entry_allowed("BTC/USDT", now, 80).allowed


def test_replay_rejects_backwards_clock() -> None:
    now = datetime(2026, 1, 1, 0, 10, tzinfo=UTC)
    engine = ReplayEngine(start_time=now, policy=ReplayPolicy())
    with pytest.raises(RuntimeError, match="replay clock moved backwards"):
        engine.entry_allowed("BTC/USDT", now - timedelta(minutes=1), 80)


def test_replay_rejects_misaligned_minute_batch() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    engine = ReplayEngine(start_time=now, policy=ReplayPolicy())
    bars = {
        "BTC/USDT": _bar("BTC/USDT", now),
        "ETH/USDT": _bar("ETH/USDT", now + timedelta(minutes=1)),
    }
    with pytest.raises(RuntimeError, match="must share one close time"):
        engine.on_minute(bars)


def test_replay_rejects_bar_mapping_pair_mismatch() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    engine = ReplayEngine(start_time=now, policy=ReplayPolicy())
    with pytest.raises(RuntimeError, match="bar mapping key/pair mismatch"):
        engine.on_minute({"ETH/USDT": _bar("BTC/USDT", now)})


def test_fill_time_risk_recheck_cancels_entry_when_data_turns_unhealthy() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    engine = ReplayEngine(start_time=start, policy=ReplayPolicy())
    decision = StrategyDecision(
        pair="BTC/USDT",
        candle_open=start,
        reference_price=100.0,
        enter_long=True,
        enter_tag="fault-test",
    )
    engine.submit_decision(decision)
    assert len(engine.state.orders) == 1

    engine.set_data_health(False, decision.known_at, "feed lost after signal")
    engine.on_minute({"BTC/USDT": _bar("BTC/USDT", decision.known_at)})

    assert not engine.state.orders
    assert "BTC/USDT" not in engine.state.positions


def test_unfilled_entry_times_out_without_creating_position() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = ReplayPolicy(entry_timeout_minutes=5)
    engine = ReplayEngine(start_time=start, policy=policy)
    decision = StrategyDecision(
        pair="BTC/USDT",
        candle_open=start,
        reference_price=90.0,
        enter_long=True,
        enter_tag="timeout-test",
    )
    engine.submit_decision(decision)
    assert len(engine.state.orders) == 1

    for minute in range(5):
        open_time = decision.known_at + timedelta(minutes=minute)
        engine.on_minute({"BTC/USDT": _bar("BTC/USDT", open_time, price=100.0)})

    assert not engine.state.orders
    assert "BTC/USDT" not in engine.state.positions
