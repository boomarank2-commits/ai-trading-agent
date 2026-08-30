"""HIXTON-V1-DIAG: V1 trading logic with measurement-only diagnostics.

This experiment deliberately keeps the V1 trading decisions unchanged:
- Binance Spot, long-only, 15m decision candles.
- Entry only on the original closed-candle Hixton flip from red to green.
- Exit only on the original closed-candle Hixton flip from green to red.
- VIDYA 10 / momentum 20 / SMA15 / ATR200 x2.
- No 1h/4h entry guards, no take-profit, no ROI, no trailing, no pyramiding.

The additional columns are measurement features only. They exist so an exported
Freqtrade `signals` dataset can answer why each V1 trade succeeded or failed
without changing which trades are taken.
"""

from __future__ import annotations

from collections import deque
from typing import Any, ClassVar

import numpy as np
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame, Series


def _pine_vidya(source: Series, length: int, momentum_length: int) -> Series:
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


def _pine_sma_ignore_na(source: Series, length: int) -> Series:
    output = np.full(len(source), np.nan, dtype=float)
    window: deque[float] = deque(maxlen=length)
    for index, value in enumerate(source.to_numpy(dtype=float)):
        if not np.isnan(value):
            window.append(float(value))
        if len(window) == length:
            output[index] = sum(window) / length
    return Series(output, index=source.index, dtype=float)


def _pine_rma(source: Series, length: int) -> Series:
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


def _true_range(dataframe: DataFrame) -> Series:
    high = dataframe["high"].astype(float)
    low = dataframe["low"].astype(float)
    close = dataframe["close"].astype(float)
    previous_close = close.shift(1)
    return DataFrame({
        "hl": high - low,
        "hc": (high - previous_close).abs(),
        "lc": (low - previous_close).abs(),
    }).max(axis=1, skipna=True)


def _pine_atr(dataframe: DataFrame, length: int) -> Series:
    return _pine_rma(_true_range(dataframe), length)


def _ema(source: Series, length: int) -> Series:
    return source.astype(float).ewm(span=length, adjust=False, min_periods=length).mean()


def _rsi(source: Series, length: int = 14) -> Series:
    change = source.astype(float).diff()
    gain = change.where(change > 0.0, 0.0)
    loss = (-change).where(change < 0.0, 0.0)
    avg_gain = _pine_rma(gain, length)
    avg_loss = _pine_rma(loss, length)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    rsi = rsi.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)
    return rsi


def _adx(dataframe: DataFrame, length: int = 14) -> Series:
    high = dataframe["high"].astype(float)
    low = dataframe["low"].astype(float)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)
    atr = _pine_rma(_true_range(dataframe), length)
    plus_di = 100.0 * _pine_rma(plus_dm, length) / atr.replace(0.0, np.nan)
    minus_di = 100.0 * _pine_rma(minus_dm, length) / atr.replace(0.0, np.nan)
    denominator = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / denominator
    return _pine_rma(dx, length)


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


def _phase_diagnostics(dataframe: DataFrame) -> DataFrame:
    size = len(dataframe)
    trend = dataframe["hixton_trend_up"].fillna(False).to_numpy(dtype=bool)
    flip_up = dataframe["hixton_flip_up"].fillna(False).to_numpy(dtype=bool)
    flip_down = dataframe["hixton_flip_down"].fillna(False).to_numpy(dtype=bool)
    highs = dataframe["high"].astype(float).to_numpy()
    lows = dataframe["low"].astype(float).to_numpy()
    closes = dataframe["close"].astype(float).to_numpy()
    atrs = dataframe["hixton_atr"].astype(float).to_numpy()
    previous_phase_bars = np.full(size, np.nan, dtype=float)
    previous_phase_range_atr = np.full(size, np.nan, dtype=float)
    previous_phase_net_atr = np.full(size, np.nan, dtype=float)
    red_rebound_atr = np.full(size, np.nan, dtype=float)
    previous_green_range_atr = np.full(size, np.nan, dtype=float)
    phase_kind = False
    phase_bars = 0
    phase_high = np.nan
    phase_low = np.nan
    phase_start_close = np.nan
    last_green_raw_range = np.nan

    def start_phase(kind: bool, i: int) -> None:
        nonlocal phase_kind, phase_bars, phase_high, phase_low, phase_start_close
        phase_kind = kind
        phase_bars = 1
        phase_high = highs[i]
        phase_low = lows[i]
        phase_start_close = closes[i]

    for i in range(size):
        if i == 0:
            start_phase(bool(trend[i]), i)
            continue
        if bool(flip_up[i]) or bool(flip_down[i]):
            atr = atrs[i]
            if phase_bars > 0 and not np.isnan(atr) and atr > 0.0:
                previous_phase_bars[i] = float(phase_bars)
                previous_phase_range_atr[i] = (phase_high - phase_low) / atr
                previous_phase_net_atr[i] = (closes[i - 1] - phase_start_close) / atr
                if bool(flip_up[i]):
                    red_rebound_atr[i] = (closes[i] - phase_low) / atr
                    if not np.isnan(last_green_raw_range):
                        previous_green_range_atr[i] = last_green_raw_range / atr
                else:
                    last_green_raw_range = phase_high - phase_low
            start_phase(bool(trend[i]), i)
        else:
            if bool(trend[i]) != phase_kind:
                start_phase(bool(trend[i]), i)
            else:
                phase_bars += 1
                phase_high = max(phase_high, highs[i])
                phase_low = min(phase_low, lows[i])

    dataframe["diag_prev_phase_bars"] = previous_phase_bars
    dataframe["diag_prev_phase_range_atr"] = previous_phase_range_atr
    dataframe["diag_prev_phase_net_atr"] = previous_phase_net_atr
    dataframe["diag_red_rebound_atr"] = red_rebound_atr
    dataframe["diag_prev_green_range_atr"] = previous_green_range_atr
    for column in (
        "diag_prev_phase_bars",
        "diag_prev_phase_range_atr",
        "diag_prev_phase_net_atr",
        "diag_red_rebound_atr",
        "diag_prev_green_range_atr",
    ):
        dataframe[column] = dataframe[column].ffill()
    return dataframe


