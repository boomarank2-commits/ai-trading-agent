from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from replay_core import ReplayEngine, ReplayPolicy


def test_stale_or_failed_market_data_blocks_new_entries() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    engine = ReplayEngine(start_time=now, policy=ReplayPolicy())
    engine.set_data_health(False, now, "simulated websocket timeout")
    decision = engine.entry_allowed("BTC/USDT", now, 80)
    assert not decision.allowed
    assert decision.reason == "data_unhealthy"
    engine.set_data_health(True, now, "reconciled")
    assert engine.entry_allowed("BTC/USDT", now, 80).allowed
