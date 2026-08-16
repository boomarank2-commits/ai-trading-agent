from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from replay_research_analysis import analyze


def test_research_analysis_joins_decision_order_and_trade(tmp_path: Path) -> None:
    decision = {
        "pair": "BTC/USDT",
        "candle_open": "2026-01-01T00:00:00+00:00",
        "enter_candidate": True,
        "entry_allowed": True,
        "entry_order_id": "order-1",
        "features": {"volume_ratio": 0.8, "adx_4h": 18.0},
    }
    (tmp_path / "decisions.jsonl").write_text(
        json.dumps(decision) + "\n", encoding="utf-8"
    )
    event = {
        "type": "order_filled",
        "side": "buy",
        "order_id": "order-1",
        "trade_id": "trade-1",
    }
    (tmp_path / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    fields = [
        "trade_id",
        "pair",
        "opened_at",
        "closed_at",
        "entry_price",
        "exit_price",
        "stake",
        "amount",
        "entry_fee",
        "exit_fee",
        "pnl_abs",
        "pnl_ratio",
        "exit_reason",
        "enter_tag",
        "duration_minutes",
        "mae_ratio",
        "mfe_ratio",
    ]
    with (tmp_path / "trades.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "trade_id": "trade-1",
                "pair": "BTC/USDT",
                "opened_at": "x",
                "closed_at": "y",
                "entry_price": 100,
                "exit_price": 99,
                "stake": 80,
                "amount": 0.8,
                "entry_fee": 0.1,
                "exit_fee": 0.1,
                "pnl_abs": -1.0,
                "pnl_ratio": -0.0125,
                "exit_reason": "failed_4h_breakout",
                "enter_tag": "slow",
                "duration_minutes": 30,
                "mae_ratio": -0.02,
                "mfe_ratio": 0.01,
            }
        )
    result = analyze(tmp_path)
    assert result["trade_count"] == 1
    assert result["failed_4h_breakout"]["trades"] == 1
    assert result["volume_ratio_15m"]["[0.75,1.0)"]["trades"] == 1
