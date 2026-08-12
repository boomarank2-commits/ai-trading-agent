"""Long-only, slow-regime pullback candidate for a 250 USDT Spot account.

Research hypothesis: after costs, buying a confirmed recovery from a shallow
pullback inside a multi-day uptrend is less fragile than buying a fresh
15-minute breakout.  Signals use only the candle being closed and older data;
Freqtrade executes them on the following candle in backtests.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from pandas import DataFrame


class TrendPullback250V1(IStrategy):
    """Slow uptrend regime with a confirmed EMA pullback recovery."""

    INTERFACE_VERSION = 3

    can_short = False
    timeframe = "15m"
    process_only_new_candles = True
    startup_candle_count = 800

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    MAX_STAKE_USDT = 80.0
    MAX_TOTAL_CAPITAL_USDT = 250.0
    MAX_TOTAL_EXPOSURE_USDT = 240.0
    MAX_DAILY_LOSS_USDT = 10.0

    # These match the locked runtime config.  Keeping them here makes the
    # candidate self-describing when evaluated without that config.
    minimal_roi: ClassVar[dict[str, float]] = {
        "0": 0.05,
        "120": 0.025,
        "360": 0.0,
    }
    stoploss = -0.055
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types: ClassVar[dict[str, Any]] = {
        "entry": "limit",
        "exit": "limit",
        "force_entry": "market",
        "force_exit": "market",
        "emergency_exit": "market",
        "stoploss": "limit",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_interval": 60,
        "stoploss_on_exchange_limit_ratio": 0.99,
    }
    order_time_in_force: ClassVar[dict[str, str]] = {"entry": "GTC", "exit": "GTC"}

    @staticmethod
    def _runmode_value(config: dict[str, Any]) -> str:
        runmode = config.get("runmode", "")
        return str(getattr(runmode, "value", runmode)).lower()

    def _runtime_entry_guards_enabled(self) -> bool:
        return self._runmode_value(self.config) in {"live", "dry_run"}

    @property
    def protections(self) -> list[dict[str, Any]]:
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 4},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 96,
                "trade_limit": 2,
                "stop_duration_candles": 24,
                "only_per_pair": False,
                "only_per_side": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 192,
                "trade_limit": 3,
                "stop_duration_candles": 48,
                "max_allowed_drawdown": 0.08,
                "calculation_mode": "equity",
                "only_per_pair": False,
            },
        ]

    def _kill_switch_path(self) -> Path:
        configured_path = os.getenv("AI_TRADING_KILL_SWITCH_FILE")
        if configured_path:
            return Path(configured_path).expanduser()
        user_data_dir = Path(str(self.config.get("user_data_dir", "user_data")))
        return user_data_dir / "STOP_ENTRIES"

    @staticmethod
    def _closed_profit_since(day_start_utc: datetime) -> float:
        closed_today = Trade.get_trades_proxy(is_open=False, close_date=day_start_utc)
        return sum(float(trade.close_profit_abs or 0.0) for trade in closed_today)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata

        dataframe["ema_recovery"] = ta.EMA(dataframe, timeperiod=48)
        dataframe["ema_regime_fast"] = ta.EMA(dataframe, timeperiod=96)
        dataframe["ema_regime_slow"] = ta.EMA(dataframe, timeperiod=384)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["volume_mean"] = (
            dataframe["volume"].shift(1).rolling(48, min_periods=48).mean()
        )
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_mean"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata

        slow_uptrend = (
            (dataframe["close"] > dataframe["ema_regime_slow"])
            & (dataframe["ema_recovery"] > dataframe["ema_regime_fast"])
            & (dataframe["ema_regime_fast"] > dataframe["ema_regime_slow"])
            & (
                dataframe["ema_regime_fast"]
                > dataframe["ema_regime_fast"].shift(24)
            )
            & (
                dataframe["ema_regime_slow"]
                > dataframe["ema_regime_slow"].shift(96)
            )
        )
        recovery_cross = (
            (dataframe["close"] > dataframe["ema_recovery"])
            & (dataframe["close"].shift(1) <= dataframe["ema_recovery"].shift(1))
        )
        momentum_recovered = (
            (dataframe["rsi"] >= 50.0)
            & (dataframe["rsi"].shift(1) < 50.0)
            & (dataframe["rsi"] <= 60.0)
        )

        dataframe.loc[
            (
                slow_uptrend
                & recovery_cross
                & momentum_recovered
                & (dataframe["atr_pct"] >= 0.0025)
                & (dataframe["atr_pct"] <= 0.035)
                & (dataframe["volume_ratio"] >= 1.00)
                & (dataframe["close"] > dataframe["open"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "slow_trend_pullback_recovery")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata

        regime_failure = (
            (dataframe["close"] < dataframe["ema_regime_fast"])
            & (
                dataframe["close"].shift(1)
                >= dataframe["ema_regime_fast"].shift(1)
            )
        )
        dataframe.loc[
            (
                regime_failure
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "slow_regime_failure")

        return dataframe

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> float:
        del pair, current_time, current_rate, leverage, entry_tag, kwargs
        if side != "long":
            return 0.0
        capped_stake = min(float(proposed_stake), float(max_stake), self.MAX_STAKE_USDT)
        if min_stake is not None and capped_stake < float(min_stake):
            return 0.0
        return max(0.0, capped_stake)

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> float:
        del (
            pair,
            current_time,
            current_rate,
            proposed_leverage,
            max_leverage,
            entry_tag,
            side,
            kwargs,
        )
        return 1.0

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> bool:
        del pair, order_type, time_in_force, entry_tag, kwargs
        if side != "long":
            return False
        if not self._runtime_entry_guards_enabled():
            return True
        if self._kill_switch_path().is_file():
            return False

        now_utc = current_time.astimezone(UTC)
        day_start_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        if self._closed_profit_since(day_start_utc) <= -self.MAX_DAILY_LOSS_USDT:
            return False

        requested_stake = max(0.0, float(amount) * float(rate))
        configured_cap = min(
            float(self.config.get("available_capital", self.MAX_TOTAL_CAPITAL_USDT)),
            self.MAX_TOTAL_CAPITAL_USDT,
            self.MAX_TOTAL_EXPOSURE_USDT,
        )
        open_stake = float(Trade.total_open_trades_stakes())
        return (open_stake + requested_stake) <= (configured_cap + 1e-6)
