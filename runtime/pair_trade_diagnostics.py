"""Summarize preserved exact backtests without changing strategy rules.

The diagnostic reads Freqtrade result ZIPs, selects the newest run for each
pair/period/strategy hash and reports the error pattern which a later,
preregistered experiment must address.  It never executes a backtest and never
writes below the results directory.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile


def _number(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _result_payload(archive_path: Path) -> tuple[dict[str, Any], bytes]:
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        result_name = next(
            name
            for name in names
            if name.endswith(".json")
            and not name.endswith("_config.json")
            and not name.startswith("audit/")
        )
        source_name = next(
            name for name in names if name.endswith("_CompressionBreakout250.py")
        )
        payload = json.loads(archive.read(result_name))
        strategy = next(iter(payload["strategy"].values()))
        return strategy, archive.read(source_name)


def _chunks(trade: dict[str, Any]) -> int:
    initial = _number(trade.get("max_stake_amount")) or _number(trade.get("stake_amount"))
    final = _number(trade.get("stake_amount"))
    if initial <= 0 or final <= 0:
        return 1
    return max(1, min(3, round(final / min(initial, 80.0))))


def _chunk_attribution(trades: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Attribute realized P/L and occupied time to each entry fill.

    Freqtrade closes all fills in a position at the same final rate.  The
    exported entry-order cost already contains the entry fee, so an entry
    fill's realized marginal result is its fee-adjusted share of exit proceeds
    minus that cost.  This is accounting attribution, not a counterfactual:
    disabling a later fill can still change wallet chronology in a shared run.
    """

    buckets: dict[int, dict[str, float | int]] = defaultdict(
        lambda: {
            "fills": 0,
            "positive_fills": 0,
            "profit_usdt": 0.0,
            "slot_hours": 0.0,
        }
    )
    for trade in trades:
        close_rate = _number(trade.get("close_rate"))
        close_fee = _number(trade.get("fee_close"))
        close_timestamp = int(_number(trade.get("close_timestamp")))
        if close_rate <= 0:
            continue
        entries = sorted(
            (
                order
                for order in trade.get("orders", [])
                if isinstance(order, dict) and order.get("ft_is_entry") is True
            ),
            key=lambda order: _number(order.get("order_filled_timestamp")),
        )
        for ordinal, order in enumerate(entries, start=1):
            amount = _number(order.get("amount"))
            safe_price = _number(order.get("safe_price"))
            if amount <= 0 or safe_price <= 0:
                continue
            entry_cost = _number(order.get("cost"))
            if entry_cost <= 0:
                entry_cost = amount * safe_price * (1.0 + _number(trade.get("fee_open")))
            profit = amount * close_rate * (1.0 - close_fee) - entry_cost
            bucket = buckets[ordinal]
            bucket["fills"] = int(bucket["fills"]) + 1
            bucket["positive_fills"] = int(bucket["positive_fills"]) + int(profit > 0)
            bucket["profit_usdt"] = _number(bucket["profit_usdt"]) + profit
            fill_timestamp = int(_number(order.get("order_filled_timestamp")))
            if close_timestamp > fill_timestamp > 0:
                bucket["slot_hours"] = _number(bucket["slot_hours"]) + (
                    close_timestamp - fill_timestamp
                ) / 3_600_000.0

    return {
        f"chunk_{ordinal}": {
            "fills": int(values["fills"]),
            "positive_fills": int(values["positive_fills"]),
            "profit_usdt": round(_number(values["profit_usdt"]), 4),
            "average_profit_usdt": round(
                _number(values["profit_usdt"]) / max(int(values["fills"]), 1), 4
            ),
            "slot_hours": round(_number(values["slot_hours"]), 2),
        }
        for ordinal, values in sorted(buckets.items())
    }


def summarize_strategy(strategy: dict[str, Any]) -> dict[str, Any]:
    trades = [row for row in strategy.get("trades", []) if isinstance(row, dict)]
    profits = [_number(row.get("profit_abs")) for row in trades]
    positive = sorted((value for value in profits if value > 0), reverse=True)
    gross_profit = sum(positive)
    gross_loss = -sum(value for value in profits if value < 0)
    exit_reasons: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"trades": 0, "profit_usdt": 0.0}
    )
    entry_tags: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"trades": 0, "profit_usdt": 0.0}
    )
    years: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"trades": 0, "profit_usdt": 0.0}
    )
    mfe_values: list[float] = []
    mae_values: list[float] = []
    durations: list[float] = []
    chunk_counts: list[int] = []
    for trade in trades:
        profit = _number(trade.get("profit_abs"))
        reason = str(trade.get("exit_reason") or "unknown")
        tag = str(trade.get("enter_tag") or "without_tag")
        year = str(trade.get("open_date") or "unknown")[:4]
        for bucket, key in ((exit_reasons, reason), (entry_tags, tag), (years, year)):
            bucket[key]["trades"] = int(bucket[key]["trades"]) + 1
            bucket[key]["profit_usdt"] = _number(bucket[key]["profit_usdt"]) + profit
        entry = _number(trade.get("open_rate"))
        if entry > 0:
            mfe_values.append((_number(trade.get("max_rate")) / entry - 1.0) * 100.0)
            mae_values.append((_number(trade.get("min_rate")) / entry - 1.0) * 100.0)
        durations.append(_number(trade.get("trade_duration")) / 60.0)
        chunk_counts.append(_chunks(trade))

    def rounded_buckets(source: dict[str, dict[str, float | int]]) -> dict[str, dict[str, Any]]:
        return {
            key: {
                "trades": int(value["trades"]),
                "profit_usdt": round(_number(value["profit_usdt"]), 4),
            }
            for key, value in sorted(source.items())
        }

    return {
        "pair": str(trades[0].get("pair") if trades else strategy.get("pairlist", ["?"])[0]),
        "backtest_start": strategy.get("backtest_start"),
        "backtest_end": strategy.get("backtest_end"),
        "profit_usdt": round(sum(profits), 4),
        "trades": len(trades),
        "wins": sum(value > 0 for value in profits),
        "losses": sum(value < 0 for value in profits),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else 0.0,
        "top_1_winner_share_pct": round(positive[0] / gross_profit * 100.0, 2)
        if gross_profit
        else 0.0,
        "top_3_winner_share_pct": round(sum(positive[:3]) / gross_profit * 100.0, 2)
        if gross_profit
        else 0.0,
        "average_mfe_pct": round(sum(mfe_values) / len(mfe_values), 2) if mfe_values else 0.0,
        "average_mae_pct": round(sum(mae_values) / len(mae_values), 2) if mae_values else 0.0,
        "average_duration_hours": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "total_entry_chunks": sum(chunk_counts),
        "additional_entry_chunks": sum(max(value - 1, 0) for value in chunk_counts),
        "chunk_attribution": _chunk_attribution(trades),
        "exit_reasons": rounded_buckets(exit_reasons),
        "entry_tags": rounded_buckets(entry_tags),
        "open_years": rounded_buckets(years),
    }


