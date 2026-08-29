"""Older-window screen for the preregistered LTC exhaustion-reversion reserve.

Research-only: fixed parameters from the Deep Research handoff, one 80-USDT
block, no tuning, and five annual slices before any exact Freqtrade candidate.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from runtime.adaptive_pair_optimizer import (
    FEE,
    STAKE,
    STRESS_FEE,
    adx,
    atr,
    download_pair,
    ema,
    net_return,
)


@dataclass(frozen=True)
class ScreenTrade:
    open_date: str
    close_date: str
    entry: float
    exit: float
    net_return: float
    pnl: float
    exit_reason: str


def build_features(base: pd.DataFrame) -> pd.DataFrame:
    x = base.copy()
    x["ema96"] = ema(x["close"], 96)
    x["atr14"] = atr(x, 14)
    x["volume_mean"] = x["volume"].shift(1).rolling(20, min_periods=20).mean()
    x["volume_ratio"] = x["volume"] / x["volume_mean"]

    informative = (
        base.set_index("date")
        .resample("4h", label="right", closed="left")
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        )
        .dropna()
        .reset_index()
    )
    informative["ema50_4h"] = ema(informative["close"], 50)
    informative["ema200_4h"] = ema(informative["close"], 200)
    informative["adx_4h"] = adx(informative, 14)
    informative["momentum30d_4h"] = (
        informative["close"] / informative["close"].shift(180) - 1.0
    )
    informative = informative.rename(
        columns={"date": "informative_date", "close": "close_4h"}
    )[
        [
            "informative_date",
            "close_4h",
            "ema50_4h",
            "ema200_4h",
            "adx_4h",
            "momentum30d_4h",
        ]
    ]
    x = pd.merge_asof(
        x.sort_values("date"),
        informative.sort_values("informative_date"),
        left_on="date",
        right_on="informative_date",
        direction="backward",
    )
    x["range_state"] = (
        (x["adx_4h"] <= 17)
        & (((x["ema50_4h"] - x["ema200_4h"]).abs() / x["close_4h"]) <= 0.025)
        & x["momentum30d_4h"].between(-0.15, 0.10)
    )
    shock_level = x["ema96"] - 2.50 * x["atr14"]
    reclaim_level = x["ema96"] - 1.50 * x["atr14"]
    x["shock"] = (
        x["range_state"]
        & (x["close"] <= shock_level)
        & (x["volume_ratio"] >= 2.0)
        & x["research_data_valid"].fillna(False)
    )
    recent_shock = (
        x["shock"].shift(1).rolling(4, min_periods=1).max().fillna(False).astype(bool)
    )
    x["entry_signal"] = (
        recent_shock
        & x["range_state"]
        & (x["close"] > reclaim_level)
        & (x["close"].shift(1) <= reclaim_level.shift(1))
        & x["research_data_valid"].fillna(False)
        & (x["volume"] > 0)
    )
    return x


def simulate(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> list[ScreenTrade]:
    start_i = int(frame["date"].searchsorted(start))
    end_i = int(frame["date"].searchsorted(end))
    entry_signal = frame["entry_signal"].fillna(False).to_numpy(dtype=bool)
    open_price = frame["open"].to_numpy(dtype=float)
    high_price = frame["high"].to_numpy(dtype=float)
    low_price = frame["low"].to_numpy(dtype=float)
    close_price = frame["close"].to_numpy(dtype=float)
    ema96 = frame["ema96"].to_numpy(dtype=float)
    adx4h = frame["adx_4h"].to_numpy(dtype=float)
    dates = frame["date"].astype(str).to_numpy()
    trades: list[ScreenTrade] = []
    i = max(start_i, 1)
    while i < end_i - 1:
        if not entry_signal[i]:
            i += 1
            continue
        entry_i = i + 1
        entry = float(open_price[entry_i])
        stop_price = entry * (1 - 0.055)
        roi_price = entry * 1.50
        last = min(end_i - 1, entry_i + 24)
        exit_i = last
        exit_price = float(close_price[last])
        exit_reason = "six_hour_time_exit"
        for pos in range(entry_i, last + 1):
            if low_price[pos] <= stop_price:
                exit_i = pos
                exit_price = stop_price
                exit_reason = "stop_loss"
                break
            if high_price[pos] >= roi_price:
                exit_i = pos
                exit_price = roi_price
                exit_reason = "roi_50"
                break
            exit_signal = (
                close_price[pos] >= ema96[pos]
                or (adx4h[pos] >= 23 and close_price[pos] < ema96[pos])
            )
            if exit_signal and pos + 1 < end_i:
                exit_i = pos + 1
                exit_price = float(open_price[exit_i])
                exit_reason = (
                    "ema96_reversion" if close_price[pos] >= ema96[pos] else "adx_abort"
                )
                break
        result = float(net_return(entry, exit_price, FEE))
        trades.append(
            ScreenTrade(
                open_date=str(dates[entry_i]),
                close_date=str(dates[exit_i]),
                entry=entry,
                exit=exit_price,
                net_return=result,
                pnl=float(STAKE * result),
                exit_reason=exit_reason,
            )
        )
        i = exit_i + 1
    return trades


def metrics(trades: list[ScreenTrade], fee: float) -> dict[str, float | int]:
    pnl = [float(STAKE * net_return(t.entry, t.exit, fee)) for t in trades]
    gross_profit = sum(value for value in pnl if value > 0)
    gross_loss = -sum(value for value in pnl if value < 0)
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in pnl:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "trades": len(trades),
        "pnl": sum(pnl),
        "profit_factor": (
            gross_profit / gross_loss
            if gross_loss > 0
            else (99.0 if gross_profit > 0 else 0.0)
        ),
        "drawdown_usdt": drawdown,
        "win_rate": sum(value > 0 for value in pnl) / len(pnl) if pnl else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cache", type=Path, default=Path("runtime/user_data/v12_public_cache")
    )
    parser.add_argument(
        "--out", type=Path, default=Path("runtime/user_data/ltc_exhaustion_oos.json")
    )
    args = parser.parse_args()
    first = pd.Timestamp("2020-08-01", tz="UTC")
    end = pd.Timestamp("2025-07-31", tz="UTC")
    base = download_pair("LTCUSDT", first, end, args.cache)
    frame = build_features(base)
    folds = []
    all_trades: list[ScreenTrade] = []
    for year in range(5):
        fold_start = first + pd.DateOffset(years=year)
        fold_end = min(fold_start + pd.DateOffset(years=1), end)
        trades = simulate(frame, fold_start, fold_end)
        all_trades.extend(trades)
        fold = {
            "start": str(fold_start),
            "end": str(fold_end),
            "base_fee": metrics(trades, FEE),
            "stress_fee": metrics(trades, STRESS_FEE),
            "trades": [asdict(trade) for trade in trades],
        }
        folds.append(fold)
        result = fold["base_fee"]
        print(
            f"fold{year + 1}: trades={result['trades']} pnl={result['pnl']:.2f} "
            f"PF={result['profit_factor']:.3f} DD={result['drawdown_usdt']:.2f}",
            flush=True,
        )
    aggregate = {
        "base_fee": metrics(all_trades, FEE),
        "stress_fee": metrics(all_trades, STRESS_FEE),
        "positive_folds": sum(fold["base_fee"]["pnl"] > 0 for fold in folds),
        "fold_count": len(folds),
    }
    payload = {
        "schema": "LTC-EXHAUSTION-OLDER-OOS-SCREEN-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_quality": base.attrs.get("data_quality", {}),
        "folds": folds,
        "aggregate": aggregate,
        "limitations": [
            "15m screening simulation, not an exact Freqtrade 1m-detail result",
            "protections and shared-wallet slot competition are not simulated",
            "fixed Deep Research parameters; no post-result tuning is allowed",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(aggregate, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
