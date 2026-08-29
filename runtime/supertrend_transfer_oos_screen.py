"""Screen a conservative approximation of one accepted Supertrend family.

The parameters are copied unchanged from the accepted DOGE V12.30 route.
This is deliberately not a parameter sweep: it asks whether that already
known family transfers to another pair across five older annual folds before
any exact 2023-2026 result may be opened.  The screen additionally requires
15m close above EMA20; the active DOGE route itself does not.  Therefore this
is directional evidence, not an exact reproduction of the bot route.
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
    download_pair,
    ema,
    net_return,
)
from runtime.v12_37_sol_oos_screen import supertrend_direction

SYMBOLS = ("SOLUSDT", "BNBUSDT", "LINKUSDT", "TRXUSDT", "LTCUSDT")


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
    frame = base.copy()
    frame["ema20"] = ema(frame["close"], 20)
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
    informative["ema100_4h"] = ema(informative["close"], 100)
    informative["ema100_rising12_4h"] = (
        informative["ema100_4h"] > informative["ema100_4h"].shift(12)
    )
    direction = supertrend_direction(informative, period=20, multiplier=3.0)
    informative["event_4h"] = (
        (direction > 0)
        & (direction.shift(1).fillna(0) <= 0)
        & (informative["close"] > informative["ema100_4h"])
        & informative["ema100_rising12_4h"]
    )
    informative["exit_4h"] = (direction < 0) & (
        direction.shift(1).fillna(0) >= 0
    )
    informative = informative.rename(columns={"date": "informative_date"})[
        ["informative_date", "event_4h", "exit_4h"]
    ]
    frame = pd.merge_asof(
        frame.sort_values("date"),
        informative.sort_values("informative_date"),
        left_on="date",
        right_on="informative_date",
        direction="backward",
    )
    minutes_after_event = (
        frame["date"] - frame["informative_date"]
    ).dt.total_seconds() / 60.0
    frame["entry_signal"] = (
        frame["event_4h"].fillna(False)
        & minutes_after_event.between(0, 225)
        & (frame["close"] > frame["ema20"])
        & frame["research_data_valid"].fillna(False)
        & (frame["volume"] > 0)
    )
    frame["exit_signal"] = frame["exit_4h"].fillna(False)
    return frame


def simulate(
    frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
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
        stop_price = entry * (1.0 - 0.055)
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
                exit_reason = "supertrend_flip"
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
    pnl = [float(STAKE * net_return(row.entry, row.exit, fee)) for row in trades]
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
        "--out", type=Path, default=Path("runtime/user_data/supertrend_transfer.json")
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
            result = fold["base_fee"]
            assert isinstance(result, dict)
            print(
                f"{symbol} fold{year + 1}: trades={result['trades']} "
                f"pnl={result['pnl']:.2f} PF={result['profit_factor']:.3f}",
                flush=True,
            )
        selection_positive = sum(
            float(fold["base_fee"]["pnl"]) > 0 for fold in folds[:3]  # type: ignore[index]
        )
        validation_positive = sum(
            float(fold["base_fee"]["pnl"]) > 0 for fold in folds[3:]  # type: ignore[index]
        )
        aggregate = {
            "base_fee": metrics(all_trades, FEE),
            "stress_fee": metrics(all_trades, STRESS_FEE),
            "selection_positive_folds": selection_positive,
            "selection_fold_count": 3,
            "validation_positive_folds": validation_positive,
            "validation_fold_count": 2,
            "opens_exact_candidate": selection_positive >= 2
            and validation_positive == 2
            and metrics(all_trades, STRESS_FEE)["pnl"] > 0
            and metrics(all_trades, STRESS_FEE)["profit_factor"] >= 1.20
            and len(all_trades) >= 15,
        }
        results[symbol] = {
            "data_quality": base.attrs.get("data_quality", {}),
            "folds": folds,
            "aggregate": aggregate,
        }
        print(json.dumps(aggregate, indent=2), flush=True)
    payload = {
        "schema": "FIXED-DOGE-SUPERTREND20X3-TRANSFER-OLDER-OOS-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "fixed_route": {
            "entry": "4h Supertrend20x3 long flip above rising EMA100",
            "execution": "first available closed 15m candle above EMA20",
            "exit": "4h Supertrend20x3 short flip; hard stop -5.5%; ROI 50%",
            "stake_usdt": STAKE,
            "pyramiding": False,
        },
        "results": results,
        "limitations": [
            "15m screen, not exact Freqtrade 1m-detail execution",
            "protections and shared-wallet slot competition are not simulated",
            "parameters copied unchanged from accepted DOGE V12.30; no tuning",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
