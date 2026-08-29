"""HIXTON-V5: pair-route refinement after the complete V3A/V4 trade analysis.

V4 is rejected: its fee-covering profit floor saved some losers, but cut many of
the large trend winners that pay for Hixton. V5 therefore removes the custom
stop completely and restores the original lower-band Hixton exit.

Routes are preregistered from the observed V3A failure modes:
- ETH, SOL, XRP, DOGE, LINK and TRX are controls and keep the exact V3A route:
  15m flip-up + completed 1h close above a non-falling 1h VIDYA; 15m flip-down.
- BTC and BNB had positive gross price edge but insufficient edge after fees.
  They keep the V3A route and additionally require completed 4h close above a
  non-falling 4h Hixton VIDYA to reduce weak/noisy 15m entries.
- LTC and BCH had negative gross price edge already before fees on the 15m route.
  They therefore use native completed 1h Hixton flip events, guarded by a
  completed bullish/non-falling 4h Hixton VIDYA regime, and exit on the native
  completed 1h Hixton flip-down.

The purchased Hixton motor itself remains unchanged on every timeframe:
VIDYA 10 / momentum 20 -> Pine-compatible SMA 15, ATR 200 x 2 bands.
No pyramiding, no ROI target and no custom/trailing profit stop.

This is a preregistered research candidate, not a claim of profitability.
"""

from __future__ import annotations

from collections import deque
from typing import Any, ClassVar

import numpy as np
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame, Series


def _pine_vidya(source: Series, length: int, momentum_length: int) -> Series:
    """Translate the Pine VIDYA recursion used by the supplied indicator."""
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
            values[index] = (
                weights[index] * src[index]
                + (1.0 - weights[index]) * previous
            )
    return Series(values, index=source.index, dtype=float)


def _pine_sma_ignore_na(source: Series, length: int) -> Series:
    """Pine ta.sma-compatible SMA: length most recent non-na source values."""
    output = np.full(len(source), np.nan, dtype=float)
    window: deque[float] = deque(maxlen=length)
    for index, value in enumerate(source.to_numpy(dtype=float)):
        if not np.isnan(value):
            window.append(float(value))
        if len(window) == length:
            output[index] = sum(window) / length
    return Series(output, index=source.index, dtype=float)


def _pine_rma(source: Series, length: int) -> Series:
    """Pine ta.rma-compatible Wilder moving average."""
    output = np.full(len(source), np.nan, dtype=float)
    seed: deque[float] = deque(maxlen=length)
    previous = np.nan
    alpha = 1.0 / length
    for index, value in enumerate(source.to_numpy(dtype=float)):
        if np.isnan(value):
            continue
        if np.isnan(previous):
            seed.append(float(value))
            if len(seed) == length:
                previous = sum(seed) / length
                output[index] = previous
        else:
            previous = alpha * float(value) + (1.0 - alpha) * previous
            output[index] = previous
    return Series(output, index=source.index, dtype=float)


def _pine_atr(dataframe: DataFrame, length: int) -> Series:
    """Pine ta.atr(length) = ta.rma(ta.tr(true), length)."""
    high = dataframe["high"].astype(float)
    low = dataframe["low"].astype(float)
    close = dataframe["close"].astype(float)
    previous_close = close.shift(1)
    high_low = high - low
    high_previous = (high - previous_close).abs()
    low_previous = (low - previous_close).abs()
    true_range = DataFrame(
        {
            "high_low": high_low,
            "high_previous": high_previous,
            "low_previous": low_previous,
        }
    ).max(axis=1, skipna=True)
    return _pine_rma(true_range, length)


def _hixton_state(dataframe: DataFrame) -> DataFrame:
    close = dataframe["close"].astype(float)
    raw_vidya = _pine_vidya(close, length=10, momentum_length=20)
    vidya = _pine_sma_ignore_na(raw_vidya, length=15)
    atr = _pine_atr(dataframe, length=200)
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


def _first_forward_filled_true(series: Series) -> Series:
    """Turn a forward-filled informative boolean into one 15m event only."""
    values = series.fillna(False).astype(bool)
    return values & ~values.shift(1, fill_value=False)


