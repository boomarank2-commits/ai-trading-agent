"""Causal fixed-family screen for pair-local long-only research routes.

This diagnostic deliberately does not modify or emulate the production bot.
It selects a small, transparent strategy family on the first two chronological
years, then reports the untouched third year and a higher-fee stress.  Any
survivor still requires an exact Freqtrade implementation and backtest.
"""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import talib.abstract as ta

START = pd.Timestamp("2023-08-25", tz="UTC")
BOUNDARIES = (
    START,
    pd.Timestamp("2024-08-25", tz="UTC"),
    pd.Timestamp("2025-08-25", tz="UTC"),
    pd.Timestamp("2026-08-25", tz="UTC"),
)
STAKE_USDT = 80.0
HARD_STOP = 0.055


@dataclass(frozen=True)
class Candidate:
    family: str
    parameters: dict[str, float | int]
    entry: pd.Series
    exit: pd.Series


@dataclass(frozen=True)
class Metrics:
    profit_usdt: float
    trades: int
    wins: int
    losses: int
    profit_factor: float
    max_drawdown_pct: float


def _crossed_above(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left > right) & (left.shift(1) <= right.shift(1))


def _crossed_below(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left < right) & (left.shift(1) >= right.shift(1))


def _supertrend(
    frame: pd.DataFrame, period: int, multiplier: float
) -> tuple[pd.Series, pd.Series]:
    atr = pd.Series(ta.ATR(frame, timeperiod=period), index=frame.index)
    midpoint = (frame["high"] + frame["low"]) / 2.0
    upper = midpoint + multiplier * atr
    lower = midpoint - multiplier * atr
    final_upper = upper.copy()
    final_lower = lower.copy()
    direction = pd.Series(0, index=frame.index, dtype="int8")
    trend = pd.Series(np.nan, index=frame.index, dtype="float64")

    for pos in range(1, len(frame)):
        prev = pos - 1
        if pd.isna(atr.iat[pos]):
            continue
        if pd.isna(final_upper.iat[prev]) or frame["close"].iat[prev] > final_upper.iat[prev]:
            final_upper.iat[pos] = upper.iat[pos]
        else:
            final_upper.iat[pos] = min(upper.iat[pos], final_upper.iat[prev])
        if pd.isna(final_lower.iat[prev]) or frame["close"].iat[prev] < final_lower.iat[prev]:
            final_lower.iat[pos] = lower.iat[pos]
        else:
            final_lower.iat[pos] = max(lower.iat[pos], final_lower.iat[prev])

        previous_direction = int(direction.iat[prev])
        if previous_direction <= 0 and frame["close"].iat[pos] > final_upper.iat[prev]:
            direction.iat[pos] = 1
        elif previous_direction >= 0 and frame["close"].iat[pos] < final_lower.iat[prev]:
            direction.iat[pos] = -1
        else:
            direction.iat[pos] = previous_direction or -1
        trend.iat[pos] = (
            final_lower.iat[pos] if direction.iat[pos] > 0 else final_upper.iat[pos]
        )
    return trend, direction


def _base_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["ema20"] = ta.EMA(result, timeperiod=20)
    result["ema50"] = ta.EMA(result, timeperiod=50)
    result["ema100"] = ta.EMA(result, timeperiod=100)
    result["ema200"] = ta.EMA(result, timeperiod=200)
    result["atr14"] = ta.ATR(result, timeperiod=14)
    result["adx14"] = ta.ADX(result, timeperiod=14)
    result["rsi14"] = ta.RSI(result, timeperiod=14)
    result["momentum30d"] = result["close"] / result["close"].shift(180) - 1.0
    result["momentum60d"] = result["close"] / result["close"].shift(360) - 1.0
    macd = ta.MACD(result, fastperiod=12, slowperiod=26, signalperiod=9)
    result["macd"] = macd["macd"]
    result["macdsignal"] = macd["macdsignal"]
    return result


