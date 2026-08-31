from __future__ import annotations

import argparse
import heapq
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

ROUTE_C = "ROUTE_C_TWO_STAGE"
PAIR_ORDER = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "DOGE/USDT",
    "LINK/USDT",
    "TRX/USDT",
    "LTC/USDT",
    "BCH/USDT",
)
EXPECTED_TRADES = 6328
EXPECTED_SNAPSHOTS = 9848
EXPECTED_BASELINE_SHARED_TRADES = 637
EXPECTED_BASELINE_SHARED_PNL = -171.36579258
STARTING_WALLET = 250.0
STAKE_REQUEST = 80.0
MAX_OPEN = 3
TOL = 1e-6


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_inputs(
    trades: pd.DataFrame,
    snapshots: pd.DataFrame,
    decisions: pd.DataFrame,
    causal_manifest: dict[str, Any],
    dead_manifest: dict[str, Any],
    sequence_manifest: dict[str, Any],
) -> None:
    if len(trades) != EXPECTED_TRADES:
        raise RuntimeError(f"Expected {EXPECTED_TRADES} trades, got {len(trades)}")
    if len(snapshots) != EXPECTED_SNAPSHOTS:
        raise RuntimeError(f"Expected {EXPECTED_SNAPSHOTS} snapshots, got {len(snapshots)}")
    if causal_manifest.get("analysis_version") != "causal-v3-cohort-lock":
        raise RuntimeError("Expected causal-v3-cohort-lock")
    if dead_manifest.get("analysis_version") != "dead-trend-v3-cohort-lock":
        raise RuntimeError("Expected dead-trend-v3-cohort-lock")
    if sequence_manifest.get("analysis_version") != "v6-sequence-exploratory-v1":
        raise RuntimeError("Expected v6-sequence-exploratory-v1")
    if int((causal_manifest.get("cohort_lock") or {}).get("total_trades") or 0) != EXPECTED_TRADES:
        raise RuntimeError("Causal cohort lock is not 6328 trades")
    if int((dead_manifest.get("cohort_lock") or {}).get("total_trades") or 0) != EXPECTED_TRADES:
        raise RuntimeError("Dead-trend cohort lock is not 6328 trades")
    route_c = decisions[decisions["route"] == ROUTE_C]
    if route_c.empty:
        raise RuntimeError("Route C decisions are missing")
    if int(route_c["triggered"].sum()) != 360:
        raise RuntimeError(f"Expected 360 exploratory Route C triggers, got {int(route_c['triggered'].sum())}")


def _route_c_exit_map(decisions: pd.DataFrame, snapshots: pd.DataFrame) -> dict[tuple[str, int], dict[str, Any]]:
    route_c = decisions[(decisions["route"] == ROUTE_C) & (decisions["triggered"] == 1)].copy()
    route_c["trigger_checkpoint"] = route_c["trigger_checkpoint"].astype(int)
    chosen = route_c.merge(
        snapshots[
            [
                "pair",
                "trade_index",
                "checkpoint_minutes",
                "execution_time",
                "hypothetical_exit_profit_abs",
            ]
        ],
        left_on=["pair", "trade_index", "trigger_checkpoint"],
        right_on=["pair", "trade_index", "checkpoint_minutes"],
        how="left",
        validate="one_to_one",
    )
    if chosen["execution_time"].isna().any():
        raise RuntimeError("A Route C trigger has no matching causal execution time")
    delta = (chosen["modified_profit_abs"] - chosen["hypothetical_exit_profit_abs"]).abs().max()
    if float(delta) > TOL:
        raise RuntimeError(f"Sequence/snapshot PnL mismatch: max delta {delta}")

    output: dict[tuple[str, int], dict[str, Any]] = {}
    for row in chosen.itertuples(index=False):
        key = (str(row.pair), int(row.trade_index))
        output[key] = {
            "close_date": pd.to_datetime(row.execution_time, utc=True),
            "profit_abs": float(row.modified_profit_abs),
            "checkpoint": int(row.trigger_checkpoint),
            "fold": str(row.fold),
        }
    return output