def _diagnostic_state(dataframe: DataFrame) -> DataFrame:
    dataframe = _hixton_state(dataframe)
    close = dataframe["close"].astype(float)
    open_ = dataframe["open"].astype(float)
    high = dataframe["high"].astype(float)
    low = dataframe["low"].astype(float)
    volume = dataframe["volume"].astype(float)
    vidya = dataframe["hixton_vidya"].astype(float)
    atr = dataframe["hixton_atr"].astype(float)
    upper = dataframe["hixton_upper"].astype(float)
    safe_atr = atr.replace(0.0, np.nan)
    safe_close = close.replace(0.0, np.nan)
    dataframe["diag_price_minus_vidya_atr"] = (close - vidya) / safe_atr
    dataframe["diag_breakout_excess_atr"] = (close - upper) / safe_atr
    dataframe["diag_candle_body_atr"] = (close - open_) / safe_atr
    dataframe["diag_candle_range_atr"] = (high - low) / safe_atr
    dataframe["diag_atr_pct"] = 100.0 * atr / safe_close
    dataframe["diag_atr_vs_median_96"] = atr / atr.rolling(96, min_periods=48).median().replace(0.0, np.nan)
    dataframe["diag_vidya_slope_1_atr"] = (vidya - vidya.shift(1)) / safe_atr
    dataframe["diag_vidya_slope_4_atr"] = (vidya - vidya.shift(4)) / safe_atr
    dataframe["diag_vidya_slope_16_atr"] = (vidya - vidya.shift(16)) / safe_atr
    dataframe["diag_volume_ratio_20"] = volume / volume.rolling(20, min_periods=10).mean().replace(0.0, np.nan)
    dataframe["diag_volume_ratio_96"] = volume / volume.rolling(96, min_periods=48).mean().replace(0.0, np.nan)
    dataframe["diag_rsi14"] = _rsi(close, 14)
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd = ema12 - ema26
    macd_signal = _ema(macd, 9)
    macd_hist = macd - macd_signal
    dataframe["diag_macd_hist"] = macd_hist
    dataframe["diag_macd_hist_atr"] = macd_hist / safe_atr
    dataframe["diag_adx14"] = _adx(dataframe, 14)
    return _phase_diagnostics(dataframe)


class CompressionBreakout250(IStrategy):
    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "HIXTON-V1-DIAG"
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
    use_custom_stoploss = False

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        return _diagnostic_state(dataframe)

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        return _diagnostic_state(dataframe)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        return _diagnostic_state(dataframe)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        dataframe.loc[
            (dataframe["volume"] > 0.0) & dataframe["hixton_flip_up"],
            ["enter_long", "enter_tag"],
        ] = (1, "hixton_v1_flip_up")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        del metadata
        dataframe.loc[
            (dataframe["volume"] > 0.0) & dataframe["hixton_flip_down"],
            ["exit_long", "exit_tag"],
        ] = (1, "hixton_v1_flip_down")
        return dataframe

    def bot_start(self, **kwargs: Any) -> None:
        del kwargs
        if not bool(self.config.get("dry_run", True)):
            raise RuntimeError("HIXTON-V1-DIAG is research/dry-run only; real-money startup is blocked.")
