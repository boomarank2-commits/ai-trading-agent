from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

import hixton_v1_causal_analysis as causal
import hixton_v1_dead_trend_analysis as base

CHECKPOINT_MINUTES = base.CHECKPOINT_MINUTES
EXIT_FEATURES = base.EXIT_FEATURES


def first_confirmed_activation_time(
    one_minute: pd.DataFrame, open_rate: float, threshold: float
) -> pd.Timestamp | None:
    """Require a completed 1m close above fee break-even, not only an intraminute wick."""
    crossed = one_minute.loc[
        (one_minute["close"].astype(float) / open_rate - 1.0) >= threshold
    ]
    if crossed.empty:
        return None
    return crossed.iloc[0]["date"] + pd.Timedelta(minutes=1)


def checkpoint_snapshot_v2(
    trade: dict[str, Any],
    one_minute: pd.DataFrame,
    fifteen: pd.DataFrame,
    one_hour: pd.DataFrame,
    checkpoint_at: pd.Timestamp,
) -> dict[str, Any] | None:
    """Build state from completed candles and execute at the following 1m open.

    Freqtrade exit signals are evaluated on a completed candle and backtesting
    fills them at the consecutive candle open.  The feature state therefore
    remains the completed 15m close, while P/L uses the first 1m open at/after
    the signal time.
    """
    snap = base.checkpoint_snapshot(
        trade, one_minute, fifteen, one_hour, checkpoint_at
    )
    if snap is None:
        return None
    signal_time = pd.to_datetime(snap["checkpoint_time"], utc=True)
    close_time = pd.to_datetime(trade["close_date"], utc=True)
    execution_rows = one_minute.loc[
        (one_minute["date"] >= signal_time) & (one_minute["date"] < close_time)
    ]
    if execution_rows.empty:
        return None
    execution = execution_rows.iloc[0]
    signal_close_rate = float(snap["checkpoint_exit_rate"])
    snap["signal_close_rate"] = signal_close_rate
    snap["checkpoint_exit_rate"] = float(execution["open"])
    snap["execution_time"] = execution["date"].isoformat()
    snap["execution_model"] = "first_1m_open_after_completed_15m_signal"
    return snap


def build_snapshots(
    repo_root: Path, results_root: Path, data_root: Path
) -> list[dict[str, Any]]:
    strategy = base.load_strategy_module(repo_root)
    trades = causal.load_diagnostic_trades(results_root)
    output: list[dict[str, Any]] = []

    for pair in causal.PAIRS:
        coin = pair.split("/", 1)[0]
        prefix = f"{coin}_USDT"
        one_minute = base.normalize_frame(data_root / f"{prefix}-1m.feather")
        fifteen_raw = base.normalize_frame(data_root / f"{prefix}-15m.feather")
        one_hour_raw = base.normalize_frame(data_root / f"{prefix}-1h.feather")
        fifteen = strategy._diagnostic_state(fifteen_raw.copy())
        one_hour = strategy._diagnostic_state(one_hour_raw.copy())

        for trade in [r for r in trades if r["pair"] == pair]:
            open_time = pd.to_datetime(trade["open_date"], utc=True)
            close_time = pd.to_datetime(trade["close_date"], utc=True)
            path = one_minute.loc[
                (one_minute["date"] >= open_time) & (one_minute["date"] < close_time)
            ]
            if path.empty:
                continue
            activation = first_confirmed_activation_time(
                path,
                float(trade["open_rate"]),
                float(trade["break_even_mfe_ratio"]),
            )
            if activation is None:
                continue
            for minutes in CHECKPOINT_MINUTES:
                snap = checkpoint_snapshot_v2(
                    trade,
                    path,
                    fifteen,
                    one_hour,
                    activation + pd.Timedelta(minutes=minutes),
                )
                if snap is None:
                    continue
                hypothetical = base.hypothetical_exit_pnl(
                    trade, float(snap["checkpoint_exit_rate"])
                )
                output.append(
                    {
                        "pair": pair,
                        "trade_index": trade["trade_index"],
                        "open_timestamp": trade["open_timestamp"],
                        "outcome_class": trade["outcome_class"],
                        "original_profit_abs": trade["profit_abs"],
                        "activation_time": activation.isoformat(),
                        "activation_model": "first_completed_1m_close_at_or_above_fee_break_even",
                        "checkpoint_minutes": minutes,
                        "hypothetical_exit_profit_abs": hypothetical,
                        "hypothetical_delta_abs": hypothetical
                        - float(trade["profit_abs"]),
                        **snap,
                    }
                )
    return output


