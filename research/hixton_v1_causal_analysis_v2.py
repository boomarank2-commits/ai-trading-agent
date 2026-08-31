from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import hixton_v1_causal_analysis as base


def _segment_fat_tail_stats(
    universe: list[dict[str, Any]], removed: list[dict[str, Any]]
) -> dict[str, float]:
    winners = [r for r in universe if float(r["profit_abs"]) > 0]
    positive = [float(r["profit_abs"]) for r in winners]
    threshold = base.quantile(positive, 0.95)
    if not math.isfinite(threshold):
        return {
            "fat_tail_count": 0.0,
            "fat_tail_removed_count": 0.0,
            "fat_tail_removed_share": 0.0,
            "fat_tail_profit_pool": 0.0,
            "fat_tail_removed_profit": 0.0,
            "fat_tail_profit_removed_share": 0.0,
        }
    fat = [r for r in winners if float(r["profit_abs"]) >= threshold]
    removed_ids = {id(r) for r in removed}
    fat_removed = [r for r in fat if id(r) in removed_ids]
    pool = sum(float(r["profit_abs"]) for r in fat)
    removed_profit = sum(float(r["profit_abs"]) for r in fat_removed)
    return {
        "fat_tail_count": float(len(fat)),
        "fat_tail_removed_count": float(len(fat_removed)),
        "fat_tail_removed_share": len(fat_removed) / len(fat) if fat else 0.0,
        "fat_tail_profit_pool": pool,
        "fat_tail_removed_profit": removed_profit,
        "fat_tail_profit_removed_share": removed_profit / pool if pool else 0.0,
    }


