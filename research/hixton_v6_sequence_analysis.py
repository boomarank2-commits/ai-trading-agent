from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_TRADES = 6328
EXPECTED_SNAPSHOTS = 9848
Q_LOW = 0.20
Q_HIGH = 0.80

WINDOWS = (
    ("F1_2024-09_to_2025-02", "2024-09-01T00:00:00Z", "2025-03-01T00:00:00Z"),
    ("F2_2025-03_to_2025-08", "2025-03-01T00:00:00Z", "2025-09-01T00:00:00Z"),
    ("F3_2025-09_to_2026-02", "2025-09-01T00:00:00Z", "2026-03-01T00:00:00Z"),
    ("F4_2026-03_to_2026-08", "2026-03-01T00:00:00Z", "2026-09-01T00:00:00Z"),
)

ROUTE_A = "ROUTE_A_60_GIVEBACK_MACD_1H"
ROUTE_B = "ROUTE_B_120_STRUCTURE_MACD_1H"
ROUTE_C = "ROUTE_C_TWO_STAGE"
ROUTES = (ROUTE_A, ROUTE_B, ROUTE_C)

MIN_POSITIVE_FOLDS = 3
MIN_TRIGGERS_PER_FOLD = 15
MAX_TRIGGER_SHARE = 0.20
MIN_DEAD_ENRICHMENT = 1.05
MAX_WINNER_DAMAGE_SHARE = 0.10
MAX_FAT_TAIL_DAMAGE_SHARE = 0.10
MAX_FAT_TAIL_TRIGGER_RATE = 0.20
MIN_POSITIVE_COINS = 6


@dataclass(frozen=True)
class Thresholds:
    giveback_q80: float
    macd_q20: float
    price_vidya_q20: float


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_inputs(
    trades: pd.DataFrame,
    snapshots: pd.DataFrame,
    causal_manifest: dict[str, Any],
    dead_manifest: dict[str, Any],
) -> None:
    if len(trades) != EXPECTED_TRADES:
        raise RuntimeError(f"Expected {EXPECTED_TRADES} V1 trades, got {len(trades)}")
    if len(snapshots) != EXPECTED_SNAPSHOTS:
        raise RuntimeError(
            f"Expected {EXPECTED_SNAPSHOTS} cohort-locked checkpoint snapshots, got {len(snapshots)}"
        )

    causal_lock = causal_manifest.get("cohort_lock") or {}
    dead_lock = dead_manifest.get("cohort_lock") or {}
    if int(causal_lock.get("total_trades") or 0) != EXPECTED_TRADES:
        raise RuntimeError("Causal manifest is not the locked 6328-trade cohort")
    if int(dead_lock.get("total_trades") or 0) != EXPECTED_TRADES:
        raise RuntimeError("Dead-trend manifest is not the locked 6328-trade cohort")
    if causal_manifest.get("analysis_version") != "causal-v3-cohort-lock":
        raise RuntimeError("Expected causal-v3-cohort-lock analysis manifest")
    if dead_manifest.get("analysis_version") != "dead-trend-v3-cohort-lock":
        raise RuntimeError("Expected dead-trend-v3-cohort-lock manifest")

    required_trade = {
        "pair",
        "trade_index",
        "open_date",
        "profit_abs",
        "outcome_class",
    }
    required_snap = {
        "pair",
        "trade_index",
        "checkpoint_minutes",
        "checkpoint_time",
        "hypothetical_exit_profit_abs",
        "giveback_fraction",
        "macd_hist_atr",
        "price_minus_vidya_atr",
        "trend_up_1h",
    }
    if not required_trade.issubset(trades.columns):
        raise RuntimeError(f"Trade file missing columns: {sorted(required_trade - set(trades.columns))}")
    if not required_snap.issubset(snapshots.columns):
        raise RuntimeError(f"Snapshot file missing columns: {sorted(required_snap - set(snapshots.columns))}")
    if trades[["pair", "trade_index"]].duplicated().any():
        raise RuntimeError("Trade file contains duplicate pair/trade_index rows")


def _build_thresholds(train: pd.DataFrame) -> dict[tuple[str, int], Thresholds]:
    output: dict[tuple[str, int], Thresholds] = {}
    for (pair, checkpoint), frame in train.groupby(["pair", "checkpoint_minutes"]):
        if len(frame) < 20:
            continue
        output[(str(pair), int(checkpoint))] = Thresholds(
            giveback_q80=float(frame["giveback_fraction"].quantile(Q_HIGH)),
            macd_q20=float(frame["macd_hist_atr"].quantile(Q_LOW)),
            price_vidya_q20=float(frame["price_minus_vidya_atr"].quantile(Q_LOW)),
        )
    return output


