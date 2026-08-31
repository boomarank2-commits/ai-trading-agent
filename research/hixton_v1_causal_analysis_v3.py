from __future__ import annotations

import argparse
import json
from pathlib import Path

import hixton_v1_causal_analysis as base
import hixton_v1_causal_analysis_v2 as safety_v2
import hixton_v1_coherent_batch as cohort


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cohort-locked Hixton V1 causal entry analysis."
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

    rows, cohort_meta = cohort.load_locked_diagnostic_trades(args.results_root)
    summary = base.build_coin_summary(rows)
    candidates = safety_v2.screen_entry_features(rows)
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
                "fat_tail_guard": "segment-local q95 plus profit-mass preservation",
                "cohort_lock": cohort_meta,
                "analysis_version": "causal-v3-cohort-lock",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Analyzed locked cohort: {len(rows)} trades; batch={cohort_meta['batch_id']}; "
        f"output: {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
