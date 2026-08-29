"""Fixed deterministic UTC opening-range breakout/retest research screen.

The 00:00-04:00 UTC range, one-range target and four-hour retest window are
fixed before execution.  This is one route, not a parameter search.
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
    download_pair,
    net_return,
)

SYMBOLS = ("SOLUSDT", "BNBUSDT", "LINKUSDT", "TRXUSDT", "LTCUSDT")
OPENING_RANGE_BARS = 16
RETEST_BARS = 16


@dataclass(frozen=True)
class ScreenTrade:
    open_date: str
    close_date: str
    entry: float
    exit: float
    pnl: float
    exit_reason: str


def build_features(base: pd.DataFrame) -> pd.DataFrame:
    frame = base.copy()
    frame["utc_day"] = frame["date"].dt.floor("D")
    frame["day_bar"] = frame.groupby("utc_day", sort=False).cumcount()
    opening = frame["day_bar"] < OPENING_RANGE_BARS
    frame["or_high"] = (
        frame["high"].where(opening).groupby(frame["utc_day"]).transform("max")
    )
    frame["or_low"] = (
        frame["low"].where(opening).groupby(frame["utc_day"]).transform("min")
    )
    frame["or_width"] = frame["or_high"] - frame["or_low"]
    after_range = frame["day_bar"] >= OPENING_RANGE_BARS
    breakout = (
        after_range
        & (frame["close"] > frame["or_high"])
        & (frame["close"].shift(1) <= frame["or_high"])
    )
    breakout_bar = frame["day_bar"].where(breakout)
    first_breakout_bar = breakout_bar.groupby(frame["utc_day"]).transform("min")
    retest_window = (
        (frame["day_bar"] > first_breakout_bar)
        & (frame["day_bar"] <= first_breakout_bar + RETEST_BARS)
    )
    frame["entry_signal"] = (
        retest_window
        & (frame["low"] <= frame["or_high"])
        & (frame["close"] > frame["or_high"])
        & frame["research_data_valid"].fillna(False)
        & (frame["or_width"] > 0)
        & (frame["volume"] > 0)
    )
    return frame


def simulate(
    frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> list[ScreenTrade]:
    start_i = int(frame["date"].searchsorted(start))
    end_i = int(frame["date"].searchsorted(end))
    entries = frame["entry_signal"].fillna(False).to_numpy(dtype=bool)
    opens = frame["open"].to_numpy(dtype=float)
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    closes = frame["close"].to_numpy(dtype=float)
    or_width = frame["or_width"].to_numpy(dtype=float)
    day_bar = frame["day_bar"].to_numpy(dtype=int)
    dates = frame["date"].astype(str).to_numpy()
    trades: list[ScreenTrade] = []
    i = max(start_i, 1)
    while i < end_i - 1:
        if not entries[i]:
            i += 1
            continue
        entry_i = i + 1
        entry = float(opens[entry_i])
        target = entry + float(or_width[i])
        stop_price = entry * 0.945
        exit_i = end_i - 1
        exit_price = float(closes[exit_i])
        reason = "window_end"
        for pos in range(entry_i, end_i):
            if lows[pos] <= stop_price:
                exit_i, exit_price, reason = pos, stop_price, "stop_loss"
                break
            if highs[pos] >= target:
                exit_i, exit_price, reason = pos, target, "opening_range_target"
                break
            if day_bar[pos] == 95 and pos + 1 < end_i:
                exit_i = pos + 1
                exit_price = float(opens[exit_i])
                reason = "utc_day_end"
                break
        if not np.isfinite(exit_price):
            raise RuntimeError("non-finite ORB exit price")
        trades.append(
            ScreenTrade(
                open_date=str(dates[entry_i]),
                close_date=str(dates[exit_i]),
                entry=entry,
                exit=exit_price,
                pnl=float(STAKE * net_return(entry, exit_price, FEE)),
                exit_reason=reason,
            )
        )
        i = exit_i + 1
    return trades


def metrics(trades: list[ScreenTrade], fee: float) -> dict[str, float | int]:
    pnl = [float(STAKE * net_return(row.entry, row.exit, fee)) for row in trades]
    gross_profit = sum(value for value in pnl if value > 0)
    gross_loss = -sum(value for value in pnl if value < 0)
    equity = peak = drawdown = 0.0
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
        "--out", type=Path, default=Path("runtime/user_data/orb_retest.json")
    )
    args = parser.parse_args()
    first = pd.Timestamp("2020-08-01", tz="UTC")
    end = pd.Timestamp("2025-07-31", tz="UTC")
    results: dict[str, object] = {}
    for symbol in SYMBOLS:
        base = download_pair(symbol, first, end, args.cache)
        frame = build_features(base)
        folds: list[dict[str, object]] = []
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
            row = fold["base_fee"]
            assert isinstance(row, dict)
            print(
                f"{symbol} fold{year + 1}: trades={row['trades']} "
                f"pnl={row['pnl']:.2f} PF={row['profit_factor']:.3f}",
                flush=True,
            )
        selection_positive = sum(
            float(fold["base_fee"]["pnl"]) > 0 for fold in folds[:3]  # type: ignore[index]
        )
        validation_positive = sum(
            float(fold["base_fee"]["pnl"]) > 0 for fold in folds[3:]  # type: ignore[index]
        )
        aggregate_base = metrics(all_trades, FEE)
        aggregate_stress = metrics(all_trades, STRESS_FEE)
        aggregate = {
            "base_fee": aggregate_base,
            "stress_fee": aggregate_stress,
            "selection_positive_folds": selection_positive,
            "validation_positive_folds": validation_positive,
            "opens_exact_candidate": selection_positive >= 2
            and validation_positive == 2
            and aggregate_stress["pnl"] >= 30.0
            and aggregate_stress["profit_factor"] >= 1.30
            and len(all_trades) >= 100,
        }
        results[symbol] = {
            "data_quality": base.attrs.get("data_quality", {}),
            "folds": folds,
            "aggregate": aggregate,
        }
        print(json.dumps(aggregate, indent=2), flush=True)
    payload = {
        "schema": "FIXED-UTC-4H-ORB-RETEST-OLDER-OOS-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "fixed_route": {
            "opening_range": "00:00-04:00 UTC on closed 15m candles",
            "entry": "first retest close above range high within 4h after confirmed breakout",
            "exit": "one opening-range width target or UTC day end; hard stop -5.5%",
            "stake_usdt": STAKE,
            "pyramiding": False,
        },
        "results": results,
        "limitations": [
            "15m causal screen, not exact Freqtrade 1m-detail execution",
            "protections and shared-wallet slot competition are not simulated",
            "one deterministic UTC route; no threshold sweep",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