def _route_a_trigger(row: pd.Series, thresholds: dict[tuple[str, int], Thresholds]) -> bool:
    if int(row["checkpoint_minutes"]) != 60:
        return False
    key = (str(row["pair"]), 60)
    threshold = thresholds.get(key)
    if threshold is None:
        return False
    return bool(
        float(row["giveback_fraction"]) >= threshold.giveback_q80
        and float(row["macd_hist_atr"]) <= threshold.macd_q20
        and int(row["trend_up_1h"]) == 0
    )


def _route_b_trigger(row: pd.Series, thresholds: dict[tuple[str, int], Thresholds]) -> bool:
    if int(row["checkpoint_minutes"]) != 120:
        return False
    key = (str(row["pair"]), 120)
    threshold = thresholds.get(key)
    if threshold is None:
        return False
    return bool(
        float(row["macd_hist_atr"]) <= threshold.macd_q20
        and float(row["price_minus_vidya_atr"]) <= threshold.price_vidya_q20
        and int(row["trend_up_1h"]) == 0
    )


def _route_eligible(route: str, frame: pd.DataFrame) -> bool:
    checkpoints = set(int(value) for value in frame["checkpoint_minutes"].tolist())
    if route == ROUTE_A:
        return 60 in checkpoints
    if route == ROUTE_B:
        return 120 in checkpoints
    return bool(checkpoints.intersection({60, 120}))


def _choose_exit(
    route: str,
    frame: pd.DataFrame,
    thresholds: dict[tuple[str, int], Thresholds],
) -> pd.Series | None:
    ordered = frame.sort_values("checkpoint_minutes")
    if route == ROUTE_A:
        selected = ordered[ordered.apply(lambda row: _route_a_trigger(row, thresholds), axis=1)]
    elif route == ROUTE_B:
        selected = ordered[ordered.apply(lambda row: _route_b_trigger(row, thresholds), axis=1)]
    elif route == ROUTE_C:
        selected_rows = []
        for _, row in ordered.iterrows():
            checkpoint = int(row["checkpoint_minutes"])
            if checkpoint == 60 and _route_a_trigger(row, thresholds):
                selected_rows.append(row)
                break
            if checkpoint == 120 and _route_b_trigger(row, thresholds):
                selected_rows.append(row)
                break
        return selected_rows[0] if selected_rows else None
    else:
        raise ValueError(f"Unknown route {route}")
    return selected.iloc[0] if not selected.empty else None


