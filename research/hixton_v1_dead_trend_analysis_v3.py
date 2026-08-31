from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import hixton_v1_causal_analysis as causal
import hixton_v1_coherent_batch as cohort
import hixton_v1_dead_trend_analysis as base
import hixton_v1_dead_trend_analysis_v2 as safety_v2

CHECKPOINT_MINUTES = safety_v2.CHECKPOINT_MINUTES


def build_snapshots(
    repo_root: Path,
    trades: list[dict],
    data_root: Path,
) -> list[dict]:
    strategy = base.load_strategy_module(repo_root)
    output: list[dict] = []

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
            activation = safety_v2.first_confirmed_activation_time(
                path,
                float(trade["open_rate"]),
                float(trade["break_even_mfe_ratio"]),
            )
            if activation is None:
                continue
            for minutes in CHECKPOINT_MINUTES:
                snap = safety_v2.checkpoint_snapshot_v2(
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
                        "hypothetical_delta_abs": hypothetical - float(trade["profit_abs"]),
                        **snap,
                    }
                )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cohort-locked safety-hardened Hixton dead-trend screen."
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

    trades, cohort_meta = cohort.load_locked_diagnostic_trades(args.results_root)
    snapshots = build_snapshots(args.repo_root, trades, args.data_root)
    candidates = safety_v2.screen_exit_candidates(snapshots, trades)
    selected = [r for r in candidates if int(r["selected_without_holdout"]) == 1]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base.write_csv(args.output_dir / "dead_trend_checkpoint_snapshots.csv", snapshots)
    base.write_csv(args.output_dir / "dead_trend_candidate_screen.csv", candidates)
    base.write_csv(args.output_dir / "dead_trend_candidates_pre_holdout.csv", selected)
    (args.output_dir / "dead_trend_manifest.json").write_text(
        json.dumps(
            {
                "activation": "first completed 1m close at/above exact fee break-even",
                "checkpoints_minutes_after_activation": list(CHECKPOINT_MINUTES),
                "features": safety_v2.EXIT_FEATURES,
                "selection": "Discovery+Validation only; holdout report-only",
                "execution": "first 1m open after completed 15m signal",
                "fat_tail_guard": "segment-local q95 plus winner/fat-tail profit-mass damage caps",
                "targeting_guard": "dead-trend enrichment required; max 35% eligible trades triggered",
                "cohort_lock": cohort_meta,
                "selected_candidate_count": len(selected),
                "analysis_version": "dead-trend-v3-cohort-lock",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Locked batch={cohort_meta['batch_id']}; snapshots={len(snapshots)}; "
        f"safety-qualified pre-holdout candidates={len(selected)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
