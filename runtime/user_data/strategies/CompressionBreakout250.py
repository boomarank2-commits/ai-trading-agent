"""HIXTON-V4: pair-aware profit-floor refinement of the supplied Pine indicator.

V4 keeps the purchased Hixton motor unchanged:
- VIDYA length 10 / momentum 20, then Pine-compatible SMA 15
- ATR 200 x 2 bands
- original closed-candle 15m flip-up entry event
- original lower-band flip-down exit
- no pyramiding and no ROI target

The complete V3A ten-pair diagnostics showed three distinct behaviours. V4 therefore
makes only two evidence-driven refinements:
1) ETH uses the completed 1h close-above-VIDYA guard without the rising-slope clause,
   because matched V1/V3 evidence showed the slope clause removed 67 ETH entries
   whose original Hixton exits summed to +13.24 USDT.
2) Every pair gets a conservative break-even profit floor after its own rounded
   peak-profit activation threshold. The threshold is based on the V3A loser-MFE
   distribution, not on a grid search. Once activated, the stop can only tighten
   to the open-price break-even level; it never trails the trend further.

This is a preregistered research candidate, not a claim of profitability.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, ClassVar

import numpy as np
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative, stoploss_from_open
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


class CompressionBreakout250(IStrategy):
    """Hixton V4: original trend exit plus pair-aware break-even protection."""

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "HIXTON-V4"

    can_short = False
    timeframe = "15m"
    process_only_new_candles = True
    startup_candle_count = 400

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    minimal_roi: ClassVar[dict[str, float]] = {}
    stoploss = -0.99
    trailing_stop = False
    use_custom_stoploss = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Net current-profit activation thresholds. These are rounded from the
    # V3A loser peak-profit distribution and intentionally not grid-optimized.
    PROFIT_FLOOR_TRIGGER: ClassVar[dict[str, float]] = {
        "BTC/USDT": 0.0050,
        "ETH/USDT": 0.0100,
        "SOL/USDT": 0.0150,
        "XRP/USDT": 0.0100,
        "BNB/USDT": 0.0060,
        "DOGE/USDT": 0.0150,
        "LINK/USDT": 0.0150,
        "TRX/USDT": 0.0050,
        "LTC/USDT": 0.0100,
        "BCH/USDT": 0.0125,
    }
    PROFIT_FLOOR = 0.0

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
        dataframe["hixton_data_probe"] = dataframe["close"]
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

        if pair == "ETH/USDT":
            guard = one_hour_bullish
            enter_tag = "hixton_flip_up_1h_bullish"
        else:
            guard = one_hour_bullish & one_hour_rising
            enter_tag = "hixton_flip_up_1h_rising"

        dataframe.loc[
            (dataframe["volume"] > 0.0)
            & dataframe["hixton_flip_up"]
            & guard,
            ["enter_long", "enter_tag"],
        ] = (1, enter_tag)
        return dataframe

    def populate_exit_trend(
        self, dataframe: DataFrame, metadata: dict[str, Any]
    ) -> DataFrame:
        del metadata
        dataframe.loc[
            (dataframe["volume"] > 0.0) & dataframe["hixton_flip_down"],
            ["exit_long", "exit_tag"],
        ] = (1, "hixton_flip_down")
        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs: Any,
    ) -> float | None:
        del current_time, current_rate, after_fill, kwargs
        trigger = self.PROFIT_FLOOR_TRIGGER.get(pair)
        if trigger is None or current_profit < trigger:
            return None

        # Once the pair-specific profit threshold has been reached, the stop
        # may only tighten to break-even relative to the original open price.
        # Freqtrade never moves a custom stoploss downward again.
        return stoploss_from_open(
            self.PROFIT_FLOOR,
            current_profit,
            is_short=trade.is_short,
            leverage=trade.leverage,
        ) or 1

    def bot_start(self, **kwargs: Any) -> None:
        del kwargs
        if not bool(self.config.get("dry_run", True)):
            raise RuntimeError(
                "HIXTON-V4 is research/dry-run only; real-money startup is blocked."
            )