def _segment_fat_tails(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    winners = [r for r in rows if float(r["original_profit_abs"]) > 0]
    threshold = causal.quantile(
        [float(r["original_profit_abs"]) for r in winners], 0.95
    )
    if not math.isfinite(threshold):
        return []
    return [r for r in winners if float(r["original_profit_abs"]) >= threshold]


def screen_exit_candidates(
    snapshots: list[dict[str, Any]], trades: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    mapping = base.segment_map(trades)
    for row in snapshots:
        row["segment"] = mapping[(row["pair"], int(row["trade_index"]))]
    output: list[dict[str, Any]] = []

    for pair in causal.PAIRS:
        for checkpoint in CHECKPOINT_MINUTES:
            group = [
                r
                for r in snapshots
                if r["pair"] == pair and int(r["checkpoint_minutes"]) == checkpoint
            ]
            discovery = [r for r in group if r["segment"] == "discovery"]
            for feature, direction in EXIT_FEATURES.items():
                values = [
                    float(r[feature])
                    for r in discovery
                    if math.isfinite(float(r[feature]))
                ]
                if feature == "trend_up_1h":
                    threshold = 0.0
                elif len(values) < 30:
                    continue
                elif direction == "high20":
                    threshold = causal.quantile(values, 0.80)
                else:
                    threshold = causal.quantile(values, 0.20)

                def trigger(row: dict[str, Any]) -> bool:
                    value = float(row[feature])
                    if not math.isfinite(value):
                        return False
                    if direction == "high20":
                        return value >= threshold
                    if direction == "low20":
                        return value <= threshold
                    return int(round(value)) == 0

                record: dict[str, Any] = {
                    "pair": pair,
                    "checkpoint_minutes": checkpoint,
                    "feature": feature,
                    "direction": direction,
                    "threshold_from_discovery": threshold,
                }

                for segment in ("discovery", "validation", "holdout"):
                    rows = [r for r in group if r["segment"] == segment]
                    triggered = [r for r in rows if trigger(r)]
                    dead = [
                        r
                        for r in rows
                        if r["outcome_class"] == "PROFITABLE_THEN_LOST"
                    ]
                    dead_triggered = [
                        r
                        for r in triggered
                        if r["outcome_class"] == "PROFITABLE_THEN_LOST"
                    ]
                    winners = [r for r in rows if float(r["original_profit_abs"]) > 0]
                    winner_triggered = [
                        r for r in triggered if float(r["original_profit_abs"]) > 0
                    ]
                    fat = _segment_fat_tails(rows)
                    fat_ids = {id(r) for r in fat}
                    fat_triggered = [r for r in triggered if id(r) in fat_ids]

                    delta = sum(float(r["hypothetical_delta_abs"]) for r in triggered)
                    winner_delta = sum(
                        float(r["hypothetical_delta_abs"]) for r in winner_triggered
                    )
                    fat_delta = sum(
                        float(r["hypothetical_delta_abs"]) for r in fat_triggered
                    )
                    winner_pool = sum(float(r["original_profit_abs"]) for r in winners)
                    fat_pool = sum(float(r["original_profit_abs"]) for r in fat)
                    trigger_share = len(triggered) / len(rows) if rows else math.nan
                    dead_base_rate = len(dead) / len(rows) if rows else math.nan
                    dead_precision = (
                        len(dead_triggered) / len(triggered) if triggered else math.nan
                    )
                    dead_enrichment = (
                        dead_precision / dead_base_rate
                        if dead_base_rate and math.isfinite(dead_precision)
                        else math.nan
                    )

                    record[f"{segment}_eligible_trades"] = len(rows)
                    record[f"{segment}_triggered_trades"] = len(triggered)
                    record[f"{segment}_trigger_share"] = trigger_share
                    record[f"{segment}_delta_pnl"] = delta
                    record[f"{segment}_dead_base_rate"] = dead_base_rate
                    record[f"{segment}_dead_precision"] = dead_precision
                    record[f"{segment}_dead_enrichment"] = dead_enrichment
                    record[f"{segment}_dead_trigger_rate"] = (
                        len(dead_triggered) / len(dead) if dead else math.nan
                    )
                    record[f"{segment}_winner_trigger_rate"] = (
                        len(winner_triggered) / len(winners) if winners else 0.0
                    )
                    record[f"{segment}_winner_delta_pnl"] = winner_delta
                    record[f"{segment}_winner_profit_damage_share"] = (
                        max(0.0, -winner_delta) / winner_pool if winner_pool else 0.0
                    )
                    record[f"{segment}_fat_tail_trigger_rate"] = (
                        len(fat_triggered) / len(fat) if fat else 0.0
                    )
                    record[f"{segment}_fat_tail_delta_pnl"] = fat_delta
                    record[f"{segment}_fat_tail_profit_damage_share"] = (
                        max(0.0, -fat_delta) / fat_pool if fat_pool else 0.0
                    )

                discovery_ok = (
                    record["discovery_triggered_trades"] >= 10
                    and record["discovery_delta_pnl"] > 0
                    and record["discovery_trigger_share"] <= 0.35
                    and record["discovery_dead_enrichment"] >= 1.20
                    and record["discovery_fat_tail_trigger_rate"] <= 0.10
                    and record["discovery_winner_profit_damage_share"] <= 0.05
                    and record["discovery_fat_tail_profit_damage_share"] <= 0.05
                )
                validation_ok = (
                    record["validation_triggered_trades"] >= 3
                    and record["validation_delta_pnl"] > 0
                    and record["validation_trigger_share"] <= 0.35
                    and record["validation_dead_enrichment"] >= 1.05
                    and record["validation_fat_tail_trigger_rate"] <= 0.20
                    and record["validation_winner_profit_damage_share"] <= 0.10
                    and record["validation_fat_tail_profit_damage_share"] <= 0.10
                )
                record["selected_without_holdout"] = int(
                    discovery_ok and validation_ok
                )
                record["holdout_supports"] = int(
                    record["holdout_delta_pnl"] > 0
                    and record["holdout_trigger_share"] <= 0.35
                    and record["holdout_dead_enrichment"] >= 1.0
                    and record["holdout_fat_tail_trigger_rate"] <= 0.20
                    and record["holdout_winner_profit_damage_share"] <= 0.10
                    and record["holdout_fat_tail_profit_damage_share"] <= 0.10
                )
                output.append(record)

    return sorted(
        output,
        key=lambda r: (
            -int(r["selected_without_holdout"]),
            -float(r["validation_delta_pnl"]),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safety-hardened causal dead-trend screen using local 1m/15m/1h candles."
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("runtime/user_data/backtest_results/hixton"),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("runtime/user_data/data/binance"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research/reports/hixton_v1_causal/dead_trend"),
    )
    args = parser.parse_args()

    trades = causal.load_diagnostic_trades(args.results_root)
    snapshots = build_snapshots(args.repo_root, args.results_root, args.data_root)
    candidates = screen_exit_candidates(snapshots, trades)
    selected = [r for r in candidates if int(r["selected_without_holdout"]) == 1]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base.write_csv(args.output_dir / "dead_trend_checkpoint_snapshots.csv", snapshots)
    base.write_csv(args.output_dir / "dead_trend_candidate_screen.csv", candidates)
    base.write_csv(
        args.output_dir / "dead_trend_candidates_pre_holdout.csv", selected
    )
    (args.output_dir / "dead_trend_manifest.json").write_text(
        json.dumps(
            {
                "activation": "first completed 1m close at/above exact fee break-even",
                "checkpoints_minutes_after_activation": list(CHECKPOINT_MINUTES),
                "features": EXIT_FEATURES,
                "selection": "Discovery+Validation only; holdout report-only",
                "execution": "first 1m open after completed 15m signal, matching next-candle-open semantics",
                "fat_tail_guard": "segment-local q95 plus winner/fat-tail profit-mass damage caps",
                "targeting_guard": "dead-trend enrichment required; max 35% eligible trades triggered",
                "same_candle_protection": "activation is confirmed on a completed 1m close; signal uses completed 15m state; execution is subsequent 1m open",
                "selected_candidate_count": len(selected),
                "analysis_version": "dead-trend-v2-safety",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Snapshots: {len(snapshots)}; safety-qualified pre-holdout candidates: {len(selected)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
