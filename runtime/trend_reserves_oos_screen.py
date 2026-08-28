"""Fixed older-window screens for five pair-local trend reserve hypotheses."""

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
    rsi,
)
from runtime.v12_37_sol_oos_screen import supertrend_direction


@dataclass(frozen=True)
class ScreenTrade:
    open_date: str
    close_date: str
    entry: float
    exit: float
    net_return: float
    pnl: float
    exit_reason: str


SYMBOLS = ("BTCUSDT", "XRPUSDT", "DOGEUSDT", "LINKUSDT", "BCHUSDT")


def _informative(base: pd.DataFrame, symbol: str) -> pd.DataFrame:
    frame = (
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
    for period in (20, 100, 150, 200):
        frame[f"ema{period}_4h"] = ema(frame["close"], period)
    frame["ema100_rising6_4h"] = frame["ema100_4h"] > frame["ema100_4h"].shift(6)
    frame["ema100_rising12_4h"] = frame["ema100_4h"] > frame["ema100_4h"].shift(12)
    frame["ema150_rising6_4h"] = frame["ema150_4h"] > frame["ema150_4h"].shift(6)
    frame["ema200_rising12_4h"] = frame["ema200_4h"] > frame["ema200_4h"].shift(12)
    frame["adx_4h"] = adx(frame, 14)
    frame["atr_4h"] = atr(frame, 14)
    frame["atr_pct_4h"] = frame["atr_4h"] / frame["close"]
    frame["momentum30d_4h"] = frame["close"] / frame["close"].shift(180) - 1.0
    frame["momentum7d_4h"] = frame["close"] / frame["close"].shift(42) - 1.0
    frame["volume_mean_4h"] = (
        frame["volume"].shift(1).rolling(20, min_periods=20).mean()
    )
    frame["volume_ratio_4h"] = frame["volume"] / frame["volume_mean_4h"]
    frame["prior_close_high6_4h"] = (
        frame["close"].shift(1).rolling(6, min_periods=6).max()
    )
    frame["atr_q20_4h"] = (
        frame["atr_pct_4h"].shift(1).rolling(180, min_periods=180).quantile(0.20)
    )
    frame["atr_q50_4h"] = (
        frame["atr_pct_4h"].shift(1).rolling(180, min_periods=180).quantile(0.50)
    )
    frame["atr_q75_4h"] = (
        frame["atr_pct_4h"].shift(1).rolling(180, min_periods=180).quantile(0.75)
    )
    frame["atr_q80_4h"] = (
        frame["atr_pct_4h"].shift(1).rolling(180, min_periods=180).quantile(0.80)
    )
    frame["atr_q90_4h"] = (
        frame["atr_pct_4h"].shift(1).rolling(180, min_periods=180).quantile(0.90)
    )
    frame["keltner_upper_4h"] = frame["ema20_4h"] + 2.0 * frame["atr_4h"]

    if symbol == "BTCUSDT":
        direction = supertrend_direction(frame, period=24, multiplier=3.5)
        frame["event_4h"] = (
            (direction > 0)
            & (direction.shift(1).fillna(0) <= 0)
            & (frame["close"] > frame["ema200_4h"])
            & frame["ema200_rising12_4h"]
            & (frame["momentum30d_4h"] > 0)
        )
        frame["route_exit_4h"] = (
            ((direction < 0) & (direction.shift(1).fillna(0) >= 0))
            | (frame["close"] < frame["ema200_4h"])
        )
    elif symbol == "XRPUSDT":
        frame["event_4h"] = (
            (frame["momentum7d_4h"] > 0.05)
            & (frame["momentum7d_4h"].shift(1) <= 0.05)
            & (frame["close"] > frame["ema100_4h"])
            & frame["ema100_rising6_4h"]
            & (frame["adx_4h"] >= 18)
        )
        frame["route_exit_4h"] = (
            (frame["momentum7d_4h"] <= 0)
            | (frame["close"] < frame["ema100_4h"])
        )
    elif symbol == "DOGEUSDT":
        volatility_cross = (
            (frame["atr_pct_4h"] > frame["atr_q75_4h"])
            & (frame["atr_pct_4h"].shift(1) <= frame["atr_q75_4h"].shift(1))
        )
        frame["event_4h"] = (
            volatility_cross
            & (frame["volume_ratio_4h"] >= 1.5)
            & (frame["close"] > frame["ema100_4h"])
            & frame["ema100_rising12_4h"]
            & (frame["close"] > frame["prior_close_high6_4h"])
        )
        frame["route_exit_4h"] = frame["close"] < frame["ema20_4h"]
    elif symbol == "LINKUSDT":
        frame["event_4h"] = (
            (frame["close"] > frame["keltner_upper_4h"])
            & (frame["close"].shift(1) <= frame["keltner_upper_4h"].shift(1))
            & (frame["close"] > frame["ema100_4h"])
            & frame["ema100_rising12_4h"]
            & (frame["adx_4h"] >= 18)
            & (frame["atr_pct_4h"] <= frame["atr_q90_4h"])
        )
        frame["route_exit_4h"] = frame["close"] < frame["ema20_4h"]
    elif symbol == "BCHUSDT":
        direction = supertrend_direction(frame, period=18, multiplier=3.5)
        frame["event_4h"] = (
            (direction > 0)
            & (direction.shift(1).fillna(0) <= 0)
            & (frame["close"] > frame["ema150_4h"])
            & frame["ema150_rising6_4h"]
            & frame["atr_pct_4h"].between(frame["atr_q20_4h"], frame["atr_q80_4h"])
        )
        frame["route_exit_4h"] = (
            (direction < 0) & (direction.shift(1).fillna(0) >= 0)
        )
    else:
        raise ValueError(symbol)
    return frame.rename(columns={"date": "informative_date"})


def build_features(base: pd.DataFrame, symbol: str) -> pd.DataFrame:
    x = base.copy()
    x["ema20"] = ema(x["close"], 20)
    x["rsi14"] = rsi(x["close"], 14)
    informative = _informative(base, symbol)
    keep = [
        "informative_date",
        "event_4h",
        "route_exit_4h",
        "atr_pct_4h",
        "atr_q50_4h",
    ]
    x = pd.merge_asof(
        x.sort_values("date"),
        informative[keep].sort_values("informative_date"),
        left_on="date",
        right_on="informative_date",
        direction="backward",
    )
    minutes_after_event = (
        x["date"] - x["informative_date"]
    ).dt.total_seconds() / 60.0
    event_window = minutes_after_event.between(0, 225)
    execution = x["close"] > x["ema20"]
    if symbol == "BTCUSDT":
        execution &= x["rsi14"].between(50, 75)
    elif symbol == "XRPUSDT":
        execution &= x["rsi14"] <= 75
    elif symbol == "DOGEUSDT":
        execution &= x["rsi14"].between(50, 78)
    elif symbol == "BCHUSDT":
        event_window = minutes_after_event == 0
    x["entry_signal"] = (
        x["event_4h"].fillna(False)
        & event_window
        & execution
        & x["research_data_valid"].fillna(False)
        & (x["volume"] > 0)
    )
    x["exit_signal"] = x["route_exit_4h"].fillna(False)
    return x


def simulate(
    frame: pd.DataFrame, symbol: str, start: pd.Timestamp, end: pd.Timestamp
) -> list[ScreenTrade]:
    start_i = int(frame["date"].searchsorted(start))
    end_i = int(frame["date"].searchsorted(end))
    entry_signal = frame["entry_signal"].fillna(False).to_numpy(dtype=bool)
    exit_signal = frame["exit_signal"].fillna(False).to_numpy(dtype=bool)
    open_price = frame["open"].to_numpy(dtype=float)
    high_price = frame["high"].to_numpy(dtype=float)
    low_price = frame["low"].to_numpy(dtype=float)
    close_price = frame["close"].to_numpy(dtype=float)
    atr_pct = frame["atr_pct_4h"].to_numpy(dtype=float)
    atr_median = frame["atr_q50_4h"].to_numpy(dtype=float)
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
            doge_vol_exit = (
                symbol == "DOGEUSDT"
                and pos - entry_i >= 96
                and atr_pct[pos] < atr_median[pos]
            )
            if (exit_signal[pos] or doge_vol_exit) and pos + 1 < end_i:
                exit_i = pos + 1
                exit_price = float(open_price[exit_i])
                exit_reason = "route_exit"
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
        "--out", type=Path, default=Path("runtime/user_data/trend_reserves_oos.json")
    )
    args = parser.parse_args()
    first = pd.Timestamp("2020-08-01", tz="UTC")
    end = pd.Timestamp("2025-07-31", tz="UTC")
    results = {}
    for symbol in SYMBOLS:
        base = download_pair(symbol, first, end, args.cache)
        frame = build_features(base, symbol)
        folds = []
        all_trades: list[ScreenTrade] = []
        for year in range(5):
            fold_start = first + pd.DateOffset(years=year)
            fold_end = min(fold_start + pd.DateOffset(years=1), end)
            trades = simulate(frame, symbol, fold_start, fold_end)
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
                f"{symbol} fold{year + 1}: trades={result['trades']} "
                f"pnl={result['pnl']:.2f} PF={result['profit_factor']:.3f} "
                f"DD={result['drawdown_usdt']:.2f}",
                flush=True,
            )
        results[symbol] = {
            "data_quality": base.attrs.get("data_quality", {}),
            "folds": folds,
            "aggregate": {
                "base_fee": metrics(all_trades, FEE),
                "stress_fee": metrics(all_trades, STRESS_FEE),
                "positive_folds": sum(
                    fold["base_fee"]["pnl"] > 0 for fold in folds
                ),
                "fold_count": len(folds),
            },
        }
        print(json.dumps(results[symbol]["aggregate"], indent=2), flush=True)
    payload = {
        "schema": "PAIR-LOCAL-TREND-RESERVES-OLDER-OOS-SCREEN-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "results": results,
        "limitations": [
            "15m screening simulation, not an exact Freqtrade 1m-detail result",
            "protections and shared-wallet slot competition are not simulated",
            "fixed Deep Research parameters; no post-result tuning is allowed",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
