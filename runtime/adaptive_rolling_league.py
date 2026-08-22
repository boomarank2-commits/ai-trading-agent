"""V12.4 rolling pair-local strategy league.

Research-only. Every rebalance period the router trains exclusively on the
previous 730 days (365d development + 365d validation), freezes qualified
family champions, and trades only the following period. If no family clears
sample, profitability, profit-factor, cost-stress and family-plateau gates,
the correct action is NO_TRADE.

This runner deliberately excludes the noisy fast-breakout, pullback and panic
families after the exact V11 Freqtrade three-year runs showed that the active
ORB/Ichimoku/Bollinger router was structurally unprofitable. It compares:

- donchian_only: slow 4h Donchian trend only
- trend_core: Donchian + Ichimoku
- balanced: Donchian + Ichimoku + Bollinger MR

BTC, ETH and SOL remain fully pair-local; there is no BTC regime dependency.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from adaptive_pair_optimizer import (
    FEE,
    PAIRS,
    STAKE,
    STRESS_FEE,
    Trade,
    Variant,
    download_pair,
    features,
    metrics,
    signal,
    simulate_variant,
    situation_keys,
    variants,
)
from adaptive_family_league import min_sample, quality_score

TRAIN_DAYS = 730
DEV_DAYS = 365
DEFAULT_STEP_DAYS = 90

MODES = {
    "donchian_only": {"donchian_trend"},
    "trend_core": {"donchian_trend", "ichimoku"},
    "balanced": {"donchian_trend", "ichimoku", "bollinger_mr"},
}


def _family_plateau_required(family: str) -> int:
    # Donchian has a deliberately tiny 3x3 grid, so require at least two nearby
    # parameterizations to survive. The larger Ichimoku/MR grids require three.
    return 2 if family == "donchian_trend" else 3


def train_stable_champions(
    x: pd.DataFrame,
    situations: pd.Series,
    dev_start_i: int,
    split_i: int,
    train_end_i: int,
    allowed_families: set[str],
) -> tuple[dict[str, dict], dict[str, dict]]:
    qualified_by_family: dict[str, list[dict]] = {}
    diagnostics: dict[str, dict] = {}

    for v in variants():
        if v.family not in allowed_families:
            continue
        mask = signal(x, v)
        dev_trades = simulate_variant(x, v, mask, dev_start_i, split_i, situations)
        val_trades = simulate_variant(x, v, mask, split_i, train_end_i, situations)
        dev = metrics(dev_trades)
        val = metrics(val_trades)
        stress = metrics(val_trades, STRESS_FEE)
        min_dev, min_val = min_sample(v)
        qualify = (
            dev["trades"] >= min_dev
            and val["trades"] >= min_val
            and dev["pnl"] > 0
            and val["pnl"] > 0
            and dev["pf"] >= 1.05
            and val["pf"] >= 1.10
            and stress["pnl"] > 0
        )
        fam = diagnostics.setdefault(
            v.family,
            {"tested": 0, "qualified": 0, "plateau_required": _family_plateau_required(v.family)},
        )
        fam["tested"] += 1
        if not qualify:
            continue
        fam["qualified"] += 1
        qualified_by_family.setdefault(v.family, []).append(
            {
                "variant": v.name,
                "family": v.family,
                "params": asdict(v),
                "score": quality_score(dev, val, stress),
                "development": dev,
                "validation": val,
                "validation_stress": stress,
            }
        )

    champions: dict[str, dict] = {}
    for family, rows in qualified_by_family.items():
        required = _family_plateau_required(family)
        if len(rows) < required:
            diagnostics[family]["plateau_pass"] = False
            continue
        # A family is not accepted because one lucky parameter won. Require the
        # median qualified variant itself to remain profitable in validation and
        # under stress, then select the highest-scoring survivor.
        median_val_pnl = float(pd.Series([r["validation"]["pnl"] for r in rows]).median())
        median_stress_pnl = float(
            pd.Series([r["validation_stress"]["pnl"] for r in rows]).median()
        )
        diagnostics[family]["median_validation_pnl"] = median_val_pnl
        diagnostics[family]["median_stress_pnl"] = median_stress_pnl
        diagnostics[family]["plateau_pass"] = median_val_pnl > 0 and median_stress_pnl > 0
        if not diagnostics[family]["plateau_pass"]:
            continue
        champions[family] = max(rows, key=lambda r: r["score"])

    return champions, diagnostics


def trade_period(
    x: pd.DataFrame,
    situations: pd.Series,
    champions: dict[str, dict],
    start_i: int,
    end_i: int,
) -> tuple[list[Trade], dict[str, dict]]:
    by_name: dict[str, Variant] = {v.name: v for v in variants()}
    ranked = sorted(champions.values(), key=lambda row: row["score"], reverse=True)
    candidates: list[tuple[int, int, int, Trade]] = []
    family_results: dict[str, dict] = {}
    for rank, champ in enumerate(ranked):
        v = by_name[champ["variant"]]
        trades = simulate_variant(x, v, signal(x, v), start_i, end_i, situations)
        family_results[v.family] = metrics(trades)
        candidates.extend((t.open_i, rank, t.close_i, t) for t in trades)

    candidates.sort(key=lambda row: (row[0], row[1]))
    accepted: list[Trade] = []
    occupied_until = start_i - 1
    for open_i, _, close_i, trade in candidates:
        if open_i <= occupied_until:
            continue
        accepted.append(trade)
        occupied_until = close_i
    return accepted, family_results


def run_period(
    symbol: str,
    df: pd.DataFrame,
    trade_start: pd.Timestamp,
    trade_end: pd.Timestamp,
    allowed_families: set[str],
) -> dict:
    train_start = trade_start - pd.Timedelta(days=TRAIN_DAYS)
    dev_end = train_start + pd.Timedelta(days=DEV_DAYS)
    local = df[(df["date"] >= train_start) & (df["date"] < trade_end)].reset_index(drop=True)
    x, quantiles = features(local, trade_start)
    situations = situation_keys(x, quantiles)
    dev_start_i = int(x["date"].searchsorted(train_start))
    split_i = int(x["date"].searchsorted(dev_end))
    train_end_i = int(x["date"].searchsorted(trade_start))
    period_end_i = int(x["date"].searchsorted(trade_end))

    champions, diagnostics = train_stable_champions(
        x, situations, dev_start_i, split_i, train_end_i, allowed_families
    )
    trades, family_results = trade_period(
        x, situations, champions, train_end_i, period_end_i
    )
    return {
        "symbol": symbol,
        "train_start": str(train_start),
        "development_end": str(dev_end),
        "trade_start": str(trade_start),
        "trade_end": str(trade_end),
        "champions": champions,
        "training_diagnostics": diagnostics,
        "result": metrics(trades),
        "stress": metrics(trades, STRESS_FEE),
        "family_result": family_results,
        "trades": [asdict(t) for t in trades],
    }


def aggregate(periods: list[dict]) -> dict:
    trades = [Trade(**row) for period in periods for row in period["trades"]]
    family_pnl: dict[str, float] = {}
    for trade in trades:
        family_pnl[trade.family] = family_pnl.get(trade.family, 0.0) + trade.pnl
    return {
        "result": metrics(trades),
        "stress": metrics(trades, STRESS_FEE),
        "positive_periods": sum(p["result"]["pnl"] > 0 for p in periods),
        "negative_periods": sum(p["result"]["pnl"] < 0 for p in periods),
        "active_periods": sum(p["result"]["trades"] > 0 for p in periods),
        "no_trade_periods": sum(p["result"]["trades"] == 0 for p in periods),
        "family_pnl": family_pnl,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("runtime/user_data/v12_public_cache"))
    parser.add_argument("--out", type=Path, default=Path("runtime/user_data/v12_rolling_league.json"))
    parser.add_argument("--trade-start", default="2023-08-01")
    parser.add_argument("--trade-end", default="2026-08-01")
    parser.add_argument("--step-days", type=int, default=DEFAULT_STEP_DAYS)
    args = parser.parse_args()

    trade_start = pd.Timestamp(args.trade_start, tz="UTC")
    trade_end = pd.Timestamp(args.trade_end, tz="UTC")
    data_start = trade_start - pd.Timedelta(days=TRAIN_DAYS)
    periods: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    cur = trade_start
    while cur < trade_end:
        nxt = min(cur + pd.Timedelta(days=args.step_days), trade_end)
        periods.append((cur, nxt))
        cur = nxt

    payload = {
        "version": "V12_ROLLING_LEAGUE_1",
        "generated_at": datetime.now(UTC).isoformat(),
        "fee_per_side": FEE,
        "stress_fee_per_side": STRESS_FEE,
        "stake_usdt": STAKE,
        "train_days": TRAIN_DAYS,
        "step_days": args.step_days,
        "trade_start": str(trade_start),
        "trade_end": str(trade_end),
        "results": {},
    }

    for symbol in PAIRS:
        print(f"=== {symbol} ===", flush=True)
        df = download_pair(symbol, data_start, trade_end, args.cache)
        payload["results"][symbol] = {}
        for mode, families in MODES.items():
            rows = []
            for n, (start, end) in enumerate(periods, 1):
                row = run_period(symbol, df, start, end, families)
                rows.append(row)
                r = row["result"]
                selected = {fam: c["variant"] for fam, c in row["champions"].items()}
                print(
                    f"{symbol} {mode} p{n:02d} {start.date()}->{end.date()} "
                    f"champions={selected} trades={r['trades']} pnl={r['pnl']:.2f} "
                    f"PF={r['pf']:.3f} DD={r['dd']:.2f}",
                    flush=True,
                )
            agg = aggregate(rows)
            payload["results"][symbol][mode] = {"periods": rows, "aggregate": agg}
            r = agg["result"]
            print(
                f"{symbol} {mode} AGG: trades={r['trades']} pnl={r['pnl']:.2f} "
                f"PF={r['pf']:.3f} DD={r['dd']:.2f} stress={agg['stress']['pnl']:.2f} "
                f"+periods={agg['positive_periods']} -periods={agg['negative_periods']} "
                f"no_trade={agg['no_trade_periods']} families={agg['family_pnl']}",
                flush=True,
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