def _mark_local_fat_tails(decisions: pd.DataFrame) -> pd.Series:
    fat = pd.Series(False, index=decisions.index)
    eligible_winners = decisions[(decisions["eligible"] == 1) & (decisions["original_profit_abs"] > 0)]
    for pair, frame in eligible_winners.groupby("pair"):
        threshold = float(frame["original_profit_abs"].quantile(0.95))
        mask = (
            (decisions["pair"] == pair)
            & (decisions["eligible"] == 1)
            & (decisions["original_profit_abs"] > 0)
            & (decisions["original_profit_abs"] >= threshold)
        )
        fat.loc[mask] = True
    return fat


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _evaluate_window(
    route: str,
    trades: pd.DataFrame,
    snapshots: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    train = snapshots[snapshots["checkpoint_time"] < start]
    thresholds = _build_thresholds(train)
    test_trades = trades[(trades["open_date"] >= start) & (trades["open_date"] < end)].copy()
    test_keys = test_trades[["pair", "trade_index"]]
    test_snapshots = snapshots.merge(test_keys, on=["pair", "trade_index"], how="inner")
    grouped = {
        (str(pair), int(trade_index)): frame
        for (pair, trade_index), frame in test_snapshots.groupby(["pair", "trade_index"])
    }

    rows: list[dict[str, Any]] = []
    for trade in test_trades.itertuples(index=False):
        key = (str(trade.pair), int(trade.trade_index))
        frame = grouped.get(key)
        eligible = bool(frame is not None and _route_eligible(route, frame))
        exit_row = _choose_exit(route, frame, thresholds) if eligible and frame is not None else None
        original = float(trade.profit_abs)
        modified = (
            float(exit_row["hypothetical_exit_profit_abs"])
            if exit_row is not None
            else original
        )
        rows.append(
            {
                "pair": str(trade.pair),
                "trade_index": int(trade.trade_index),
                "open_date": trade.open_date,
                "outcome_class": str(trade.outcome_class),
                "eligible": int(eligible),
                "triggered": int(exit_row is not None),
                "trigger_checkpoint": int(exit_row["checkpoint_minutes"]) if exit_row is not None else None,
                "original_profit_abs": original,
                "modified_profit_abs": modified,
                "delta_pnl": modified - original,
            }
        )

    decisions = pd.DataFrame(rows)
    decisions["is_fat_tail"] = _mark_local_fat_tails(decisions).astype(int)
    eligible = decisions[decisions["eligible"] == 1]
    triggered = eligible[eligible["triggered"] == 1]
    dead = eligible[eligible["outcome_class"] == "PROFITABLE_THEN_LOST"]
    triggered_dead = triggered[triggered["outcome_class"] == "PROFITABLE_THEN_LOST"]
    winners = eligible[eligible["original_profit_abs"] > 0]
    triggered_winners = triggered[triggered["original_profit_abs"] > 0]
    fat_tails = eligible[eligible["is_fat_tail"] == 1]
    triggered_fat = triggered[triggered["is_fat_tail"] == 1]

    winner_damage = float((-triggered_winners["delta_pnl"].clip(upper=0)).sum())
    fat_damage = float((-triggered_fat["delta_pnl"].clip(upper=0)).sum())
    dead_base_rate = _safe_ratio(len(dead), len(eligible))
    dead_precision = _safe_ratio(len(triggered_dead), len(triggered))

    metrics = {
        "trades": int(len(decisions)),
        "eligible_trades": int(len(eligible)),
        "triggered_trades": int(len(triggered)),
        "trigger_share": _safe_ratio(len(triggered), len(eligible)),
        "baseline_pnl": float(decisions["original_profit_abs"].sum()),
        "modified_pnl": float(decisions["modified_profit_abs"].sum()),
        "delta_pnl": float(decisions["delta_pnl"].sum()),
        "dead_base_rate": dead_base_rate,
        "dead_precision": dead_precision,
        "dead_enrichment": _safe_ratio(dead_precision, dead_base_rate),
        "winner_profit": float(winners["original_profit_abs"].sum()),
        "winner_damage_abs": winner_damage,
        "winner_damage_share": _safe_ratio(winner_damage, float(winners["original_profit_abs"].sum())),
        "fat_tail_count": int(len(fat_tails)),
        "fat_tail_triggered": int(len(triggered_fat)),
        "fat_tail_trigger_rate": _safe_ratio(len(triggered_fat), len(fat_tails)),
        "fat_tail_profit": float(fat_tails["original_profit_abs"].sum()),
        "fat_tail_damage_abs": fat_damage,
        "fat_tail_damage_share": _safe_ratio(fat_damage, float(fat_tails["original_profit_abs"].sum())),
    }
    return decisions, metrics


def _route_gate(folds: pd.DataFrame, pairs: pd.DataFrame) -> tuple[int, list[str]]:
    failures: list[str] = []
    if float(folds["delta_pnl"].sum()) <= 0:
        failures.append("aggregate_delta<=0")
    if int((folds["delta_pnl"] > 0).sum()) < MIN_POSITIVE_FOLDS:
        failures.append("positive_folds<3")
    if int(folds["triggered_trades"].min()) < MIN_TRIGGERS_PER_FOLD:
        failures.append("min_triggers_per_fold<15")
    if float(folds["trigger_share"].max()) > MAX_TRIGGER_SHARE:
        failures.append("trigger_share>20%")
    if float(folds["dead_enrichment"].min()) < MIN_DEAD_ENRICHMENT:
        failures.append("dead_enrichment<1.05")
    if float(folds["winner_damage_share"].max()) > MAX_WINNER_DAMAGE_SHARE:
        failures.append("winner_damage>10%")
    if float(folds["fat_tail_damage_share"].max()) > MAX_FAT_TAIL_DAMAGE_SHARE:
        failures.append("fat_tail_damage>10%")
    if float(folds["fat_tail_trigger_rate"].max()) > MAX_FAT_TAIL_TRIGGER_RATE:
        failures.append("fat_tail_trigger_rate>20%")
    if int((pairs["delta_pnl"] > 0).sum()) < MIN_POSITIVE_COINS:
        failures.append("positive_coins<6")
    return (0 if failures else 1), failures


def _write_markdown(path: Path, summary: pd.DataFrame, folds: pd.DataFrame) -> None:
    lines = [
        "# Hixton V6 – explorative Sequenzanalyse",
        "",
        "**Kein finaler OOS-Beweis und noch kein V6-Tradingcode.** Der alte Holdout ist verbraucht.",
        "",
        "## Routen",
        "",
        "- ROUTE_A: 60m Giveback q80 + MACD q20 + 1h-Trend verloren.",
        "- ROUTE_B: 120m MACD q20 + Preis/VIDYA q20 + 1h-Trend verloren.",
        "- ROUTE_C: zuerst ROUTE_A bei 60m, sonst ROUTE_B bei 120m.",
        "",
        "## Zusammenfassung",
        "",
        "| Route | Delta P/L | positive Folds | positive Coins | max Trigger | max Winner-Schaden | max Fat-Tail-Schaden | Fresh-OOS-Kandidat |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.route} | {row.delta_pnl:.2f} | {row.positive_folds}/4 | "
            f"{row.positive_coins}/10 | {100*row.max_trigger_share:.2f}% | "
            f"{100*row.max_winner_damage_share:.2f}% | {100*row.max_fat_tail_damage_share:.2f}% | "
            f"{int(row.candidate_for_fresh_oos)} |"
        )
    lines.extend(["", "## Fold-Details", ""])
    for route in ROUTES:
        lines.append(f"### {route}")
        lines.append("")
        lines.append("| Fold | Delta P/L | Trigger | Enrichment | Winner-Schaden | Fat-Tail-Schaden |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for row in folds[folds["route"] == route].itertuples(index=False):
            lines.append(
                f"| {row.fold} | {row.delta_pnl:.2f} | {100*row.trigger_share:.2f}% | "
                f"{row.dead_enrichment:.2f}x | {100*row.winner_damage_share:.2f}% | "
                f"{100*row.fat_tail_damage_share:.2f}% |"
            )
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "`candidate_for_fresh_oos = 1` bedeutet nur: Route unverändert einfrieren und auf wirklich neuen Daten prüfen.",
            "Es ist **keine** Freigabe für V6 und keine Profitabilitätsbehauptung.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Explorative Hixton V6 Sequenzanalyse nach verbrauchtem Holdout")
    parser.add_argument(
        "--causal-root",
        type=Path,
        default=Path("research/reports/hixton_v1_causal"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research/reports/hixton_v6_sequence"),
    )
    args = parser.parse_args()

    trades_path = args.causal_root / "all_v1_trade_features.csv"
    snapshots_path = args.causal_root / "dead_trend" / "dead_trend_checkpoint_snapshots.csv"
    causal_manifest_path = args.causal_root / "analysis_manifest.json"
    dead_manifest_path = args.causal_root / "dead_trend" / "dead_trend_manifest.json"
    for path in (trades_path, snapshots_path, causal_manifest_path, dead_manifest_path):
        if not path.is_file():
            raise RuntimeError(f"Missing required V3 causal artifact: {path}")

    trades = pd.read_csv(trades_path)
    snapshots = pd.read_csv(snapshots_path)
    trades["open_date"] = pd.to_datetime(trades["open_date"], utc=True)
    snapshots["checkpoint_time"] = pd.to_datetime(snapshots["checkpoint_time"], utc=True)
    causal_manifest = _read_json(causal_manifest_path)
    dead_manifest = _read_json(dead_manifest_path)
    _validate_inputs(trades, snapshots, causal_manifest, dead_manifest)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fold_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    decision_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []

    for route in ROUTES:
        route_decisions: list[pd.DataFrame] = []
        for fold_name, start_text, end_text in WINDOWS:
            start = pd.Timestamp(start_text)
            end = pd.Timestamp(end_text)
            decisions, metrics = _evaluate_window(route, trades, snapshots, start, end)
            decisions.insert(0, "route", route)
            decisions.insert(1, "fold", fold_name)
            route_decisions.append(decisions)
            fold_rows.append({"route": route, "fold": fold_name, **metrics})

        combined = pd.concat(route_decisions, ignore_index=True)
        decision_frames.append(combined)
        for pair, frame in combined.groupby("pair"):
            pair_rows.append(
                {
                    "route": route,
                    "pair": pair,
                    "trades": int(len(frame)),
                    "triggered_trades": int(frame["triggered"].sum()),
                    "delta_pnl": float(frame["delta_pnl"].sum()),
                    "baseline_pnl": float(frame["original_profit_abs"].sum()),
                    "modified_pnl": float(frame["modified_profit_abs"].sum()),
                }
            )

    fold_df = pd.DataFrame(fold_rows)
    pair_df = pd.DataFrame(pair_rows)
    for route in ROUTES:
        route_folds = fold_df[fold_df["route"] == route]
        route_pairs = pair_df[pair_df["route"] == route]
        candidate, failures = _route_gate(route_folds, route_pairs)
        summary_rows.append(
            {
                "route": route,
                "delta_pnl": float(route_folds["delta_pnl"].sum()),
                "positive_folds": int((route_folds["delta_pnl"] > 0).sum()),
                "positive_coins": int((route_pairs["delta_pnl"] > 0).sum()),
                "max_trigger_share": float(route_folds["trigger_share"].max()),
                "min_dead_enrichment": float(route_folds["dead_enrichment"].min()),
                "max_winner_damage_share": float(route_folds["winner_damage_share"].max()),
                "max_fat_tail_trigger_rate": float(route_folds["fat_tail_trigger_rate"].max()),
                "max_fat_tail_damage_share": float(route_folds["fat_tail_damage_share"].max()),
                "candidate_for_fresh_oos": candidate,
                "gate_failures": ";".join(failures),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    decisions_df = pd.concat(decision_frames, ignore_index=True)
    fold_df.to_csv(args.output_dir / "sequence_fold_results.csv", index=False)
    pair_df.to_csv(args.output_dir / "sequence_pair_results.csv", index=False)
    summary_df.to_csv(args.output_dir / "sequence_route_summary.csv", index=False)
    decisions_df.to_csv(args.output_dir / "sequence_trade_decisions.csv", index=False)
    _write_markdown(args.output_dir / "SEQUENCE_ANALYSIS.md", summary_df, fold_df)

    manifest = {
        "analysis_version": "v6-sequence-exploratory-v1",
        "status": "exploratory_after_consumed_holdout_not_final_oos",
        "source_causal_analysis": causal_manifest.get("analysis_version"),
        "source_dead_trend_analysis": dead_manifest.get("analysis_version"),
        "cohort_lock": causal_manifest.get("cohort_lock"),
        "expected_trades": EXPECTED_TRADES,
        "expected_snapshots": EXPECTED_SNAPSHOTS,
        "windows": [
            {"fold": name, "start": start, "end_exclusive": end}
            for name, start, end in WINDOWS
        ],
        "threshold_rule": "per pair and checkpoint; q20/q80 from snapshots with checkpoint_time strictly before each test window",
        "routes": {
            ROUTE_A: "60m: giveback_fraction>=q80 AND macd_hist_atr<=q20 AND trend_up_1h==0",
            ROUTE_B: "120m: macd_hist_atr<=q20 AND price_minus_vidya_atr<=q20 AND trend_up_1h==0",
            ROUTE_C: "first ROUTE_A at 60m, otherwise ROUTE_B at 120m",
        },
        "fresh_oos_gate": {
            "aggregate_delta_pnl": ">0",
            "positive_folds": ">=3/4",
            "min_triggers_per_fold": MIN_TRIGGERS_PER_FOLD,
            "max_trigger_share": MAX_TRIGGER_SHARE,
            "min_dead_enrichment_each_fold": MIN_DEAD_ENRICHMENT,
            "max_winner_damage_share_each_fold": MAX_WINNER_DAMAGE_SHARE,
            "max_fat_tail_damage_share_each_fold": MAX_FAT_TAIL_DAMAGE_SHARE,
            "max_fat_tail_trigger_rate_each_fold": MAX_FAT_TAIL_TRIGGER_RATE,
            "positive_coins": f">={MIN_POSITIVE_COINS}/10",
        },
        "candidate_routes": summary_df.loc[
            summary_df["candidate_for_fresh_oos"] == 1, "route"
        ].tolist(),
        "warning": "A candidate route must be frozen and tested on genuinely new data before any V6 trading code or profitability claim.",
    }
    (args.output_dir / "sequence_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    print("Hixton V6 sequence analysis complete")
    for row in summary_df.itertuples(index=False):
        print(
            f"  {row.route}: delta={row.delta_pnl:.2f} USDT, "
            f"positive_folds={row.positive_folds}/4, positive_coins={row.positive_coins}/10, "
            f"fresh_oos_candidate={int(row.candidate_for_fresh_oos)}"
        )
    print(f"Output: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
