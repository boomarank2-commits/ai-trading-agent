from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "research" / "hixton_v6_route_c_portfolio_replay.py"
spec = importlib.util.spec_from_file_location("hixton_v6_route_c_portfolio_replay", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _row(
    pair: str,
    trade_index: int,
    open_date: str,
    close_date: str,
    profit: float,
    stake: float = 79.9,
) -> dict[str, object]:
    return {
        "pair": pair,
        "trade_index": trade_index,
        "open_date": open_date,
        "close_date": close_date,
        "profit_abs": profit,
        "stake_amount": stake,
    }


def test_simulator_releases_same_timestamp_close_before_entry() -> None:
    trades = pd.DataFrame(
        [
            _row("BTC/USDT", 1, "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", 1.0),
            _row("ETH/USDT", 1, "2026-01-01T00:00:00Z", "2026-01-01T03:00:00Z", 0.0),
            _row("SOL/USDT", 1, "2026-01-01T00:00:00Z", "2026-01-01T03:00:00Z", 0.0),
            _row("XRP/USDT", 1, "2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z", 2.0),
        ]
    )
    accepted, summary = module._simulate(trades, None)
    assert len(accepted) == 4
    assert summary["trades"] == 4
    assert abs(summary["profit_usdt"] - 3.0) < 1e-9


def test_route_exit_can_free_slot_for_new_opportunity() -> None:
    trades = pd.DataFrame(
        [
            _row("BTC/USDT", 1, "2026-01-01T00:00:00Z", "2026-01-01T04:00:00Z", -5.0),
            _row("ETH/USDT", 1, "2026-01-01T00:00:00Z", "2026-01-01T04:00:00Z", 0.0),
            _row("SOL/USDT", 1, "2026-01-01T00:00:00Z", "2026-01-01T04:00:00Z", 0.0),
            _row("DOGE/USDT", 1, "2026-01-01T02:00:00Z", "2026-01-01T03:00:00Z", -2.0),
        ]
    )
    baseline, _ = module._simulate(trades, None)
    exit_map = {
        ("BTC/USDT", 1): {
            "close_date": pd.Timestamp("2026-01-01T01:00:00Z"),
            "profit_abs": -1.0,
            "checkpoint": 60,
            "fold": "test",
        }
    }
    modified, _ = module._simulate(trades, exit_map)
    assert len(baseline) == 3
    assert len(modified) == 4
    assert int((modified["exit_kind"] != "v1").sum()) == 1


def test_pair_priority_is_explicit_and_stable() -> None:
    assert module.PAIR_ORDER[:4] == ("BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT")
    assert module.STARTING_WALLET == 250.0
    assert module.STAKE_REQUEST == 80.0
    assert module.MAX_OPEN == 3
