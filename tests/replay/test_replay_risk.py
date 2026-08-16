from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from replay_core import ClosedTrade, Position, ReplayEngine, ReplayPolicy


def test_daily_closed_loss_guard_blocks_new_entry() -> None:
    now = datetime(2026, 2, 1, 12, tzinfo=UTC)
    engine = ReplayEngine(start_time=now, policy=ReplayPolicy(fee_per_side=0.0))
    engine.state.closed_trades.append(
        ClosedTrade(
            trade_id="x",
            pair="BTC/USDT",
            opened_at=now - timedelta(hours=1),
            closed_at=now - timedelta(minutes=1),
            entry_price=100,
            exit_price=87.5,
            stake=80,
            amount=0.8,
            entry_fee=0,
            exit_fee=0,
            pnl_abs=-10.0,
            pnl_ratio=-0.125,
            exit_reason="failed_4h_breakout",
            enter_tag=None,
            duration_minutes=59,
            mae_ratio=-0.13,
            mfe_ratio=0.0,
        )
    )
    result = engine.entry_allowed("ETH/USDT", now, 80)
    assert not result.allowed
    assert result.reason == "daily_closed_loss"


def test_global_exposure_contract_is_240_not_three_independent_wallets() -> None:
    now = datetime(2026, 2, 1, tzinfo=UTC)
    engine = ReplayEngine(start_time=now, policy=ReplayPolicy(fee_per_side=0.0))
    for index, pair in enumerate(("BTC/USDT", "ETH/USDT", "SOL/USDT")):
        engine.state.positions[pair] = Position(
            trade_id=str(index),
            pair=pair,
            opened_at=now,
            entry_price=100,
            stake=80,
            amount=0.8,
            entry_fee=0,
            enter_tag=None,
            breakout_level=None,
            atr_4h=None,
            highest_rate=100,
            lowest_rate=100,
        )
    result = engine.entry_allowed("BTC/USDT", now, 1)
    assert not result.allowed
    assert result.reason in {"pair_already_open", "max_open_positions"}
    assert sum(position.stake for position in engine.state.positions.values()) == 240