def _simulate(
    trades: pd.DataFrame,
    exit_map: dict[tuple[str, int], dict[str, Any]] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rank = {pair: index for index, pair in enumerate(PAIR_ORDER)}
    work = trades.copy()
    work["open_date"] = pd.to_datetime(work["open_date"], utc=True)
    work["close_date"] = pd.to_datetime(work["close_date"], utc=True)
    work["pair_rank"] = work["pair"].map(rank)
    work = work.sort_values(["open_date", "pair_rank", "trade_index"])

    cash = STARTING_WALLET
    active: list[tuple[int, int, float, float, tuple[str, int], str]] = []
    serial = 0
    accepted: list[dict[str, Any]] = []

    for row in work.itertuples(index=False):
        open_date = pd.to_datetime(row.open_date, utc=True)
        while active and active[0][0] <= int(open_date.value):
            _, _, stake, profit, _, _ = heapq.heappop(active)
            cash += stake + profit

        if len(active) >= MAX_OPEN or cash < STAKE_REQUEST:
            continue

        key = (str(row.pair), int(row.trade_index))
        stake = float(row.stake_amount)
        replacement = exit_map.get(key) if exit_map is not None else None
        if replacement is None:
            close_date = pd.to_datetime(row.close_date, utc=True)
            profit = float(row.profit_abs)
            exit_kind = "v1"
        else:
            close_date = pd.to_datetime(replacement["close_date"], utc=True)
            profit = float(replacement["profit_abs"])
            exit_kind = f"route_c_{replacement['checkpoint']}m"
            if close_date >= pd.to_datetime(row.close_date, utc=True):
                raise RuntimeError(f"Route C did not shorten {key}")

        cash -= stake
        heapq.heappush(
            active,
            (int(close_date.value), serial, stake, profit, key, exit_kind),
        )
        serial += 1
        accepted.append(
            {
                "pair": key[0],
                "trade_index": key[1],
                "open_date": open_date.isoformat(),
                "close_date": close_date.isoformat(),
                "stake_amount": stake,
                "profit_abs": profit,
                "exit_kind": exit_kind,
            }
        )

    while active:
        _, _, stake, profit, _, _ = heapq.heappop(active)
        cash += stake + profit

    accepted_frame = pd.DataFrame(accepted)
    pnl = float(accepted_frame["profit_abs"].sum()) if not accepted_frame.empty else 0.0
    if not math.isclose(cash - STARTING_WALLET, pnl, rel_tol=0.0, abs_tol=TOL):
        raise RuntimeError("Wallet/PnL accounting mismatch")
    return accepted_frame, {
        "trades": int(len(accepted_frame)),
        "profit_usdt": pnl,
        "final_wallet_usdt": cash,
    }


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Hixton V6 Route C – Shared-Portfolio Replay",
        "",
        "**Historischer Replay nach verbrauchtem Holdout; kein frischer OOS-Beweis.**",
        "",
        "Der Baseline-Simulator muss zuerst den bereits bekannten echten V1-Shared-Lauf exakt reproduzieren. Erst danach wird Route C mit den kausalen 1m-Ausfuehrungszeiten eingesetzt.",
        "",
        "## Ergebnis",
        "",
        f"- V1 Shared: {summary['baseline']['trades']} Trades, {summary['baseline']['profit_usdt']:.4f} USDT.",
        f"- Route C Shared: {summary['route_c']['trades']} Trades, {summary['route_c']['profit_usdt']:.4f} USDT.",
        f"- Delta: {summary['delta_profit_usdt']:+.4f} USDT.",
        f"- Direkter Effekt auf gemeinsame Trades: {summary['direct_common_trade_delta_usdt']:+.4f} USDT.",
        f"- Effekt durch veraenderte Slot-/Folgetrade-Auswahl: {summary['opportunity_set_delta_usdt']:+.4f} USDT.",
        f"- Route-C-Exits im modifizierten Shared-Portfolio: {summary['accepted_route_c_exits']}.",
        f"- Nur Baseline akzeptiert: {summary['only_baseline_trades']}; nur Route C akzeptiert: {summary['only_route_c_trades']}.",
        "",
        "## Entscheidung",
        "",
        "**Route C wird fuer das aktuelle Shared-Portfolio verworfen.**" if summary["reject_for_shared_portfolio"] else "**Route C verbessert den Shared-Replay und darf als eingefrorener Kandidat weitergeprueft werden.**",
        "",
        "Die Standalone-/Walk-Forward-Verbesserung darf nicht als Shared-Portfolio-Gewinn interpretiert werden.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrated Hixton Route C shared-wallet replay")
    parser.add_argument("--causal-root", type=Path, default=Path("research/reports/hixton_v1_causal"))
    parser.add_argument("--sequence-root", type=Path, default=Path("research/reports/hixton_v6_sequence"))
    parser.add_argument("--output-dir", type=Path, default=Path("research/reports/hixton_v6_route_c_portfolio"))
    args = parser.parse_args()

    trades = pd.read_csv(args.causal_root / "all_v1_trade_features.csv")
    snapshots = pd.read_csv(args.causal_root / "dead_trend" / "dead_trend_checkpoint_snapshots.csv")
    decisions = pd.read_csv(args.sequence_root / "sequence_trade_decisions.csv")
    causal_manifest = _read_json(args.causal_root / "analysis_manifest.json")
    dead_manifest = _read_json(args.causal_root / "dead_trend" / "dead_trend_manifest.json")
    sequence_manifest = _read_json(args.sequence_root / "sequence_manifest.json")
    _validate_inputs(trades, snapshots, decisions, causal_manifest, dead_manifest, sequence_manifest)

    exit_map = _route_c_exit_map(decisions, snapshots)
    baseline_trades, baseline = _simulate(trades, None)
    if baseline["trades"] != EXPECTED_BASELINE_SHARED_TRADES or not math.isclose(
        baseline["profit_usdt"], EXPECTED_BASELINE_SHARED_PNL, rel_tol=0.0, abs_tol=TOL
    ):
        raise RuntimeError(
            "Baseline calibration failed: expected "
            f"{EXPECTED_BASELINE_SHARED_TRADES} trades / {EXPECTED_BASELINE_SHARED_PNL:.8f} USDT, "
            f"got {baseline['trades']} / {baseline['profit_usdt']:.8f}."
        )

    route_c_trades, route_c = _simulate(trades, exit_map)
    base_map = {(str(r.pair), int(r.trade_index)): float(r.profit_abs) for r in baseline_trades.itertuples(index=False)}
    route_map = {(str(r.pair), int(r.trade_index)): float(r.profit_abs) for r in route_c_trades.itertuples(index=False)}
    common = set(base_map) & set(route_map)
    only_base = set(base_map) - set(route_map)
    only_route = set(route_map) - set(base_map)
    direct_delta = sum(route_map[key] - base_map[key] for key in common)
    opportunity_delta = sum(route_map[key] for key in only_route) - sum(base_map[key] for key in only_base)
    total_delta = float(route_c["profit_usdt"] - baseline["profit_usdt"])
    if not math.isclose(direct_delta + opportunity_delta, total_delta, rel_tol=0.0, abs_tol=TOL):
        raise RuntimeError("Portfolio delta decomposition mismatch")

    summary = {
        "analysis_version": "v6-route-c-shared-replay-v1",
        "status": "historical_replay_after_consumed_holdout_not_fresh_oos",
        "baseline_contract": {
            "starting_wallet_usdt": STARTING_WALLET,
            "requested_stake_usdt": STAKE_REQUEST,
            "max_open_trades": MAX_OPEN,
            "pair_priority": list(PAIR_ORDER),
            "same_timestamp_order": "release closes before processing new entries; entries ordered by pair priority",
            "cash_reservation": "reported per-trade stake_amount; new entry requires available cash >= 80 USDT",
        },
        "baseline": baseline,
        "route_c": route_c,
        "delta_profit_usdt": total_delta,
        "direct_common_trade_delta_usdt": float(direct_delta),
        "opportunity_set_delta_usdt": float(opportunity_delta),
        "common_accepted_trades": len(common),
        "only_baseline_trades": len(only_base),
        "only_route_c_trades": len(only_route),
        "accepted_route_c_exits": int((route_c_trades["exit_kind"] != "v1").sum()),
        "exploratory_route_c_trigger_map_size": len(exit_map),
        "baseline_reproduced_exactly": True,
        "reject_for_shared_portfolio": bool(total_delta <= 0.0),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    baseline_trades.to_csv(args.output_dir / "baseline_shared_accepted_trades.csv", index=False)
    route_c_trades.to_csv(args.output_dir / "route_c_shared_accepted_trades.csv", index=False)
    (args.output_dir / "portfolio_replay_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    _write_report(args.output_dir / "ROUTE_C_SHARED_REPLAY.md", summary)

    print("Hixton Route C shared-portfolio replay complete")
    print(f"  V1 baseline: {baseline['trades']} trades, {baseline['profit_usdt']:.4f} USDT")
    print(f"  Route C:     {route_c['trades']} trades, {route_c['profit_usdt']:.4f} USDT")
    print(f"  Delta:       {total_delta:+.4f} USDT")
    print(f"  direct={direct_delta:+.4f}; slot/opportunity={opportunity_delta:+.4f}")
    print(f"  reject_for_shared_portfolio={int(total_delta <= 0.0)}")
    print(f"Output: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
