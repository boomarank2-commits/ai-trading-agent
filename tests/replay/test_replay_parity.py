from __future__ import annotations

import json
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from replay_parity import compare_signal_decisions


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_signal_parity_uses_entry_and_exit_rows_separately(tmp_path: Path) -> None:
    paper = tmp_path / "paper.jsonl"
    replay = tmp_path / "replay.jsonl"
    key = "2026-01-01T00:00:00+00:00"
    write_jsonl(
        paper,
        [
            {
                "type": "strategy_signal_decision",
                "kind": "entry",
                "pair": "BTC/USDT",
                "candle_open_utc": key,
                "enter_long": True,
                "exit_long": False,
            },
            {
                "type": "strategy_signal_decision",
                "kind": "exit",
                "pair": "BTC/USDT",
                "candle_open_utc": key,
                "enter_long": True,
                "exit_long": True,
            },
        ],
    )
    write_jsonl(
        replay,
        [
            {
                "pair": "BTC/USDT",
                "candle_open": key,
                "enter_candidate": True,
                "exit_candidate": True,
            }
        ],
    )
    result = compare_signal_decisions(paper, replay)
    assert result["signal_parity"] is True
    assert result["signal_mismatches"] == 0
    assert result["entry"]["parity"] is True
    assert result["exit"]["parity"] is True
