"""Diagnose V8 failed breakouts, volume quality and causal regime attribution.

The script is read-only. It consumes one replay run and never changes the
strategy or its parameters. Results are descriptive research evidence only.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL {path}:{line_no}") from exc
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _trades(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        return {row["trade_id"]: row for row in csv.DictReader(stream)}


def _bucket(value: float | None, cuts: tuple[float, ...]) -> str:
    if value is None:
        return "missing"
    lower = "-inf"
    for cut in cuts:
        if value < cut:
            return f"[{lower},{cut})"
        lower = str(cut)
    return f"[{lower},+inf)"


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnl = [_float(row.get("pnl_abs")) or 0.0 for row in rows]
    wins = [value for value in pnl if value > 0]
    losses = [-value for value in pnl if value < 0]
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    return {
        "trades": len(rows),
        "net_pnl": sum(pnl),
        "profit_factor": (
            gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)
        ),
        "win_rate_pct": len(wins) / len(rows) * 100.0 if rows else 0.0,
    }


def analyze(run_dir: Path) -> dict[str, Any]:
    decisions = _jsonl(run_dir / "decisions.jsonl")
    events = _jsonl(run_dir / "events.jsonl")
    trades = _trades(run_dir / "trades.csv")

    decision_by_order = {
        str(row["entry_order_id"]): row
        for row in decisions
        if row.get("entry_order_id")
    }
    trade_to_order: dict[str, str] = {}
    for event in events:
        if event.get("type") == "order_filled" and event.get("side") == "buy":
            trade_id = event.get("trade_id")
            order_id = event.get("order_id")
            if trade_id and order_id:
                trade_to_order[str(trade_id)] = str(order_id)

    joined: list[dict[str, Any]] = []
    for trade_id, trade in trades.items():
        order_id = trade_to_order.get(trade_id)
        decision = decision_by_order.get(order_id or "", {})
        joined.append(
            {
                **trade,
                "decision": decision,
                "features": decision.get("features", {}),
            }
        )

    def group_feature(feature: str, cuts: tuple[float, ...]) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in joined:
            value = _float(row.get("features", {}).get(feature))
            grouped[_bucket(value, cuts)].append(row)
        return {key: _stats(value) for key, value in sorted(grouped.items())}

    failed = [row for row in joined if row.get("exit_reason") == "failed_4h_breakout"]
    candidate_rows = [row for row in decisions if row.get("enter_candidate")]
    rejection_reasons: dict[str, int] = defaultdict(int)
    for row in candidate_rows:
        reason = row.get("entry_rejection_reason")
        if reason:
            rejection_reasons[str(reason)] += 1

    return {
        "warning": (
            "retrospective descriptive analysis only; do not select new thresholds from this "
            "output without a new pre-registered experiment"
        ),
        "trade_count": len(joined),
        "failed_4h_breakout": _stats(failed),
        "entry_candidates": len(candidate_rows),
        "entry_rejection_reasons": dict(sorted(rejection_reasons.items())),
        "volume_ratio_15m": group_feature("volume_ratio", (0.75, 1.0, 1.25, 1.5, 2.0)),
        "breakout_distance_atr": group_feature(
            "breakout_distance_atr", (0.0, 0.25, 0.5, 1.0, 2.0)
        ),
        "adx_4h": group_feature("adx_4h", (16.0, 20.0, 25.0, 32.0)),
        "momentum_30d_4h": group_feature(
            "momentum_30d_4h", (0.03, 0.05, 0.10, 0.20, 0.40)
        ),
        "atr_pct_15m": group_feature("atr_pct", (0.003, 0.005, 0.01, 0.02, 0.04)),
        "btc_regime_up": group_feature("btc_regime_up", (0.5,)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    result = analyze(args.run_dir)
    output = args.run_dir / "research_analysis.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
