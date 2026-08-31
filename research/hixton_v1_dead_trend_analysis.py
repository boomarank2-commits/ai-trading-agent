from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

import hixton_v1_causal_analysis as causal

CHECKPOINT_MINUTES = (60, 120)
# Direction is preregistered from the meaning of each state variable, not selected from returns.
EXIT_FEATURES = {
    "giveback_fraction": "high20",
    "drawdown_from_high_atr": "high20",
    "bars_since_high": "high20",
    "price_minus_vidya_atr": "low20",
    "vidya_slope_4_atr": "low20",
    "macd_hist_atr": "low20",
    "trend_up_1h": "equals0",
}


def load_strategy_module(repo_root: Path):
    path = repo_root / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
    spec = importlib.util.spec_from_file_location("hixton_dead_trend_strategy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load strategy module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalize_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_feather(path)
    if "date" not in frame.columns:
        raise RuntimeError(f"Missing date column: {path}")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)


def hypothetical_exit_pnl(row: dict[str, Any], exit_rate: float) -> float:
    amount = float(row["amount"])
    open_rate = float(row["open_rate"])
    fee_open = float(row["fee_open"])
    fee_close = float(row["fee_close"])
    return (
        amount * (exit_rate - open_rate)
        - amount * open_rate * fee_open
        - amount * exit_rate * fee_close
    )


def completed_informative_state(frame: pd.DataFrame, at: pd.Timestamp, hours: int) -> dict[str, Any]:
    # Informative candle timestamp is its open time; it becomes causal only after it closes.
    eligible = frame.loc[frame["date"] + pd.Timedelta(hours=hours) <= at]
    if eligible.empty:
        return {}
    return eligible.iloc[-1].to_dict()


def first_activation_time(one_minute: pd.DataFrame, open_rate: float, threshold: float) -> pd.Timestamp | None:
    crossed = one_minute.loc[(one_minute["high"].astype(float) / open_rate - 1.0) >= threshold]
    if crossed.empty:
        return None
    return crossed.iloc[0]["date"]


def checkpoint_snapshot(
    trade: dict[str, Any],
    one_minute: pd.DataFrame,
    fifteen: pd.DataFrame,
    one_hour: pd.DataFrame,
    checkpoint_at: pd.Timestamp,
) -> dict[str, Any] | None:
    open_time = pd.to_datetime(trade["open_date"], utc=True)
    close_time = pd.to_datetime(trade["close_date"], utc=True)
    if checkpoint_at >= close_time:
        return None

    # Use the first fully completed 15m candle at/after the checkpoint.
    completed = fifteen.loc[
        (fifteen["date"] + pd.Timedelta(minutes=15) >= checkpoint_at)
        & (fifteen["date"] + pd.Timedelta(minutes=15) < close_time)
    ]
    if completed.empty:
        return None
    state = completed.iloc[0]
    state_time = state["date"] + pd.Timedelta(minutes=15)
    minute_path = one_minute.loc[(one_minute["date"] >= open_time) & (one_minute["date"] < state_time)]
    if minute_path.empty:
        return None

    highs = minute_path["high"].astype(float)
    running_high = float(highs.max())
    high_index = highs.idxmax()
    high_time = minute_path.loc[high_index, "date"]
    close_rate = float(state["close"])
    atr = float(state["hixton_atr"])
    running_mfe = running_high / float(trade["open_rate"]) - 1.0
    current_return = close_rate / float(trade["open_rate"]) - 1.0
    giveback = running_mfe - current_return
    one_hour_state = completed_informative_state(one_hour, state_time, 1)

    return {
        "checkpoint_time": state_time.isoformat(),
        "checkpoint_exit_rate": close_rate,
        "running_mfe": running_mfe,
        "current_return": current_return,
        "giveback_fraction": giveback / running_mfe if running_mfe > 0 else math.nan,
        "drawdown_from_high_atr": (running_high - close_rate) / atr if atr > 0 else math.nan,
        "bars_since_high": max(0.0, (state_time - high_time).total_seconds() / 900.0),
        "price_minus_vidya_atr": (close_rate - float(state["hixton_vidya"])) / atr if atr > 0 else math.nan,
        "vidya_slope_4_atr": float(state["diag_vidya_slope_4_atr"]),
        "macd_hist_atr": float(state["diag_macd_hist_atr"]),
        "trend_up_1h": float(bool(one_hour_state.get("hixton_trend_up", False))),
    }


def build_snapshots(repo_root: Path, results_root: Path, data_root: Path) -> list[dict[str, Any]]:
    strategy = load_strategy_module(repo_root)
    trades = causal.load_diagnostic_trades(results_root)
    output: list[dict[str, Any]] = []

    for pair in causal.PAIRS:
        coin = pair.split("/", 1)[0]
        prefix = f"{coin}_USDT"
        one_minute = normalize_frame(data_root / f"{prefix}-1m.feather")
        fifteen_raw = normalize_frame(data_root / f"{prefix}-15m.feather")
        one_hour_raw = normalize_frame(data_root / f"{prefix}-1h.feather")
        fifteen = strategy._diagnostic_state(fifteen_raw.copy())
        one_hour = strategy._diagnostic_state(one_hour_raw.copy())

        for trade in [r for r in trades if r["pair"] == pair]:
            open_time = pd.to_datetime(trade["open_date"], utc=True)
            close_time = pd.to_datetime(trade["close_date"], utc=True)
            path = one_minute.loc[(one_minute["date"] >= open_time) & (one_minute["date"] < close_time)]
            if path.empty:
                continue
            activation = first_activation_time(
                path,
                float(trade["open_rate"]),
                float(trade["break_even_mfe_ratio"]),
            )
            if activation is None:
                continue
            for minutes in CHECKPOINT_MINUTES:
                snap = checkpoint_snapshot(
                    trade, path, fifteen, one_hour, activation + pd.Timedelta(minutes=minutes)
                )
                if snap is None:
                    continue
                hypothetical = hypothetical_exit_pnl(trade, float(snap["checkpoint_exit_rate"]))
                output.append({
                    "pair": pair,
                    "trade_index": trade["trade_index"],
                    "open_timestamp": trade["open_timestamp"],
                    "outcome_class": trade["outcome_class"],
                    "is_fat_tail": trade["is_fat_tail"],
                    "original_profit_abs": trade["profit_abs"],
                    "activation_time": activation.isoformat(),
                    "checkpoint_minutes": minutes,
                    "hypothetical_exit_profit_abs": hypothetical,
                    "hypothetical_delta_abs": hypothetical - float(trade["profit_abs"]),
                    **snap,
                })
    return output


