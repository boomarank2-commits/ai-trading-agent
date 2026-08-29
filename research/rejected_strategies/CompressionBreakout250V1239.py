"""V12.39 research candidate: replace only XRP with fixed 7-day momentum."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from CompressionBreakout250 import CompressionBreakout250
from freqtrade.persistence import Trade
from freqtrade.strategy import informative
from pandas import DataFrame


class CompressionBreakout250V1239(CompressionBreakout250):
    """V12.33 plus the preregistered XRP 7-day momentum reserve."""

    STRATEGY_VERSION = "V12.39"

    @informative("4h")
    def populate_indicators_4h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        dataframe = super().populate_indicators_4h(dataframe, metadata)
        dataframe["xrp_momentum_7d"] = (
            dataframe["close"] / dataframe["close"].shift(42) - 1.0
        )
        dataframe["xrp_momentum_cross"] = (
            (dataframe["xrp_momentum_7d"] > 0.05)
            & (dataframe["xrp_momentum_7d"].shift(1) <= 0.05)
        ).astype(int)
        dataframe["xrp_ema100_rising_6"] = (
            dataframe["ema_macro100"] > dataframe["ema_macro100"].shift(6)
        ).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if pair != "XRP/USDT":
            return dataframe

        dataframe["enter_long"] = 0
        dataframe["enter_tag"] = None
        dataframe["regime_state"] = self.REGIME_NO_TRADE
        dataframe["route_family"] = self.FAMILY_NO_TRADE
        dataframe["no_trade_reason"] = "v12_39_xrp_wait_7d_momentum"

        route_ready = (
            (dataframe["xrp_momentum_cross_4h"] > 0)
            & (dataframe["close_4h"] > dataframe["ema_macro100_4h"])
            & (dataframe["xrp_ema100_rising_6_4h"] > 0)
            & (dataframe["adx_4h"] >= 18)
        )
        execution_ready = (
            route_ready
            & (dataframe["close"] > dataframe["ema_exec"])
            & (dataframe["rsi"] <= 75)
            & (dataframe["volume"] > 0)
        )
        first_execution = execution_ready & ~execution_ready.shift(1).fillna(False)
        dataframe.loc[route_ready, "regime_state"] = self.REGIME_TREND
        dataframe.loc[route_ready, "no_trade_reason"] = "wait_execution_gate"
        dataframe.loc[first_execution, "route_family"] = "XRP_7D_MOMENTUM"
        dataframe.loc[first_execution, "no_trade_reason"] = ""
        dataframe.loc[first_execution, ["enter_long", "enter_tag"]] = (
            1,
            "v12_39_xrp_7d_momentum",
        )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))
        if pair != "XRP/USDT":
            return super().populate_exit_trend(dataframe, metadata)
        xrp_exit = (
            (dataframe["xrp_momentum_7d_4h"] <= 0)
            | (dataframe["close_4h"] < dataframe["ema_macro100_4h"])
        )
        dataframe.loc[
            xrp_exit & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "v12_39_xrp_7d_momentum_exit")
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
        if pair == "XRP/USDT" and "v12_39_xrp_7d_momentum" in enter_tag:
            return None
        return super().custom_exit(
            pair,
            trade,
            current_time,
            current_rate,
            current_profit,
            **kwargs,
        )