def screen_entry_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same q20/q80 screen as V1 analysis, but fat-tail guards are segment-local.

    Winner/Fat-tail labels used for Discovery/Validation are calculated only from
    that segment's realized outcomes.  Holdout outcomes therefore cannot change
    the Discovery/Validation preservation guardrails.
    """
    output: list[dict[str, Any]] = []
    for pair in base.PAIRS:
        pair_rows = [r for r in rows if r["pair"] == pair]
        segment_map = base.chronological_segments(pair_rows)
        for row in pair_rows:
            row["segment"] = segment_map[id(row)]
        discovery = [r for r in pair_rows if r["segment"] == "discovery"]

        rules: list[tuple[str, str, float]] = []
        for feature in base.CONTINUOUS_FEATURES:
            values = [
                float(r[feature])
                for r in discovery
                if math.isfinite(float(r[feature]))
            ]
            if len(values) >= 50:
                rules.extend(
                    (
                        (feature, "low20", base.quantile(values, 0.20)),
                        (feature, "high20", base.quantile(values, 0.80)),
                    )
                )
        for feature in base.BOOL_FEATURES:
            rules.extend(((feature, "equals", 0.0), (feature, "equals", 1.0)))

        for feature, direction, threshold in rules:
            def remove(row: dict[str, Any]) -> bool:
                value = float(row[feature])
                if not math.isfinite(value):
                    return False
                if direction == "low20":
                    return value <= threshold
                if direction == "high20":
                    return value >= threshold
                return int(round(value)) == int(threshold)

            record: dict[str, Any] = {
                "pair": pair,
                "feature": feature,
                "direction": direction,
                "threshold_from_discovery": threshold,
            }
            segment_stats: dict[str, dict[str, float]] = {}
            for segment in ("discovery", "validation", "holdout"):
                universe = [r for r in pair_rows if r["segment"] == segment]
                removed = [r for r in universe if remove(r)]
                kept = [r for r in universe if not remove(r)]
                u, rm, kp = base.metrics(universe), base.metrics(removed), base.metrics(kept)
                trade_share = rm["trades"] / u["trades"] if u["trades"] else math.nan
                loss_share = (
                    rm["loss_damage"] / u["loss_damage"]
                    if u["loss_damage"]
                    else math.nan
                )
                winner_share = (
                    rm["winner_profit"] / u["winner_profit"]
                    if u["winner_profit"]
                    else math.nan
                )
                fat = _segment_fat_tail_stats(universe, removed)
                s = {
                    "removed_trades": rm["trades"],
                    "removed_net_pnl": rm["net_pnl"],
                    "trade_share": trade_share,
                    "loss_damage_share": loss_share,
                    "winner_profit_share": winner_share,
                    "damage_efficiency": loss_share / trade_share if trade_share else math.nan,
                    "winner_cost_efficiency": winner_share / trade_share if trade_share else math.nan,
                    "universe_pf": u["profit_factor"],
                    "kept_pf": kp["profit_factor"],
                    **fat,
                }
                segment_stats[segment] = s
                for key, value in s.items():
                    record[f"{segment}_{key}"] = value

            d = segment_stats["discovery"]
            v = segment_stats["validation"]
            h = segment_stats["holdout"]
            discovery_ok = (
                d["removed_trades"] >= 15
                and d["removed_net_pnl"] < 0
                and d["trade_share"] <= 0.35
                and d["damage_efficiency"] >= 1.35
                and (
                    math.isnan(d["winner_cost_efficiency"])
                    or d["winner_cost_efficiency"] <= 0.85
                )
                and d["fat_tail_removed_share"] <= 0.15
                and d["fat_tail_profit_removed_share"] <= 0.10
                and d["kept_pf"] > d["universe_pf"]
            )
            validation_ok = (
                v["removed_trades"] >= 5
                and v["removed_net_pnl"] < 0
                and v["damage_efficiency"] >= 1.10
                and v["fat_tail_removed_share"] <= 0.25
                and v["fat_tail_profit_removed_share"] <= 0.15
                and v["kept_pf"] >= v["universe_pf"]
            )
            record["candidate_selected_without_holdout"] = int(
                discovery_ok and validation_ok
            )
            record["holdout_supports_candidate"] = int(
                h["removed_trades"] > 0
                and h["removed_net_pnl"] < 0
                and h["damage_efficiency"] >= 1.0
                and h["fat_tail_profit_removed_share"] <= 0.15
                and h["kept_pf"] >= h["universe_pf"]
            )
            output.append(record)

    return sorted(
        output,
        key=lambda r: (
            -int(r["candidate_selected_without_holdout"]),
            -base.fnum(r["validation_damage_efficiency"]),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Leakage-hardened Hixton V1 causal entry analysis."
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("runtime/user_data/backtest_results/hixton"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research/reports/hixton_v1_causal"),
    )
    args = parser.parse_args()

    rows = base.load_diagnostic_trades(args.results_root)
    summary = base.build_coin_summary(rows)
    candidates = screen_entry_features(rows)
    queue = base.build_dead_trend_queue(rows)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    base.write_csv(out / "all_v1_trade_features.csv", rows)
    base.write_csv(out / "coin_summary.csv", summary)
    base.write_csv(out / "entry_feature_tail_screen.csv", candidates)
    base.write_csv(
        out / "entry_filter_candidates.csv",
        [r for r in candidates if int(r["candidate_selected_without_holdout"]) == 1],
    )
    base.write_csv(out / "dead_trend_research_queue.csv", queue)
    base.write_report(out / "V1_CAUSAL_ANALYSIS.md", summary, candidates, queue)
    (out / "analysis_manifest.json").write_text(
        json.dumps(
            {
                "experiment_id": base.EXPERIMENT_ID,
                "strategy_sha256": base.STRATEGY_SHA256,
                "trades": len(rows),
                "candidate_count_before_holdout": sum(
                    int(r["candidate_selected_without_holdout"]) for r in candidates
                ),
                "split": "chronological 60/20/20 per coin",
                "fat_tail_guard": "segment-local q95 plus profit-mass preservation; no holdout leakage into Discovery/Validation",
                "dead_trend_exit": "not simulated in this stage",
                "analysis_version": "causal-v2-safety",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Analyzed {len(rows)} trades with V2 safety guards; output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
