"""V12.40 research candidate: combine two fixed SOL trend families."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from CompressionBreakout250 import CompressionBreakout250, _supertrend_direction
from freqtrade.persistence import Trade
from freqtrade.strategy import informative
from pandas import DataFrame


class CompressionBreakout250V1240(CompressionBreakout250):
    """V12.33 plus the fixed V12.37 SOL Supertrend reserve."""

    STRATEGY_VERSION = "V12.40"

    @informative("4h")
    def populate_indicators_4h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        dataframe = super().populate_indicators_4h(dataframe, metadata)
        dataframe["sol_supertrend_direction"] = _supertrend_direction(
            dataframe, period=14, multiplier=3.5
        )
        dataframe["sol_supertrend_long_flip"] = (
            (dataframe["sol_supertrend_direction"] > 0)
            & (dataframe["sol_supertrend_direction"].shift(1).fillna(0) <= 0)
        ).astype(int)
        dataframe["sol_supertrend_short_flip"] = (
            (dataframe["sol_supertrend_direction"] < 0)
            & (dataframe["sol_supertrend_direction"].shift(1).fillna(0) >= 0)
        ).astype(int)
        dataframe["sol_ema200_rising_6"] = (
            dataframe["ema_slow"] > dataframe["ema_slow"].shift(6)
        ).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if pair != "SOL/USDT":
            return dataframe

        active_sol_signal = dataframe["enter_long"].fillna(0) > 0
        reserve_state = (
            (dataframe["sol_supertrend_long_flip_4h"] > 0)
            & (dataframe["close_4h"] > dataframe["ema_slow_4h"])
            & (dataframe["sol_ema200_rising_6_4h"] > 0)
            & (dataframe["adx_4h"] >= 20)
            & (dataframe["momentum_30d_4h"] >= 0.05)
        )
        reserve_start = reserve_state & ~reserve_state.shift(1).fillna(False)
        first_hour = (
            reserve_start.rolling(4, min_periods=1).max().fillna(False).astype(bool)
        )
        execution_ready = (
            first_hour
            & (dataframe["close"] > dataframe["ema_exec"])
            & (dataframe["rsi"] >= 50)
            & (dataframe["rsi"] <= 72)
            & (dataframe["volume"] > 0)
        )
        seen_execution = (
            execution_ready.shift(1)
            .rolling(4, min_periods=1)
            .max()
            .fillna(False)
            .astype(bool)
        )
        reserve_signal = execution_ready & ~seen_execution & ~active_sol_signal
        dataframe.loc[first_hour, "regime_state"] = self.REGIME_TREND
        dataframe.loc[first_hour, "no_trade_reason"] = "wait_sol_supertrend_execution"
        dataframe.loc[reserve_signal, "route_family"] = "SOL_SUPERTREND_RESERVE"
        dataframe.loc[reserve_signal, "no_trade_reason"] = ""
        dataframe.loc[reserve_signal, ["enter_long", "enter_tag"]] = (
            1,
            "v12_40_sol_donchian_plus_supertrend14x3_5",
        )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))
        dataframe = super().populate_exit_trend(dataframe, metadata)
        if pair == "SOL/USDT":
            # SOL has two entry families in this candidate. Their exits are
            # routed by enter_tag in custom_exit so one family's exit cannot
            # accidentally close the other family's trade.
            dataframe["exit_long"] = 0
            dataframe["exit_tag"] = None
        return dataframe

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> str | None:
        enter_tag = str(getattr(trade, "enter_tag", "") or "")
        if pair != "SOL/USDT" or self.dp is None:
            return super().custom_exit(
                pair,
                trade,
                current_time,
                current_rate,
                current_profit,
                **kwargs,
            )
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if not dataframe.empty:
                candle = dataframe.iloc[-1].squeeze()
                if "_donchian_plus_supertrend14x3_5" in enter_tag:
                    if float(candle.get("sol_supertrend_short_flip_4h", 0.0)) > 0:
                        return "v12_40_sol_supertrend_short_flip"
                    return None
                structure_exit = float(candle.get("close_4h", 0.0)) < float(
                    candle.get("donchian_exit_4h", 0.0)
                )
                regime_exit = (
                    float(candle.get("close_4h", 0.0))
                    < float(candle.get("ema_fast_4h", 0.0))
                    and float(candle.get("momentum_30d_4h", 0.0)) < 0.0
                )
                if structure_exit or regime_exit:
                    return "v12_17_slow_trend_exit"
        except (KeyError, TypeError, ValueError):
            pass
        return super().custom_exit(
            pair,
            trade,
            current_time,
            current_rate,
            current_profit,
            **kwargs,
        )
