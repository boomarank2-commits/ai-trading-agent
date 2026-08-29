"""Hixton HIXTON-V1 baseline for the isolated ten-coin research branch.

The implementation reproduces the user-supplied indicator logic without copying
its presentation code. It is intentionally a measurement baseline, not a claim
of profitability and not a real-money candidate.

Research/execution contract:
- Binance Spot, long-only, 15m decision candles.
- Ten whitelisted USDT pairs compete only in portfolio mode.
- Fixed 80 USDT stake, maximum three simultaneous positions (240 USDT).
- Single-pair diagnostics start from their own 250 USDT wallet.
- Entry: closed-candle crossover of close above VIDYA+ATR*2.
- Exit: closed-candle crossunder of close below VIDYA-ATR*2.
- VIDYA length 10, momentum length 20, then SMA(15).
- ATR length 200, multiplier 2.0.
- No pair-specific filters, no pyramiding, no ROI profit-taking.
- 1h/4h informative probes are deliberately unused by the signal logic; they
  force the locked backtest audit to verify all four downloaded datasets
  (1m/15m/1h/4h) on this clean-reset branch.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame, Series


def _pine_vidya(source: Series, length: int, momentum_length: int) -> Series:
    """Causal translation of the Pine VIDYA recursion used by the indicator."""
    source = source.astype(float)
    change = source.diff()
    up = change.where(change > 0.0, 0.0)
    down = (-change).where(change < 0.0, 0.0)
    up_sum = up.rolling(momentum_length, min_periods=momentum_length).sum()
    down_sum = down.rolling(momentum_length, min_periods=momentum_length).sum()
    denominator = up_sum + down_sum
    cmo = ((up_sum - down_sum) / denominator).abs()
    cmo = cmo.where(denominator != 0.0, 0.0)

    alpha = 2.0 / (length + 1.0)
    weight = alpha * cmo

    values = np.full(len(source), np.nan, dtype=float)
    src = source.to_numpy(dtype=float)
    weights = weight.to_numpy(dtype=float)
    for index in range(len(values)):
        previous = values[index - 1] if index else np.nan
        if np.isnan(previous):
            values[index] = src[index]
        elif np.isnan(weights[index]):
            values[index] = np.nan
        else:
            values[index] = weights[index] * src[index] + (1.0 - weights[index]) * previous
    return Series(values, index=source.index, dtype=float)


def _hixton_state(dataframe: DataFrame) -> DataFrame:
    close = dataframe["close"].astype(float)
    raw_vidya = _pine_vidya(close, length=10, momentum_length=20)
    vidya = raw_vidya.rolling(15, min_periods=15).mean()
    atr = Series(ta.ATR(dataframe, timeperiod=200), index=dataframe.index, dtype=float)
    upper = vidya + atr * 2.0
    lower = vidya - atr * 2.0

    cross_up = (close > upper) & (close.shift(1) <= upper.shift(1))
    cross_down = (close < lower) & (close.shift(1) >= lower.shift(1))

    trend = np.zeros(len(dataframe), dtype=bool)
    trend_up = False
    for index in range(len(dataframe)):
        if bool(cross_up.iloc[index]):
            trend_up = True
        if bool(cross_down.iloc[index]):
            trend_up = False
        trend[index] = trend_up

    trend_series = Series(trend, index=dataframe.index, dtype=bool)
    prior_trend = trend_series.shift(1, fill_value=False)

    dataframe["hixton_vidya"] = vidya
    dataframe["hixton_atr"] = atr
    dataframe["hixton_upper"] = upper
    dataframe["hixton_lower"] = lower
    dataframe["hixton_trend_up"] = trend_series
    dataframe["hixton_flip_up"] = trend_series & ~prior_trend
    dataframe["hixton_flip_down"] = ~trend_series & prior_trend
    return dataframe


class CompressionBreakout250(IStrategy):
    """Exact-parameter Hixton baseline, isolated from V12.33 strategy logic."""

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "HIXTON-V1"

    can_short = False
    timeframe = "15m"
    process_only_new_candles = True
    startup_candle_count = 400

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    minimal_roi: ClassVar[dict[str, float]] = {}
    stoploss = -0.99
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        dataframe["hixton_data_probe"] = dataframe["close"]
        return dataframe

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        dataframe["hixton_data_probe"] = dataframe["close"]
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        return _hixton_state(dataframe)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        dataframe.loc[
            (dataframe["volume"] > 0.0) & dataframe["hixton_flip_up"],
            ["enter_long", "enter_tag"],
        ] = (1, "hixton_flip_up")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        dataframe.loc[
            (dataframe["volume"] > 0.0) & dataframe["hixton_flip_down"],
            ["exit_long", "exit_tag"],
        ] = (1, "hixton_flip_down")
        return dataframe

    def bot_start(self, **kwargs: Any) -> None:
        del kwargs
        if not bool(self.config.get("dry_run", True)):
            raise RuntimeError("HIXTON-V1 is research/dry-run only; real-money startup is blocked.")
