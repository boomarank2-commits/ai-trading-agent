from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from replay_core import MinuteBar, ReplayEngine, ReplayPolicy, StrategyDecision, final_metrics

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "golden_replay.json"


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def run_fixture() -> ReplayEngine:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    engine = ReplayEngine(
        start_time=parse(payload["start"]), policy=ReplayPolicy(fee_per_side=0.002)
    )
    for item in payload["decisions"]:
        item = dict(item)
        item["candle_open"] = parse(item["candle_open"])
        engine.submit_decision(StrategyDecision(**item))
    for item in payload["minutes"]:
        minute = parse(item["open_time"])
        o, h, low, close = item["btc"]
        bars = {
            "BTC/USDT": MinuteBar("BTC/USDT", minute, o, h, low, close, 1),
            "ETH/USDT": MinuteBar("ETH/USDT", minute, 100, 101, 99, 100, 1),
            "SOL/USDT": MinuteBar("SOL/USDT", minute, 100, 101, 99, 100, 1),
        }
        engine.on_minute(bars)
    return engine


def test_golden_replay_is_stable() -> None:
    engine = run_fixture()
    metrics = final_metrics(engine)
    assert metrics["trade_count"] == 1
    assert engine.state.closed_trades[0].exit_reason == "roi"
    assert round(engine.state.closed_trades[0].pnl_abs, 6) == 39.6
    # Checkpoint schema 2 intentionally fingerprints new execution/idempotency state.
    assert engine.checkpoint_hash() == "5a9208b026bba418896a2fbd7daa42149cc5a009db21e08d683d2a65f2b13ef9"
