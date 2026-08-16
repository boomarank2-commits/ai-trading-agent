from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from v8_replay_adapter import V8ReplayAdapter

REPO = Path(__file__).resolve().parents[2]
STRATEGY = REPO / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
CONFIG = REPO / "runtime" / "user_data" / "config.json"


def frame(start: datetime, periods: int, minutes: int) -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=periods, freq=f"{minutes}min", tz="UTC")
    close = pd.Series([100.0 + index * 0.01 for index in range(periods)])
    return pd.DataFrame(
        {
            "date": dates,
            "open": close - 0.02,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
            "volume": 1000.0,
        }
    )


def test_informative_candle_is_not_visible_before_its_close() -> None:
    base = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-01-01T03:30:00Z",
                    "2026-01-01T03:45:00Z",
                    "2026-01-01T04:00:00Z",
                ],
                utc=True,
            ),
            "close": [1, 1, 1],
        }
    )
    info = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01T00:00:00Z"], utc=True),
            "close": [123.0],
        }
    )
    merged = V8ReplayAdapter._merge_informative(base, info, minutes=240, prefix="")
    assert pd.isna(merged.loc[0, "close_4h"])
    assert merged.loc[1, "close_4h"] == 123.0


def test_exact_v8_callbacks_build_replay_decisions() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw_sha = hashlib.sha256(STRATEGY.read_bytes()).hexdigest()
    adapter = V8ReplayAdapter(
        strategy_source=STRATEGY,
        strategy_sha256=raw_sha,
        strategy_class="CompressionBreakout250",
        config=config,
    )
    start = datetime(2025, 1, 1, tzinfo=UTC)
    candles_4h = frame(start, 600, 240)
    candles_1h = frame(start, 2400, 60)
    candles_15m = frame(start, 9600, 15)
    decision_start = start + timedelta(days=80)
    decision_end = decision_start + timedelta(days=2)
    decisions = adapter.decisions(
        pair="BTC/USDT",
        candles_15m=candles_15m,
        candles_1h=candles_1h,
        candles_4h=candles_4h,
        btc_4h=candles_4h,
        decision_start=decision_start,
        decision_end=decision_end,
    )
    assert len(decisions) > 100
    assert all(decision.known_at >= decision_start for decision in decisions)
    assert all(decision.known_at < decision_end for decision in decisions)
