"""Older-window screen for broad-core failed-breakout exit decisions.

This research-only approximation keeps the active V12.33 broad-core entries
fixed and compares three immutable exit policies on five annual slices.  It is
not a Freqtrade result and cannot promote a strategy by itself.
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

SYMBOLS = ("BNBUSDT", "SOLUSDT", "LINKUSDT", "TRXUSDT", "LTCUSDT")
POLICIES = ("active_15m_failure", "no_early_failure", "confirmed_4h_failure")


@dataclass(frozen=True)
class ScreenTrade:
    open_date: str
    close_date: str
    entry: float
    exit: float
    pnl: float
    exit_reason: str


def _informative(base: pd.DataFrame, rule: str, suffix: str) -> pd.DataFrame:
    frame = (
        base.set_index("date")
        .resample(rule, label="right", closed="left")
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
    frame[f"ema50_{suffix}"] = ema(frame["close"], 50)
    frame[f"ema200_{suffix}"] = ema(frame["close"], 200)
    frame[f"rsi_{suffix}"] = rsi(frame["close"], 14)
    frame[f"close_{suffix}"] = frame["close"]
    if suffix == "1h":
        frame["ema50_rising_1h"] = frame["ema50_1h"] > frame["ema50_1h"].shift(8)
        return frame[
            [
                "date",
                "close_1h",
                "ema50_1h",
                "ema200_1h",
                "rsi_1h",
                "ema50_rising_1h",
            ]
        ]

    frame["atr_4h"] = atr(frame, 14)
    frame["adx_4h"] = adx(frame, 14)
    frame["momentum_30d_4h"] = frame["close"] / frame["close"].shift(180) - 1.0
    frame["donchian_entry_4h"] = (
        frame["high"].shift(1).rolling(120, min_periods=120).max()
    )
    frame["donchian_exit_4h"] = (
        frame["low"].shift(1).rolling(60, min_periods=60).min()
    )
    frame["fresh_breakout_4h"] = (
        (frame["close"] > frame["donchian_entry_4h"])
        & (frame["close"].shift(1) <= frame["donchian_entry_4h"].shift(1))
    )
    frame["ema50_rising_4h"] = frame["ema50_4h"] > frame["ema50_4h"].shift(3)
    return frame[
        [
            "date",
            "close_4h",
            "ema50_4h",
            "ema200_4h",
            "rsi_4h",
            "atr_4h",
            "adx_4h",
            "momentum_30d_4h",
            "donchian_entry_4h",
            "donchian_exit_4h",
            "fresh_breakout_4h",
            "ema50_rising_4h",
        ]
    ]


def build_features(base: pd.DataFrame, symbol: str) -> pd.DataFrame:
    frame = base.copy()
    frame["ema20"] = ema(frame["close"], 20)
    frame["ema50"] = ema(frame["close"], 50)
    frame["atr15"] = atr(frame, 14)
    frame["rsi15"] = rsi(frame["close"], 14)
    for rule, suffix in (("1h", "1h"), ("4h", "4h")):
        info = _informative(base, rule, suffix)
        frame = pd.merge_asof(
            frame.sort_values("date"),
            info.sort_values("date"),
            on="date",
            direction="backward",
        )
    fresh = frame["fresh_breakout_4h"].fillna(False)
    fresh_first_15m = fresh & ~fresh.shift(1).fillna(False)
    adx_min = 21 if symbol == "SOLUSDT" else 16
    frame["entry_signal"] = (
        fresh_first_15m
        & (frame["close_4h"] > frame["ema50_4h"])
        & (frame["ema50_4h"] > frame["ema200_4h"])
        & frame["ema50_rising_4h"].fillna(False)
        & (frame["adx_4h"] >= adx_min)
        & (frame["momentum_30d_4h"] >= 0.03)
        & frame["rsi_4h"].between(50, 78)
        & (frame["close_1h"] > frame["ema50_1h"])
        & (frame["ema50_1h"] > frame["ema200_1h"])
        & frame["ema50_rising_1h"].fillna(False)
        & (frame["rsi_1h"] >= 48)
        & (frame["close"] > frame["ema20"])
        & (frame["ema20"] > frame["ema50"])
        & frame["rsi15"].between(48, 78)
        & (frame["atr15"] / frame["close"]).between(0.003, 0.060)
        & frame["research_data_valid"].fillna(False)
        & (frame["volume"] > 0)
    )
    frame["slow_exit"] = (
        (frame["close_4h"] < frame["donchian_exit_4h"])
        | (
            (frame["close_4h"] < frame["ema50_4h"])
            & (frame["momentum_30d_4h"] < 0)
        )
    )
    return frame


def simulate(
    frame: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    policy: str,
) -> list[ScreenTrade]:
    start_i = int(frame["date"].searchsorted(start))
    end_i = int(frame["date"].searchsorted(end))
    entry_signal = frame["entry_signal"].fillna(False).to_numpy(dtype=bool)
    slow_exit = frame["slow_exit"].fillna(False).to_numpy(dtype=bool)
    opens = frame["open"].to_numpy(dtype=float)
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    closes = frame["close"].to_numpy(dtype=float)
    close_4h = frame["close_4h"].to_numpy(dtype=float)
    ema50_4h = frame["ema50_4h"].to_numpy(dtype=float)
    levels = frame["donchian_entry_4h"].to_numpy(dtype=float)
    atr_4h = frame["atr_4h"].to_numpy(dtype=float)
    dates = frame["date"].astype(str).to_numpy()
    trades: list[ScreenTrade] = []
    pos = max(start_i, 1)
    while pos < end_i - 1:
        if not entry_signal[pos]:
            pos += 1
            continue
        entry_i = pos + 1
        entry = float(opens[entry_i])
        breakout_level = float(levels[pos])
        breakout_atr = float(atr_4h[pos])
        hard_stop = entry * 0.945
        roi = entry * 1.50
        profit_floor = entry * 1.05
        floor_armed = False
        exit_i = end_i - 1
        exit_price = float(closes[exit_i])
        reason = "window_end"
        for current in range(entry_i, end_i):
            if floor_armed and lows[current] <= profit_floor:
                exit_i, exit_price, reason = current, profit_floor, "profit_floor"
                break
            if lows[current] <= hard_stop:
                exit_i, exit_price, reason = current, hard_stop, "hard_stop"
                break
            if highs[current] >= roi:
                exit_i, exit_price, reason = current, roi, "roi_50"
                break
            if highs[current] >= entry * 1.30:
                floor_armed = True
            age_bars = current - entry_i
            failed = closes[current] < breakout_level - 0.50 * breakout_atr
            confirmed = failed and close_4h[current] < ema50_4h[current]
            if age_bars <= 48 * 4 and (
                (policy == "active_15m_failure" and failed)
                or (policy == "confirmed_4h_failure" and confirmed)
            ):
                next_i = min(current + 1, end_i - 1)
                exit_i, exit_price, reason = next_i, float(opens[next_i]), policy
                break
            if slow_exit[current]:
                next_i = min(current + 1, end_i - 1)
                exit_i, exit_price, reason = next_i, float(opens[next_i]), "slow_exit"
                break
        pnl = STAKE * net_return(entry, exit_price, FEE)
        trades.append(
            ScreenTrade(
                open_date=str(dates[entry_i]),
                close_date=str(dates[exit_i]),
                entry=entry,
                exit=exit_price,
                pnl=float(pnl),
                exit_reason=reason,
            )
        )
        pos = exit_i + 1
    return trades


def metrics(trades: list[ScreenTrade], fee: float) -> dict[str, float | int]:
    pnl = [STAKE * net_return(trade.entry, trade.exit, fee) for trade in trades]
    gains = sum(value for value in pnl if value > 0)
    losses = -sum(value for value in pnl if value < 0)
    equity = np.cumsum([0.0, *pnl])
    peak = np.maximum.accumulate(equity)
    return {
        "trades": len(trades),
        "pnl": float(sum(pnl)),
        "profit_factor": gains / losses if losses else (99.0 if gains else 0.0),
        "drawdown_usdt": float(np.max(peak - equity)),
        "wins": sum(value > 0 for value in pnl),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cache", type=Path, default=Path("runtime/user_data/v12_public_cache")
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("runtime/user_data/failed_breakout_oos.json"),
    )
    args = parser.parse_args()
    first = pd.Timestamp("2020-08-01", tz="UTC")
    end = pd.Timestamp("2025-07-31", tz="UTC")
    results: dict[str, dict] = {}
    for symbol in SYMBOLS:
        base = download_pair(symbol, first, end, args.cache)
        frame = build_features(base, symbol)
        policies: dict[str, dict] = {}
        for policy in POLICIES:
            folds = []
            all_trades: list[ScreenTrade] = []
            for year in range(5):
                fold_start = first + pd.DateOffset(years=year)
                fold_end = min(fold_start + pd.DateOffset(years=1), end)
                trades = simulate(frame, fold_start, fold_end, policy)
                all_trades.extend(trades)
                folds.append(
                    {
                        "start": str(fold_start),
                        "end": str(fold_end),
                        "base_fee": metrics(trades, FEE),
                        "stress_fee": metrics(trades, STRESS_FEE),
                        "trades": [asdict(trade) for trade in trades],
                    }
                )
            selection = folds[:3]
            validation = folds[3:]
            policies[policy] = {
                "folds": folds,
                "aggregate": {
                    "base_fee": metrics(all_trades, FEE),
                    "stress_fee": metrics(all_trades, STRESS_FEE),
                    "selection_positive_folds": sum(
                        fold["base_fee"]["pnl"] > 0 for fold in selection
                    ),
                    "validation_positive_folds": sum(
                        fold["base_fee"]["pnl"] > 0 for fold in validation
                    ),
                },
            }
            aggregate = policies[policy]["aggregate"]
            print(
                f"{symbol} {policy}: pnl={aggregate['base_fee']['pnl']:.2f} "
                f"trades={aggregate['base_fee']['trades']} "
                f"PF={aggregate['base_fee']['profit_factor']:.2f} "
                f"selection={aggregate['selection_positive_folds']}/3 "
                f"validation={aggregate['validation_positive_folds']}/2",
                flush=True,
            )
        results[symbol] = {
            "data_quality": base.attrs.get("data_quality", {}),
            "policies": policies,
        }
    payload = {
        "schema": "FAILED-BREAKOUT-OLDER-OOS-SCREEN-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "results": results,
        "limitations": [
            "15m approximation, not an exact Freqtrade 1m-detail result",
            "single 80-USDT block and no portfolio slot competition",
            "policies were fixed before reading this output",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
