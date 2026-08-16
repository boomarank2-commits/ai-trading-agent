"""Post-run historical replay analysis without changing trading decisions."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_trades(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    numeric = {
        "entry_price",
        "exit_price",
        "stake",
        "amount",
        "entry_fee",
        "exit_fee",
        "pnl_abs",
        "pnl_ratio",
        "duration_minutes",
        "mae_ratio",
        "mfe_ratio",
    }
    for row in rows:
        for key in numeric:
            row[key] = float(row[key])
        row["opened_at"] = datetime.fromisoformat(str(row["opened_at"]))
        row["closed_at"] = datetime.fromisoformat(str(row["closed_at"]))
    return rows


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    wins = [row for row in rows if row["pnl_abs"] > 0]
    losses = [row for row in rows if row["pnl_abs"] < 0]
    gross_profit = sum(row["pnl_abs"] for row in wins)
    gross_loss = -sum(row["pnl_abs"] for row in losses)
    return {
        "trades": len(rows),
        "net_pnl": sum(row["pnl_abs"] for row in rows),
        "profit_factor": (
            gross_profit / gross_loss if gross_loss else (math.inf if gross_profit else 0.0)
        ),
        "win_rate_pct": len(wins) / len(rows) * 100 if rows else 0.0,
        "avg_trade": (
            sum(row["pnl_abs"] for row in rows) / len(rows) if rows else 0.0
        ),
        "avg_duration_minutes": (
            sum(row["duration_minutes"] for row in rows) / len(rows) if rows else 0.0
        ),
        "fees": sum(row["entry_fee"] + row["exit_fee"] for row in rows),
    }


def analyze(run_dir: Path) -> dict[str, Any]:
    trades = _load_trades(run_dir / "trades.csv")
    per_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_exit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trades:
        per_pair[str(row["pair"])].append(row)
        per_year[row["closed_at"].strftime("%Y")].append(row)
        per_month[row["closed_at"].strftime("%Y-%m")].append(row)
        per_exit[str(row["exit_reason"])].append(row)
    result = {
        "overall": _stats(trades),
        "per_pair": {key: _stats(value) for key, value in sorted(per_pair.items())},
        "per_year": {key: _stats(value) for key, value in sorted(per_year.items())},
        "per_month": {key: _stats(value) for key, value in sorted(per_month.items())},
        "per_exit_reason": {key: _stats(value) for key, value in sorted(per_exit.items())},
        "pnl_concentration": {},
    }
    sorted_winners = sorted(
        (row["pnl_abs"] for row in trades if row["pnl_abs"] > 0), reverse=True
    )
    total_net = result["overall"]["net_pnl"]
    for topn in (1, 3, 5, 10):
        contribution = sum(sorted_winners[:topn])
        result["pnl_concentration"][f"top_{topn}_winner_pnl"] = contribution
        result["pnl_concentration"][f"top_{topn}_winner_vs_net_pct"] = (
            contribution / total_net * 100 if total_net else None
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    result = analyze(args.run_dir)
    output = args.run_dir / "analysis.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
