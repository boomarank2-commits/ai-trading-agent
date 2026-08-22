"""V12.3 robust pair-local strategy league.

Each 730-day training window is split into 365d development + 365d validation.
Only strategy-family champions that are profitable in both halves and remain
profitable under validation cost stress are allowed into the following 365d
blind period. BTC, ETH and SOL are evaluated independently.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from adaptive_pair_optimizer import (
    BLIND_DAYS,
    FEE,
    PAIRS,
    STAKE,
    STRESS_FEE,
    TRAIN_DAYS,
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

CORE_FAMILIES = {"donchian_trend", "slow_breakout", "ichimoku", "bollinger_mr"}
ALL_FAMILIES = CORE_FAMILIES | {"trend_pullback", "panic_bounce"}


def min_sample(v: Variant) -> tuple[int, int]:
    if v.family == "donchian_trend":
        return 3, 3
    if v.family == "ichimoku":
        return 5, 4
    return 8, 6


def quality_score(dev: dict, val: dict, stress: dict) -> float:
    exp_dev = dev["pnl"] / max(dev["trades"], 1)
    exp_val = val["pnl"] / max(val["trades"], 1)
    consistency = min(dev["pnl"], val["pnl"])
    return (
        1.5 * exp_val * math.sqrt(val["trades"])
        + 0.6 * exp_dev * math.sqrt(dev["trades"])
        + 0.04 * consistency
        + 0.02 * stress["pnl"]
        - 0.02 * val["dd"]
    )


def train_family_champions(
    x: pd.DataFrame,
    situations: pd.Series,
    start_i: int,
    split_i: int,
    end_i: int,
    allowed_families: set[str],
) -> tuple[dict[str, dict], dict]:
    champions: dict[str, dict] = {}
    diagnostics: dict[str, dict] = {}
    for v in variants():
        if v.family not in allowed_families:
            continue
        mask = signal(x, v)
        dev_trades = simulate_variant(x, v, mask, start_i, split_i, situations)
        val_trades = simulate_variant(x, v, mask, split_i, end_i, situations)
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
        fam = diagnostics.setdefault(v.family, {"tested": 0, "qualified": 0})
        fam["tested"] += 1
        if not qualify:
            continue
        fam["qualified"] += 1
        score = quality_score(dev, val, stress)
        record = {
            "variant": v.name,
            "family": v.family,
            "score": score,
            "params": asdict(v),
            "development": dev,
            "validation": val,
            "validation_stress": stress,
        }
        prev = champions.get(v.family)
        if prev is None or record["score"] > prev["score"]:
            champions[v.family] = record
    return champions, diagnostics


def blind_champion_trades(
    x: pd.DataFrame,
    situations: pd.Series,
    champions: dict[str, dict],
    start_i: int,
    end_i: int,
) -> tuple[list[Trade], dict[str, dict]]:
    by_name = {v.name: v for v in variants()}
    ranked = sorted(champions.values(), key=lambda item: item["score"], reverse=True)
    candidates: list[tuple[int, int, int, Trade]] = []
    family_metrics: dict[str, dict] = {}
    for rank, champ in enumerate(ranked):
        v = by_name[champ["variant"]]
        trades = simulate_variant(x, v, signal(x, v), start_i, end_i, situations)
        family_metrics[v.family] = metrics(trades)
        for trade in trades:
            candidates.append((trade.open_i, rank, trade.close_i, trade))
    candidates.sort(key=lambda item: (item[0], item[1]))
    accepted: list[Trade] = []
    occupied_until = start_i - 1
    used_open_i: set[int] = set()
    for open_i, _, close_i, trade in candidates:
        if open_i <= occupied_until or open_i in used_open_i:
            continue
        accepted.append(trade)
        used_open_i.add(open_i)
        occupied_until = close_i
    return accepted, family_metrics


def run_fold(
    symbol: str,
    df: pd.DataFrame,
    start: pd.Timestamp,
    allowed_families: set[str],
) -> dict:
    train_end = start + pd.Timedelta(days=TRAIN_DAYS)
    blind_end = train_end + pd.Timedelta(days=BLIND_DAYS)
    dev_end = start + pd.Timedelta(days=TRAIN_DAYS // 2)
    local = df[(df["date"] >= start) & (df["date"] < blind_end)].reset_index(drop=True)
    x, quantiles = features(local, train_end)
    situations = situation_keys(x, quantiles)
    start_i = int(x["date"].searchsorted(start))
    split_i = int(x["date"].searchsorted(dev_end))
    train_end_i = int(x["date"].searchsorted(train_end))
    blind_end_i = int(x["date"].searchsorted(blind_end))
    champions, diagnostics = train_family_champions(
        x, situations, start_i, split_i, train_end_i, allowed_families
    )
    blind, family_blind = blind_champion_trades(
        x, situations, champions, train_end_i, blind_end_i
    )
    return {
        "symbol": symbol,
        "start": str(start),
        "development_end": str(dev_end),
        "training_end": str(train_end),
        "blind_end": str(blind_end),
        "champions": champions,
        "training_diagnostics": diagnostics,
        "blind": metrics(blind),
        "blind_stress": metrics(blind, STRESS_FEE),
        "family_blind": family_blind,
        "blind_trades": [asdict(t) for t in blind],
    }


def aggregate(folds: list[dict]) -> dict:
    all_trades = [Trade(**t) for fold in folds for t in fold["blind_trades"]]
    fam_pnl: dict[str, float] = {}
    for t in all_trades:
        fam_pnl[t.family] = fam_pnl.get(t.family, 0.0) + t.pnl
    return {
        "blind": metrics(all_trades),
        "stress": metrics(all_trades, STRESS_FEE),
        "positive_folds": sum(f["blind"]["pnl"] > 0 for f in folds),
        "active_folds": sum(f["blind"]["trades"] > 0 for f in folds),
        "family_pnl": fam_pnl,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("runtime/user_data/v12_public_cache"))
    parser.add_argument("--out", type=Path, default=Path("runtime/user_data/v12_family_league.json"))
    parser.add_argument("--start", default="2021-08-01")
    parser.add_argument("--folds", type=int, default=3)
    args = parser.parse_args()

    first = pd.Timestamp(args.start, tz="UTC")
    starts = [first + pd.DateOffset(years=i) for i in range(args.folds)]
    end = max(starts) + pd.Timedelta(days=TRAIN_DAYS + BLIND_DAYS)
    modes = {"core": CORE_FAMILIES, "all": ALL_FAMILIES}
    payload = {
        "version": "V12_FAMILY_LEAGUE_1",
        "generated_at": datetime.now(UTC).isoformat(),
        "fee_per_side": FEE,
        "stress_fee_per_side": STRESS_FEE,
        "stake_usdt": STAKE,
        "results": {},
    }
    for symbol in PAIRS:
        print(f"=== {symbol} ===", flush=True)
        df = download_pair(symbol, first, end, args.cache)
        payload["results"][symbol] = {}
        for mode, families in modes.items():
            folds = []
            for n, start in enumerate(starts, 1):
                fold = run_fold(symbol, df, start, families)
                folds.append(fold)
                b = fold["blind"]
                names = {fam: c["variant"] for fam, c in fold["champions"].items()}
                print(
                    f"{symbol} {mode} fold{n}: champions={names} "
                    f"trades={b['trades']} pnl={b['pnl']:.2f} PF={b['pf']:.3f} DD={b['dd']:.2f}",
                    flush=True,
                )
            agg = aggregate(folds)
            payload["results"][symbol][mode] = {"folds": folds, "aggregate": agg}
            b = agg["blind"]
            print(
                f"{symbol} {mode} AGG: +folds={agg['positive_folds']}/{args.folds} "
                f"active={agg['active_folds']}/{args.folds} trades={b['trades']} "
                f"pnl={b['pnl']:.2f} PF={b['pf']:.3f} DD={b['dd']:.2f} "
                f"stress={agg['stress']['pnl']:.2f} families={agg['family_pnl']}",
                flush=True,
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
