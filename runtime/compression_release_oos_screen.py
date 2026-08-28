"""Fixed older-window screens for BNB and TRX compression-release reserves."""

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
    download_pair,
    ema,
    net_return,
)


@dataclass(frozen=True)
class Route:
    symbol: str
    quantile: float
    quantile_window: int
    compression_bars: int
    require_two_width_rises: bool
    max_hold_bars: int | None


@dataclass(frozen=True)
class ScreenTrade:
    open_date: str
    close_date: str
    entry: float
    exit: float
    net_return: float
    pnl: float
    exit_reason: str


ROUTES = (
    Route("BNBUSDT", 0.20, 180, 3, False, None),
    Route("TRXUSDT", 0.15, 240, 4, True, 10 * 24 * 4),
)


def build_features(base: pd.DataFrame, route: Route) -> pd.DataFrame:
    x = base.copy()
    x["ema20"] = ema(x["close"], 20)
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
    informative["ema20_4h"] = ema(informative["close"], 20)
    informative["ema100_4h"] = ema(informative["close"], 100)
    informative["ema100_rising12_4h"] = (
        informative["ema100_4h"] > informative["ema100_4h"].shift(12)
    )
    middle = informative["close"].rolling(20, min_periods=20).mean()
    deviation = informative["close"].rolling(20, min_periods=20).std(ddof=0)
    informative["bb_upper_4h"] = middle + 2.0 * deviation
    informative["bb_width_4h"] = 4.0 * deviation / middle
    informative["width_quantile_4h"] = (
        informative["bb_width_4h"]
        .shift(1)
        .rolling(route.quantile_window, min_periods=route.quantile_window)
        .quantile(route.quantile)
    )
    compression = pd.Series(True, index=informative.index)
    for offset in range(1, route.compression_bars + 1):
        compression &= (
            informative["bb_width_4h"].shift(offset)
            <= informative["width_quantile_4h"].shift(offset)
        )
    width_release = informative["bb_width_4h"] > informative["bb_width_4h"].shift(1)
    if route.require_two_width_rises:
        width_release &= (
            informative["bb_width_4h"].shift(1)
            > informative["bb_width_4h"].shift(2)
        )
    informative["release_4h"] = (
        compression
        & width_release
        & (informative["close"] > informative["bb_upper_4h"])
        & informative["ema100_rising12_4h"]
    )
    informative = informative.rename(columns={"date": "informative_date"})[
        ["informative_date", "ema20_4h", "release_4h"]
    ]
    x = pd.merge_asof(
        x.sort_values("date"),
        informative.sort_values("informative_date"),
        left_on="date",
        right_on="informative_date",
        direction="backward",
    )
    minutes_after_release = (
        x["date"] - x["informative_date"]
    ).dt.total_seconds() / 60.0
    x["entry_signal"] = (
        x["release_4h"].fillna(False)
        & minutes_after_release.between(0, 225)
        & (x["close"] > x["ema20"])
        & x["research_data_valid"].fillna(False)
        & (x["volume"] > 0)
    )
    x["exit_signal"] = x["close"] < x["ema20_4h"]
    return x


def simulate(
    frame: pd.DataFrame,
    route: Route,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> list[ScreenTrade]:
    start_i = int(frame["date"].searchsorted(start))
    end_i = int(frame["date"].searchsorted(end))
    entry_signal = frame["entry_signal"].fillna(False).to_numpy(dtype=bool)
    exit_signal = frame["exit_signal"].fillna(False).to_numpy(dtype=bool)
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
        last = end_i - 1
        if route.max_hold_bars is not None:
            last = min(last, entry_i + route.max_hold_bars)
        exit_i = last
        exit_price = float(close_price[last])
        exit_reason = "window_or_time_end"
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
            if exit_signal[pos] and pos + 1 < end_i:
                exit_i = pos + 1
                exit_price = float(open_price[exit_i])
                exit_reason = "ema20_4h_exit"
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
        "--out", type=Path, default=Path("runtime/user_data/compression_oos.json")
    )
    args = parser.parse_args()
    first = pd.Timestamp("2020-08-01", tz="UTC")
    end = pd.Timestamp("2025-07-31", tz="UTC")
    results = {}
    for route in ROUTES:
        base = download_pair(route.symbol, first, end, args.cache)
        frame = build_features(base, route)
        folds = []
        all_trades: list[ScreenTrade] = []
        for year in range(5):
            fold_start = first + pd.DateOffset(years=year)
            fold_end = min(fold_start + pd.DateOffset(years=1), end)
            trades = simulate(frame, route, fold_start, fold_end)
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
                f"{route.symbol} fold{year + 1}: trades={result['trades']} "
                f"pnl={result['pnl']:.2f} PF={result['profit_factor']:.3f} "
                f"DD={result['drawdown_usdt']:.2f}",
                flush=True,
            )
        results[route.symbol] = {
            "route": asdict(route),
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
        print(json.dumps(results[route.symbol]["aggregate"], indent=2), flush=True)
    payload = {
        "schema": "BNB-TRX-COMPRESSION-OLDER-OOS-SCREEN-1",
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
