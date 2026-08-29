"""Older-window screen for the immutable V12.37 SOL Supertrend route.

This is a research screen, not a Freqtrade result and not an active strategy.
It reuses the already documented V12.37 parameters without tuning and checks
five annual slices that precede the exact 2023-2026 financial backtest.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
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
    rsi,
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


def supertrend_direction(
    frame: pd.DataFrame, period: int = 14, multiplier: float = 3.5
) -> pd.Series:
    atr_value = atr(frame, period)
    midpoint = (frame["high"] + frame["low"]) / 2.0
    upper = midpoint + multiplier * atr_value
    lower = midpoint - multiplier * atr_value
    final_upper = upper.copy()
    final_lower = lower.copy()
    direction = pd.Series(0, index=frame.index, dtype="int8")

    for pos in range(1, len(frame)):
        previous = pos - 1
        if np.isnan(atr_value.iat[pos]):
            continue
        if (
            np.isnan(final_upper.iat[previous])
            or frame["close"].iat[previous] > final_upper.iat[previous]
        ):
            final_upper.iat[pos] = upper.iat[pos]
        else:
            final_upper.iat[pos] = min(upper.iat[pos], final_upper.iat[previous])
        if (
            np.isnan(final_lower.iat[previous])
            or frame["close"].iat[previous] < final_lower.iat[previous]
        ):
            final_lower.iat[pos] = lower.iat[pos]
        else:
            final_lower.iat[pos] = max(lower.iat[pos], final_lower.iat[previous])

        previous_direction = int(direction.iat[previous])
        if (
            previous_direction <= 0
            and frame["close"].iat[pos] > final_upper.iat[previous]
        ):
            direction.iat[pos] = 1
        elif (
            previous_direction >= 0
            and frame["close"].iat[pos] < final_lower.iat[previous]
        ):
            direction.iat[pos] = -1
        else:
            direction.iat[pos] = previous_direction or -1
    return direction


def build_features(base: pd.DataFrame) -> pd.DataFrame:
    x = base.copy()
    x["ema20"] = ema(x["close"], 20)
    x["rsi14"] = rsi(x["close"], 14)

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
    informative["ema200_4h"] = ema(informative["close"], 200)
    informative["ema200_rising6_4h"] = (
        informative["ema200_4h"] > informative["ema200_4h"].shift(6)
    )
    informative["adx_4h"] = adx(informative, 14)
    informative["momentum30d_4h"] = (
        informative["close"] / informative["close"].shift(180) - 1.0
    )
    informative["direction_4h"] = supertrend_direction(informative)
    informative["flip_long_4h"] = (
        (informative["direction_4h"] > 0)
        & (informative["direction_4h"].shift(1).fillna(0) <= 0)
    )
    informative["flip_short_4h"] = (
        (informative["direction_4h"] < 0)
        & (informative["direction_4h"].shift(1).fillna(0) >= 0)
    )
    informative = informative.rename(
        columns={"date": "informative_date", "close": "close_4h"}
    )[
        [
            "informative_date",
            "close_4h",
            "ema200_4h",
            "ema200_rising6_4h",
            "adx_4h",
            "momentum30d_4h",
            "direction_4h",
            "flip_long_4h",
            "flip_short_4h",
        ]
    ]
    x = pd.merge_asof(
        x.sort_values("date"),
        informative.sort_values("informative_date"),
        left_on="date",
        right_on="informative_date",
        direction="backward",
    )
    minutes_after_informative = (
        x["date"] - x["informative_date"]
    ).dt.total_seconds() / 60.0
    x["entry_window"] = minutes_after_informative.between(0, 45)
    x["entry_signal"] = (
        x["flip_long_4h"].fillna(False)
        & x["entry_window"]
        & (x["close_4h"] > x["ema200_4h"])
        & x["ema200_rising6_4h"].fillna(False)
        & (x["adx_4h"] >= 20)
        & (x["momentum30d_4h"] >= 0.05)
        & (x["close"] > x["ema20"])
        & x["rsi14"].between(50, 72)
        & x["research_data_valid"].fillna(False)
        & (x["volume"] > 0)
    )
    return x


def simulate(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> list[ScreenTrade]:
    start_i = int(frame["date"].searchsorted(start))
    end_i = int(frame["date"].searchsorted(end))
    entry_signal = frame["entry_signal"].fillna(False).to_numpy(dtype=bool)
    exit_signal = frame["flip_short_4h"].fillna(False).to_numpy(dtype=bool)
    open_price = frame["open"].to_numpy(dtype=float)
    high_price = frame["high"].to_numpy(dtype=float)
    low_price = frame["low"].to_numpy(dtype=float)
    close_price = frame["close"].to_numpy(dtype=float)
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
        exit_i = end_i - 1
        exit_price = float(close_price[exit_i])
        exit_reason = "window_end"
        for pos in range(entry_i, end_i):
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
            if exit_signal[pos] and pos + 1 < end_i:
                exit_i = pos + 1
                exit_price = float(open_price[exit_i])
                exit_reason = "supertrend_short_flip"
                break
        result = net_return(entry, exit_price, FEE)
        trades.append(
            ScreenTrade(
                open_date=str(dates[entry_i]),
                close_date=str(dates[exit_i]),
                entry=entry,
                exit=exit_price,
                net_return=float(result),
                pnl=float(STAKE * result),
                exit_reason=exit_reason,
            )
        )
        i = exit_i + 1
    return trades


def metrics(trades: list[ScreenTrade], fee: float) -> dict[str, float | int]:
    pnl = [STAKE * net_return(t.entry, t.exit, fee) for t in trades]
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
        "--out", type=Path, default=Path("runtime/user_data/v12_37_sol_oos.json")
    )
    args = parser.parse_args()

    first = pd.Timestamp("2020-08-01", tz="UTC")
    end = pd.Timestamp("2025-07-31", tz="UTC")
    base = download_pair("SOLUSDT", first, end, args.cache)
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
        "schema": "V12.37-SOL-OLDER-OOS-SCREEN-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "route": {
            "supertrend_period": 14,
            "supertrend_multiplier": 3.5,
            "macro_ema": 200,
            "macro_ema_rising_bars": 6,
            "adx_min": 20,
            "momentum_30d_min": 0.05,
            "entry_window_15m_bars": 4,
            "rsi_min": 50,
            "rsi_max": 72,
            "stoploss": -0.055,
            "roi": 0.50,
        },
        "data_quality": base.attrs.get("data_quality", {}),
        "folds": folds,
        "aggregate": aggregate,
        "limitations": [
            "15m screening simulation, not an exact Freqtrade 1m-detail result",
            "protections and shared-wallet slot competition are not simulated",
            "no parameter was selected or changed after viewing these folds",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(aggregate, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