def segment_map(trades: list[dict[str, Any]]) -> dict[tuple[str, int], str]:
    result: dict[tuple[str, int], str] = {}
    for pair in causal.PAIRS:
        group = sorted([r for r in trades if r["pair"] == pair], key=lambda r: int(r["open_timestamp"]))
        for index, row in enumerate(group):
            fraction = (index + 0.5) / max(1, len(group))
            result[(pair, int(row["trade_index"]))] = (
                "discovery" if fraction < 0.60 else "validation" if fraction < 0.80 else "holdout"
            )
    return result


def screen_exit_candidates(snapshots: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping = segment_map(trades)
    for row in snapshots:
        row["segment"] = mapping[(row["pair"], int(row["trade_index"]))]
    output: list[dict[str, Any]] = []

    for pair in causal.PAIRS:
        for checkpoint in CHECKPOINT_MINUTES:
            group = [r for r in snapshots if r["pair"] == pair and int(r["checkpoint_minutes"]) == checkpoint]
            discovery = [r for r in group if r["segment"] == "discovery"]
            for feature, direction in EXIT_FEATURES.items():
                values = [float(r[feature]) for r in discovery if math.isfinite(float(r[feature]))]
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
                    delta = sum(float(r["hypothetical_delta_abs"]) for r in triggered)
                    dead = [r for r in rows if r["outcome_class"] == "PROFITABLE_THEN_LOST"]
                    dead_triggered = [r for r in triggered if r["outcome_class"] == "PROFITABLE_THEN_LOST"]
                    fat = [r for r in rows if int(r["is_fat_tail"]) == 1]
                    fat_triggered = [r for r in triggered if int(r["is_fat_tail"]) == 1]
                    record[f"{segment}_eligible_trades"] = len(rows)
                    record[f"{segment}_triggered_trades"] = len(triggered)
                    record[f"{segment}_delta_pnl"] = delta
                    record[f"{segment}_dead_trigger_rate"] = len(dead_triggered) / len(dead) if dead else math.nan
                    record[f"{segment}_fat_tail_trigger_rate"] = len(fat_triggered) / len(fat) if fat else 0.0

                discovery_ok = (
                    record["discovery_triggered_trades"] >= 10
                    and record["discovery_delta_pnl"] > 0
                    and record["discovery_fat_tail_trigger_rate"] <= 0.10
                )
                validation_ok = (
                    record["validation_triggered_trades"] >= 3
                    and record["validation_delta_pnl"] > 0
                    and record["validation_fat_tail_trigger_rate"] <= 0.20
                )
                record["selected_without_holdout"] = int(discovery_ok and validation_ok)
                record["holdout_supports"] = int(
                    record["holdout_delta_pnl"] > 0
                    and record["holdout_fat_tail_trigger_rate"] <= 0.20
                )
                output.append(record)
    return sorted(output, key=lambda r: (-int(r["selected_without_holdout"]), -float(r["validation_delta_pnl"])))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Causal dead-trend screen using the locked local 1m/15m/1h candle set.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--results-root", type=Path, default=Path("runtime/user_data/backtest_results/hixton"))
    parser.add_argument("--data-root", type=Path, default=Path("runtime/user_data/data/binance"))
    parser.add_argument("--output-dir", type=Path, default=Path("research/reports/hixton_v1_causal/dead_trend"))
    args = parser.parse_args()

    trades = causal.load_diagnostic_trades(args.results_root)
    snapshots = build_snapshots(args.repo_root, args.results_root, args.data_root)
    candidates = screen_exit_candidates(snapshots, trades)
    selected = [r for r in candidates if int(r["selected_without_holdout"]) == 1]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "dead_trend_checkpoint_snapshots.csv", snapshots)
    write_csv(args.output_dir / "dead_trend_candidate_screen.csv", candidates)
    write_csv(args.output_dir / "dead_trend_candidates_pre_holdout.csv", selected)
    (args.output_dir / "dead_trend_manifest.json").write_text(json.dumps({
        "activation": "exact fee break-even MFE, observed causally on 1m high",
        "checkpoints_minutes_after_activation": list(CHECKPOINT_MINUTES),
        "features": EXIT_FEATURES,
        "selection": "Discovery+Validation only; holdout report-only",
        "same_candle_protection": "checkpoint is at least 60 minutes after activation; exit uses completed 15m close",
        "selected_candidate_count": len(selected),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Snapshots: {len(snapshots)}; pre-holdout candidates: {len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
