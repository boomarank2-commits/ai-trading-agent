from __future__ import annotations

import math
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
        volume=10.0,
    )


def _entry(start: datetime, price: float = 100.0) -> StrategyDecision:
    return StrategyDecision(
        pair="BTC/USDT",
        candle_open=start,
        reference_price=price,
        enter_long=True,
        enter_tag="execution-test",
    )


def test_duplicate_minute_is_idempotent_and_conflict_fails_closed() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    engine = ReplayEngine(start_time=start)
    bar = _bar("BTC/USDT", start)
    engine.on_minute({"BTC/USDT": bar})
    checkpoint = engine.checkpoint_hash()

    engine.on_minute({"BTC/USDT": bar})
    assert engine.checkpoint_hash() == checkpoint

    conflicting = MinuteBar(
        pair="BTC/USDT",
        open_time=start,
        open=100.0,
        high=102.0,
        low=99.0,
        close=101.0,
        volume=10.0,
    )
    with pytest.raises(RuntimeError, match="conflicting duplicate"):
        engine.on_minute({"BTC/USDT": conflicting})


def test_execution_delay_requires_later_minute_before_fill() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = ReplayPolicy(execution_delay_minutes=1)
    engine = ReplayEngine(start_time=start, policy=policy)
    decision = _entry(start)
    engine.submit_decision(decision)

    engine.on_minute({"BTC/USDT": _bar("BTC/USDT", decision.known_at)})
    assert "BTC/USDT" not in engine.state.positions
    assert len(engine.state.orders) == 1

    engine.on_minute(
        {"BTC/USDT": _bar("BTC/USDT", decision.known_at + timedelta(minutes=1))}
    )
    assert "BTC/USDT" in engine.state.positions
    assert not engine.state.orders


def test_spread_is_applied_adversely_without_changing_default_signal() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = ReplayPolicy(spread_bps=20.0)
    engine = ReplayEngine(start_time=start, policy=policy)
    decision = _entry(start)
    engine.submit_decision(decision)
    engine.on_minute({"BTC/USDT": _bar("BTC/USDT", decision.known_at)})

    position = engine.state.positions["BTC/USDT"]
    assert math.isclose(position.entry_price, 100.1, rel_tol=0, abs_tol=1e-12)


def test_partial_entry_fills_across_two_touching_bars() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = ReplayPolicy(fill_fraction_per_touch=0.5)
    engine = ReplayEngine(start_time=start, policy=policy)
    decision = _entry(start)
    engine.submit_decision(decision)

    engine.on_minute({"BTC/USDT": _bar("BTC/USDT", decision.known_at)})
    position = engine.state.positions["BTC/USDT"]
    assert math.isclose(position.stake, 40.0)
    assert len(engine.state.orders) == 1
    order = next(iter(engine.state.orders.values()))
    assert math.isclose(order.filled_stake, 40.0)
    assert math.isclose(order.remaining_stake, 40.0)

    engine.on_minute(
        {"BTC/USDT": _bar("BTC/USDT", decision.known_at + timedelta(minutes=1))}
    )
    position = engine.state.positions["BTC/USDT"]
    assert math.isclose(position.stake, 80.0)
    assert math.isclose(position.initial_stake, 80.0)
    assert not engine.state.orders


def test_partial_exit_realizes_one_trade_after_second_fill() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = ReplayPolicy(fill_fraction_per_touch=0.5)
    engine = ReplayEngine(start_time=start, policy=policy)
    entry = _entry(start)
    engine.submit_decision(entry)
    engine.on_minute({"BTC/USDT": _bar("BTC/USDT", entry.known_at)})
    engine.on_minute(
        {"BTC/USDT": _bar("BTC/USDT", entry.known_at + timedelta(minutes=1))}
    )

    exit_decision = StrategyDecision(
        pair="BTC/USDT",
        candle_open=start + timedelta(minutes=15),
        reference_price=100.0,
        exit_long=True,
        exit_tag="manual_test_exit",
    )
    engine.submit_decision(exit_decision)
    engine.on_minute({"BTC/USDT": _bar("BTC/USDT", exit_decision.known_at)})
    assert "BTC/USDT" in engine.state.positions
    assert len(engine.state.closed_trades) == 0
    pending = next(iter(engine.state.orders.values()))
    assert pending.side == "sell"
    assert pending.filled_amount > 0

    engine.on_minute(
        {
            "BTC/USDT": _bar(
                "BTC/USDT", exit_decision.known_at + timedelta(minutes=1)
            )
        }
    )
    assert "BTC/USDT" not in engine.state.positions
    assert not engine.state.orders
    assert len(engine.state.closed_trades) == 1
    assert engine.state.closed_trades[0].exit_reason == "manual_test_exit"


def test_cancel_reject_extends_timeout_before_final_cancel() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = ReplayPolicy(entry_timeout_minutes=1, cancel_rejects_before_cancel=1)
    engine = ReplayEngine(start_time=start, policy=policy)
    decision = _entry(start, price=90.0)
    engine.submit_decision(decision)

    engine.on_minute({"BTC/USDT": _bar("BTC/USDT", decision.known_at, 100.0)})
    assert len(engine.state.orders) == 1
    order = next(iter(engine.state.orders.values()))
    assert order.cancel_reject_count == 1

    engine.on_minute(
        {
            "BTC/USDT": _bar(
                "BTC/USDT", decision.known_at + timedelta(minutes=1), 100.0
            )
        }
    )
    assert not engine.state.orders
    assert "BTC/USDT" not in engine.state.positions


def test_checkpoint_restores_partial_position_and_ignores_replayed_last_minute(
    tmp_path: Path,
) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = ReplayPolicy(fill_fraction_per_touch=0.5)
    engine = ReplayEngine(start_time=start, policy=policy)
    decision = _entry(start)
    engine.submit_decision(decision)
    bar = _bar("BTC/USDT", decision.known_at)
    engine.on_minute({"BTC/USDT": bar})
    assert math.isclose(engine.state.positions["BTC/USDT"].stake, 40.0)

    checkpoint = tmp_path / "replay.json"
    engine.save_checkpoint(checkpoint)
    restored = ReplayEngine.from_checkpoint(checkpoint, policy=policy)
    assert math.isclose(restored.state.positions["BTC/USDT"].stake, 40.0)
    assert len(restored.state.orders) == 1

    restored.on_minute({"BTC/USDT": bar})
    assert math.isclose(restored.state.positions["BTC/USDT"].stake, 40.0)
    assert len(restored.state.orders) == 1
