"""Fixed Bollinger 20/2 range-reversion screen on five weak pairs.

The route and gates follow the research master plan and are fixed before the
screen is run.  There is no threshold sweep and no exact-period result is
used to select or tune parameters.
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
    download_pair,
    ema,
    net_return,
)

SYMBOLS = ("SOLUSDT", "BNBUSDT", "LINKUSDT", "TRXUSDT", "LTCUSDT")


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
    frame["bb_middle"] = frame["close"].rolling(20, min_periods=20).mean()
    deviation = frame["close"].rolling(20, min_periods=20).std(ddof=0)
    frame["bb_lower"] = frame["bb_middle"] - 2.0 * deviation

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
    informative["ema50"] = ema(informative["close"], 50)
    informative["ema200"] = ema(informative["close"], 200)
    informative["adx14"] = adx(informative, 14)
    informative["range_regime"] = (
        (informative["adx14"] <= 18.0)
        & (
            (informative["ema50"] - informative["ema200"]).abs()
            / informative["close"]
            <= 0.03
        )
    )
    informative = informative.rename(columns={"date": "informative_date"})[
        ["informative_date", "range_regime"]
    ]
    frame = pd.merge_asof(
        frame.sort_values("date"),
        informative.sort_values("informative_date"),
        left_on="date",
        right_on="informative_date",
        direction="backward",
    )
    frame["entry_signal"] = (
        (frame["close"].shift(1) <= frame["bb_lower"].shift(1))
        & (frame["close"] > frame["bb_lower"])
        & (frame["close"] < frame["bb_middle"])
        & frame["range_regime"].fillna(False)
        & frame["research_data_valid"].fillna(False)
        & (frame["volume"] > 0)
    )
    frame["exit_signal"] = frame["close"] >= frame["bb_middle"]
    return frame


def simulate(
    frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> list[ScreenTrade]:
    start_i = int(frame["date"].searchsorted(start))
    end_i = int(frame["date"].searchsorted(end))
    entries = frame["entry_signal"].fillna(False).to_numpy(dtype=bool)
    exits = frame["exit_signal"].fillna(False).to_numpy(dtype=bool)
    opens = frame["open"].to_numpy(dtype=float)
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    closes = frame["close"].to_numpy(dtype=float)
    dates = frame["date"].astype(str).to_numpy()
    trades: list[ScreenTrade] = []
    i = max(start_i, 1)
    while i < end_i - 1:
        if not entries[i]:
            i += 1
            continue
        entry_i = i + 1
        entry = float(opens[entry_i])
        stop_price = entry * 0.945
        roi_price = entry * 1.50
        exit_i = end_i - 1
        exit_price = float(closes[exit_i])
        reason = "window_end"
        for pos in range(entry_i, end_i):
            if lows[pos] <= stop_price:
                exit_i, exit_price, reason = pos, stop_price, "stop_loss"
                break
            if highs[pos] >= roi_price:
                exit_i, exit_price, reason = pos, roi_price, "roi_50"
                break
            if exits[pos] and pos + 1 < end_i:
                exit_i = pos + 1
                exit_price = float(opens[exit_i])
                reason = "bollinger_middle"
                break
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
        "--out", type=Path, default=Path("runtime/user_data/bollinger_range.json")
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
            and len(all_trades) >= 30,
        }
        results[symbol] = {
            "data_quality": base.attrs.get("data_quality", {}),
            "folds": folds,
            "aggregate": aggregate,
        }
        print(json.dumps(aggregate, indent=2), flush=True)
    payload = {
        "schema": "FIXED-BOLLINGER20X2-RANGE-OLDER-OOS-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "fixed_route": {
            "range": "4h ADX14 <= 18 and abs(EMA50-EMA200)/close <= 3%",
            "entry": (
                "15m prior close at/below lower Bollinger20x2 then close back "
                "inside below middle"
            ),
            "exit": "15m middle band; hard stop -5.5%; ROI 50%",
            "stake_usdt": STAKE,
            "pyramiding": False,
        },
        "results": results,
        "limitations": [
            "15m causal screen, not exact Freqtrade 1m-detail execution",
            "protections and shared-wallet slot competition are not simulated",
            "one fixed master-plan route; no threshold sweep",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