def analyze(
    results_root: Path,
    *,
    strategy_hash: str = "",
    period_days: int = 1095,
) -> dict[str, Any]:
    selected: dict[str, tuple[int, Path, dict[str, Any]]] = {}
    for archive_path in results_root.rglob("*.zip"):
        try:
            strategy, source = _result_payload(archive_path)
        except (BadZipFile, KeyError, OSError, StopIteration, json.JSONDecodeError):
            continue
        import hashlib

        digest = hashlib.sha256(source).hexdigest()
        if strategy_hash and digest != strategy_hash:
            continue
        if int(strategy.get("backtest_days") or 0) != period_days:
            continue
        trades = strategy.get("trades") or []
        pairlist = strategy.get("pairlist") or []
        pair = str(trades[0].get("pair")) if trades else str(pairlist[0] if pairlist else "")
        if not pair or pair == "PORTFOLIO":
            continue
        stamp = int(strategy.get("backtest_run_end_ts") or archive_path.stat().st_mtime_ns)
        previous = selected.get(pair)
        if previous is None or stamp > previous[0]:
            summary = summarize_strategy(strategy)
            summary["archive"] = str(archive_path.resolve())
            summary["strategy_sha256"] = digest
            selected[pair] = (stamp, archive_path, summary)
    return {
        "schema_version": 1,
        "strategy_sha256_filter": strategy_hash or None,
        "period_days": period_days,
        "pairs": {pair: selected[pair][2] for pair in sorted(selected)},
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Pair-lokale Trade-Diagnose",
        "",
        f"Strategie-Hash: `{report.get('strategy_sha256_filter') or 'neuester je Pair'}`",
        "",
        "| Pair | P/L | Trades | PF | Top-1 Gewinner | MFE Ø | MAE Ø | Dauer Ø | Zusatzblöcke |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pair, row in report["pairs"].items():
        lines.append(
            f"| {pair} | {row['profit_usdt']:+.2f} | {row['trades']} | "
            f"{row['profit_factor']:.2f} | {row['top_1_winner_share_pct']:.1f} % | "
            f"{row['average_mfe_pct']:.1f} % | {row['average_mae_pct']:.1f} % | "
            f"{row['average_duration_hours']:.1f} h | {row['additional_entry_chunks']} |"
        )
    lines.extend(
        [
            "",
            "## Block-Attribution",
            "",
            "Die Werte teilen den realisierten Exit proportional auf die Entry-Fills auf. "
            "Sie sind eine Buchhaltungsattribution, kein gemeinsames Wallet-"
            "Gegenexperiment: Das Entfernen eines Blocks kann die spätere Slot- und "
            "Protection-Chronologie verändern.",
            "",
        ]
    )
    for pair, row in report["pairs"].items():
        chunks = row["chunk_attribution"]
        if len(chunks) <= 1:
            continue
        later_profit = sum(
            _number(chunk["profit_usdt"])
            for name, chunk in chunks.items()
            if name != "chunk_1"
        )
        later_fills = sum(
            int(chunk["fills"])
            for name, chunk in chunks.items()
            if name != "chunk_1"
        )
        lines.append(
            f"- {pair}: {later_fills} spätere Fills erzielten zusammen "
            f"{later_profit:+.2f} USDT."
        )
    for pair, row in report["pairs"].items():
        lines.extend(
            [
                "",
                f"## {pair}",
                "",
                f"- Exit-Gründe: `{json.dumps(row['exit_reasons'], ensure_ascii=False)}`",
                f"- Entry-Familien: `{json.dumps(row['entry_tags'], ensure_ascii=False)}`",
                f"- Eröffnungsjahre: `{json.dumps(row['open_years'], ensure_ascii=False)}`",
                "- Block-Attribution: `"
                f"{json.dumps(row['chunk_attribution'], ensure_ascii=False)}`",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--strategy-hash", default="")
    parser.add_argument("--period-days", type=int, default=1095)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    report = analyze(
        args.results_root,
        strategy_hash=args.strategy_hash,
        period_days=args.period_days,
    )
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = render_markdown(report)
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