def _candidate_families(frame: pd.DataFrame) -> list[Candidate]:
    candidates: list[Candidate] = []
    close = frame["close"]
    macro100 = (close > frame["ema100"]) & (frame["ema100"] > frame["ema100"].shift(12))
    macro200 = (close > frame["ema200"]) & (frame["ema200"] > frame["ema200"].shift(12))

    for fast, slow, adx_min, macro_period in itertools.product(
        (12, 20, 30), (40, 50, 80), (12, 18, 24), (100, 200)
    ):
        if fast >= slow:
            continue
        ema_fast = ta.EMA(frame, timeperiod=fast)
        ema_slow = ta.EMA(frame, timeperiod=slow)
        macro = macro100 if macro_period == 100 else macro200
        entry = _crossed_above(ema_fast, ema_slow) & macro & (frame["adx14"] >= adx_min)
        exit_signal = _crossed_below(ema_fast, ema_slow) | (close < ema_slow)
        candidates.append(
            Candidate(
                "ema_trend",
                {"fast": fast, "slow": slow, "adx_min": adx_min, "macro": macro_period},
                entry,
                exit_signal,
            )
        )

    for period, multiplier, macro_period in itertools.product(
        (10, 14, 20), (2.0, 3.0, 4.0), (100, 200)
    ):
        _, direction = _supertrend(frame, period, multiplier)
        macro = macro100 if macro_period == 100 else macro200
        entry = (direction > 0) & (direction.shift(1) <= 0) & macro
        exit_signal = (direction < 0) & (direction.shift(1) >= 0)
        candidates.append(
            Candidate(
                "supertrend",
                {"period": period, "multiplier": multiplier, "macro": macro_period},
                entry,
                exit_signal,
            )
        )

    for breakout, exit_lookback, macro_period, momentum_days in itertools.product(
        (20, 40, 80, 120), (10, 20, 40), (100, 200), (30, 60)
    ):
        prior_high = frame["high"].shift(1).rolling(breakout, min_periods=breakout).max()
        prior_low = frame["low"].shift(1).rolling(exit_lookback, min_periods=exit_lookback).min()
        macro = macro100 if macro_period == 100 else macro200
        momentum = frame["momentum30d"] if momentum_days == 30 else frame["momentum60d"]
        entry = _crossed_above(close, prior_high) & macro & (momentum > 0)
        exit_signal = close < prior_low
        candidates.append(
            Candidate(
                "macro_donchian",
                {
                    "breakout": breakout,
                    "exit": exit_lookback,
                    "macro": macro_period,
                    "momentum_days": momentum_days,
                },
                entry,
                exit_signal,
            )
        )

    for lower, recover, upper, macro_period in itertools.product(
        (30, 35, 40), (40, 45, 50), (60, 65, 70), (100, 200)
    ):
        oversold_recent = (
            (frame["rsi14"] < lower)
            .shift(1)
            .rolling(12, min_periods=1)
            .max()
            .fillna(False)
            .astype(bool)
        )
        macro = macro100 if macro_period == 100 else macro200
        entry = (
            oversold_recent
            & _crossed_above(
                frame["rsi14"], pd.Series(recover, index=frame.index)
            )
            & macro
        )
        exit_signal = (frame["rsi14"] > upper) | (close < frame[f"ema{macro_period}"])
        candidates.append(
            Candidate(
                "rsi_trend_pullback",
                {"lower": lower, "recover": recover, "upper": upper, "macro": macro_period},
                entry,
                exit_signal,
            )
        )

    for adx_min, macro_period, exit_mode in itertools.product(
        (12, 18, 24), (100, 200), (20, 50)
    ):
        macro = macro100 if macro_period == 100 else macro200
        entry = (
            _crossed_above(frame["macd"], frame["macdsignal"])
            & macro
            & (frame["adx14"] >= adx_min)
        )
        exit_line = frame["ema20"] if exit_mode == 20 else frame["ema50"]
        exit_signal = _crossed_below(frame["macd"], frame["macdsignal"]) | (close < exit_line)
        candidates.append(
            Candidate(
                "macd_trend",
                {"adx_min": adx_min, "macro": macro_period, "exit_ema": exit_mode},
                entry,
                exit_signal,
            )
        )
    return candidates