class CompressionBreakout250(IStrategy):
    """Hixton V5: V3A controls plus targeted higher-timeframe weak-pair routes."""

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "HIXTON-V5"

    can_short = False
    timeframe = "15m"
    process_only_new_candles = True
    startup_candle_count = 400

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    minimal_roi: ClassVar[dict[str, float]] = {}
    stoploss = -0.99
    trailing_stop = False
    use_custom_stoploss = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    V3A_CONTROL_PAIRS: ClassVar[frozenset[str]] = frozenset(
        {"ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "LINK/USDT", "TRX/USDT"}
    )
    FOUR_HOUR_GUARD_PAIRS: ClassVar[frozenset[str]] = frozenset(
        {"BTC/USDT", "BNB/USDT"}
    )
    ONE_HOUR_ROUTE_PAIRS: ClassVar[frozenset[str]] = frozenset(
        {"LTC/USDT", "BCH/USDT"}
    )

    @informative("1h")
    def populate_indicators_1h(
        self, dataframe: DataFrame, metadata: dict[str, Any]
    ) -> DataFrame:
        del metadata
        dataframe = _hixton_state(dataframe)
        dataframe["hixton_vidya_rising"] = (
            dataframe["hixton_vidya"] >= dataframe["hixton_vidya"].shift(1)
        )
        return dataframe

    @informative("4h")
    def populate_indicators_4h(
        self, dataframe: DataFrame, metadata: dict[str, Any]
    ) -> DataFrame:
        del metadata
        dataframe = _hixton_state(dataframe)
        dataframe["hixton_vidya_rising"] = (
            dataframe["hixton_vidya"] >= dataframe["hixton_vidya"].shift(1)
        )
        return dataframe

    def populate_indicators(
        self, dataframe: DataFrame, metadata: dict[str, Any]
    ) -> DataFrame:
        del metadata
        return _hixton_state(dataframe)

    def populate_entry_trend(
        self, dataframe: DataFrame, metadata: dict[str, Any]
    ) -> DataFrame:
        pair = str(metadata.get("pair") or "")
        one_hour_bullish = dataframe["close_1h"] > dataframe["hixton_vidya_1h"]
        one_hour_rising = dataframe["hixton_vidya_rising_1h"].fillna(False)
        four_hour_bullish = dataframe["close_4h"] > dataframe["hixton_vidya_4h"]
        four_hour_rising = dataframe["hixton_vidya_rising_4h"].fillna(False)
        four_hour_guard = four_hour_bullish & four_hour_rising

        if pair in self.ONE_HOUR_ROUTE_PAIRS:
            one_hour_flip_up_event = _first_forward_filled_true(
                dataframe["hixton_flip_up_1h"]
            )
            entry = one_hour_flip_up_event & four_hour_guard
            enter_tag = "hixton_1h_flip_up_4h_guard"
        else:
            entry = dataframe["hixton_flip_up"] & one_hour_bullish & one_hour_rising
            enter_tag = "hixton_15m_flip_up_1h_guard"
            if pair in self.FOUR_HOUR_GUARD_PAIRS:
                entry = entry & four_hour_guard
                enter_tag = "hixton_15m_flip_up_1h_4h_guard"

        dataframe.loc[
            (dataframe["volume"] > 0.0) & entry,
            ["enter_long", "enter_tag"],
        ] = (1, enter_tag)
        return dataframe

    def populate_exit_trend(
        self, dataframe: DataFrame, metadata: dict[str, Any]
    ) -> DataFrame:
        pair = str(metadata.get("pair") or "")
        if pair in self.ONE_HOUR_ROUTE_PAIRS:
            exit_signal = _first_forward_filled_true(dataframe["hixton_flip_down_1h"])
            exit_tag = "hixton_1h_flip_down"
        else:
            exit_signal = dataframe["hixton_flip_down"]
            exit_tag = "hixton_15m_flip_down"

        dataframe.loc[
            (dataframe["volume"] > 0.0) & exit_signal,
            ["exit_long", "exit_tag"],
        ] = (1, exit_tag)
        return dataframe

    def bot_start(self, **kwargs: Any) -> None:
        del kwargs
        if not bool(self.config.get("dry_run", True)):
            raise RuntimeError(
                "HIXTON-V5 is research/dry-run only; real-money startup is blocked."
            )
