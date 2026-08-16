"""Immutable per-run telemetry and report writer for historical live replay."""

from __future__ import annotations

import contextlib
import csv
import json
import os
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from replay_core import ClosedTrade, ReplayEngine, ReplaySink, final_metrics


class JsonlReplaySink(ReplaySink):
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._paths = {
            "decision": self.run_dir / "decisions.jsonl",
            "event": self.run_dir / "events.jsonl",
            "error": self.run_dir / "errors.jsonl",
            "equity": self.run_dir / "equity.jsonl",
        }

    @staticmethod
    def _append(path: Path, payload: Mapping[str, Any]) -> None:
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(dict(payload), sort_keys=True, ensure_ascii=False))
            stream.write("\n")
            stream.flush()
            with contextlib.suppress(OSError):
                os.fsync(stream.fileno())

    def decision(self, payload: Mapping[str, Any]) -> None:
        self._append(self._paths["decision"], payload)

    def event(self, payload: Mapping[str, Any]) -> None:
        self._append(self._paths["event"], payload)

    def error(self, payload: Mapping[str, Any]) -> None:
        self._append(self._paths["error"], payload)

    def equity(self, payload: Mapping[str, Any]) -> None:
        self._append(self._paths["equity"], payload)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(dict(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(raw, encoding="utf-8", newline="\n")
    temp.replace(path)


def write_trades_csv(path: Path, trades: list[ClosedTrade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for trade in trades:
            row = asdict(trade)
            row["opened_at"] = trade.opened_at.isoformat()
            row["closed_at"] = trade.closed_at.isoformat()
            writer.writerow(row)


def finalize_run(run_dir: Path, engine: ReplayEngine, manifest: Mapping[str, Any]) -> None:
    write_json_atomic(run_dir / "manifest.json", manifest)
    write_json_atomic(run_dir / "metrics.json", final_metrics(engine))
    write_trades_csv(run_dir / "trades.csv", engine.state.closed_trades)