def _simulate(
    frame: pd.DataFrame,
    candidate: Candidate,
    start: pd.Timestamp,
    end: pd.Timestamp,
    fee: float,
) -> Metrics:
    dates = pd.to_datetime(frame["date"], utc=True)
    date_values = dates.astype("int64").to_numpy()
    open_rates = frame["open"].to_numpy(dtype="float64")
    low_rates = frame["low"].to_numpy(dtype="float64")
    close_rates = frame["close"].to_numpy(dtype="float64")
    entry_flags = candidate.entry.fillna(False).to_numpy(dtype="bool")
    exit_flags = candidate.exit.fillna(False).to_numpy(dtype="bool")
    date_unit = getattr(dates.dtype, "unit", "ns")
    start_value = start.as_unit(date_unit).asm8.astype("int64")
    end_value = end.as_unit(date_unit).asm8.astype("int64")

    active = False
    entry_rate = 0.0
    pending_entry = False
    pending_exit = False
    profits: list[float] = []
    last_close_rate: float | None = None

    for pos in range(1, len(frame)):
        date_value = date_values[pos]
        if date_value < start_value:
            continue
        if date_value >= end_value:
            break

        last_close_rate = float(close_rates[pos])

        open_rate = float(open_rates[pos])
        if active and pending_exit:
            gross = open_rate / entry_rate
            profits.append(STAKE_USDT * (gross * (1.0 - fee) / (1.0 + fee) - 1.0))
            active = False
            pending_exit = False
        if not active and pending_entry:
            entry_rate = open_rate
            active = True
            pending_entry = False

        if active:
            stop_rate = entry_rate * (1.0 - HARD_STOP)
            if float(low_rates[pos]) <= stop_rate:
                gross = stop_rate / entry_rate
                profits.append(STAKE_USDT * (gross * (1.0 - fee) / (1.0 + fee) - 1.0))
                active = False
                pending_exit = False

        if active and bool(exit_flags[pos]):
            pending_exit = True
        elif not active and bool(entry_flags[pos]):
            pending_entry = True

    if active and last_close_rate is not None:
        gross = last_close_rate / entry_rate
        profits.append(STAKE_USDT * (gross * (1.0 - fee) / (1.0 + fee) - 1.0))

    positive = sum(value for value in profits if value > 0)
    negative = -sum(value for value in profits if value < 0)
    equity = np.cumsum([0.0, *profits])
    peaks = np.maximum.accumulate(equity)
    drawdown = float(np.max(peaks - equity)) if len(equity) else 0.0
    return Metrics(
        profit_usdt=round(float(sum(profits)), 4),
        trades=len(profits),
        wins=sum(value > 0 for value in profits),
        losses=sum(value <= 0 for value in profits),
        profit_factor=(
            round(positive / negative, 4)
            if negative > 0
            else (999.0 if positive > 0 else 0.0)
        ),
        max_drawdown_pct=round(drawdown / 250.0 * 100.0, 4),
    )


def run(data_file: Path, fee: float, stress_fee: float) -> dict[str, object]:
    frame = pd.read_feather(data_file).sort_values("date").reset_index(drop=True)
    frame = _base_indicators(frame)
    candidates = _candidate_families(frame)
    rows: list[dict[str, object]] = []
    for candidate in candidates:
        years = [
            _simulate(frame, candidate, BOUNDARIES[index], BOUNDARIES[index + 1], fee)
            for index in range(3)
        ]
        stress = _simulate(frame, candidate, BOUNDARIES[0], BOUNDARIES[-1], stress_fee)
        selection_profit = years[0].profit_usdt + years[1].profit_usdt
        selection_pass = (
            years[0].profit_usdt > 0
            and years[1].profit_usdt > 0
            and years[0].trades + years[1].trades >= 8
        )
        validation_pass = years[2].profit_usdt > 0 and years[2].trades >= 3
        stress_pass = stress.profit_usdt > 0 and stress.profit_factor > 1.0
        rows.append(
            {
                "family": candidate.family,
                "parameters": candidate.parameters,
                "selection_profit_usdt": round(selection_profit, 4),
                "selection_pass": selection_pass,
                "validation_pass": validation_pass,
                "stress_pass": stress_pass,
                "all_gates_pass": selection_pass and validation_pass and stress_pass,
                "years": [asdict(value) for value in years],
                "stress": asdict(stress),
            }
        )
    rows.sort(
        key=lambda row: (
            bool(row["all_gates_pass"]),
            min(float(year["profit_usdt"]) for year in row["years"]),
            float(row["stress"]["profit_usdt"]),
        ),
        reverse=True,
    )
    return {
        "schema_version": 2,
        "window_end_liquidation": True,
        "data_file": str(data_file.resolve()),
        "fee_per_side": fee,
        "stress_fee_per_side": stress_fee,
        "candidate_count": len(rows),
        "survivor_count": sum(bool(row["all_gates_pass"]) for row in rows),
        "top_candidates": rows[:30],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("--fee", type=float, default=0.002)
    parser.add_argument("--stress-fee", type=float, default=0.003)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.data_file, args.fee, args.stress_fee)
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
