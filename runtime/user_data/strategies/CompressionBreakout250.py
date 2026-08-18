"""V12.4 pair-local slow Donchian candidate for the 250 USDT testbot.

This candidate deliberately removes the three V11 entry families that failed the
three-year local BTC/ETH/SOL backtests (ORB-Retest, Ichimoku and Bollinger MR).
Each pair is evaluated independently. A trade is allowed only on a fresh
20-day high of closed 4h candles inside an established 4h/1h uptrend.
Otherwise the correct action is NO_TRADE.

Safety remains Binance Spot, long-only, 1x, max 80 USDT per position,
max three positions / 240 USDT total exposure and a -5.5% hard stop.
"""

from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame


class CompressionBreakout250(IStrategy):
    """V12.4: pair-local 20-day 4h Donchian trend candidate."""

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "V12.4"

    can_short = False
    timeframe = "15m"
    process_only_new_candles = True
    startup_candle_count = 400

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    MAX_STAKE_USDT = 80.0
    MAX_TOTAL_CAPITAL_USDT = 250.0
    MAX_TOTAL_EXPOSURE_USDT = 240.0
    MAX_OPEN_POSITIONS = 3
    MAX_DAILY_LOSS_USDT_PER_PAIR = 10.0

    ALLOWED_PAIRS = {"BTC/USDT", "ETH/USDT", "SOL/USDT"}

    BUY_MOMENTUM_30D = 0.03
    BUY_ADX_4H_MIN = 16.0
    BUY_RSI_4H_MAX = 78.0
    BUY_ATR_MIN = 0.003
    BUY_ATR_MAX = 0.060
    BUY_FAILURE_ATR = 0.50

    REGIME_TREND = "TREND/BREAKOUT"
    REGIME_NO_TRADE = "NO_TRADE"
    FAMILY_DONCHIAN = "DONCHIAN_TREND"
    FAMILY_NO_TRADE = "NO_TRADE"

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

    plot_config: ClassVar[dict[str, Any]] = {
        "main_plot": {"ema_exec": {}, "ema_fast": {}},
        "subplots": {
            "Momentum": {"rsi": {}},
            "Volume": {"volume_ratio": {}},
        },
    }

    @staticmethod
    def _runmode_value(config: dict[str, Any]) -> str:
        runmode = config.get("runmode", "")
        return str(getattr(runmode, "value", runmode)).lower()

    def _runtime_entry_guards_enabled(self) -> bool:
        return self._runmode_value(self.config) in {"live", "dry_run"}

    def bot_start(self, **kwargs: Any) -> None:
        del kwargs
        if not self._runtime_entry_guards_enabled():
            return

        exchange = self.config.get("exchange", {})
        order_types = self.config.get("order_types", {})
        time_in_force = self.config.get("order_time_in_force", {})
        pairs = exchange.get("pair_whitelist", []) if isinstance(exchange, dict) else []

        configured_source = getattr(type(self), "__file__", None)
        if not isinstance(configured_source, str) or not configured_source:
            raise RuntimeError("Freqtrade did not expose the resolved strategy source")
        strategy_source = Path(configured_source).resolve(strict=True)
        adjacent_parameters = strategy_source.with_suffix(".json")

        stake_amount = float(self.config.get("stake_amount", 0.0))
        available_capital = float(self.config.get("available_capital", 0.0))
        max_open_trades = int(self.config.get("max_open_trades", -1))

        api_server = self.config.get("api_server", {})
        api_server_safe = False
        if isinstance(api_server, dict):
            api_server_safe = api_server.get("enabled") is False
            if self._runmode_value(self.config) == "dry_run":
                api_server_safe = api_server_safe or (
                    api_server.get("enabled") is True
                    and api_server.get("listen_ip_address") == "127.0.0.1"
                    and api_server.get("listen_port") == 8080
                    and api_server.get("enable_openapi") is False
                    and api_server.get("CORS_origins") == []
                )

        invariants_hold = (
            self.can_short is False
            and self.position_adjustment_enable is False
            and self.max_entry_position_adjustment == 0
            and self.timeframe == "15m"
            and self.config.get("strategy") == type(self).__name__
            and self.config.get("timeframe") == "15m"
            and str(self.config.get("trading_mode", "")).lower() == "spot"
            and not str(self.config.get("margin_mode", ""))
            and str(self.config.get("stake_currency", "")).upper() == "USDT"
            and 0.0 < stake_amount <= self.MAX_STAKE_USDT
            and 0.0 < available_capital <= self.MAX_TOTAL_CAPITAL_USDT
            and 1 <= max_open_trades <= self.MAX_OPEN_POSITIONS
            and stake_amount * max_open_trades <= self.MAX_TOTAL_EXPOSURE_USDT
            and math.isclose(float(self.stoploss), -0.055, abs_tol=1e-12)
            and order_types.get("entry") == "limit"
            and order_types.get("exit") == "limit"
            and order_types.get("force_exit") == "market"
            and order_types.get("emergency_exit") == "market"
            and order_types.get("stoploss") == "limit"
            and order_types.get("stoploss_on_exchange") is True
            and int(order_types.get("stoploss_on_exchange_interval", 0)) >= 60
            and math.isclose(
                float(order_types.get("stoploss_on_exchange_limit_ratio", 0.0)),
                0.99,
                abs_tol=1e-12,
            )
            and time_in_force.get("entry") == "GTC"
            and time_in_force.get("exit") == "GTC"
            and self.config.get("unfilledtimeout")
            == {
                "entry": 5,
                "exit": 5,
                "exit_timeout_count": 2,
                "unit": "minutes",
            }
            and exchange.get("name") == "binance"
            and bool(pairs)
            and set(pairs).issubset(self.ALLOWED_PAIRS)
            and len(pairs) == len(set(pairs))
            and self.config.get("force_entry_enable") is False
            and api_server_safe
            and self.config.get("telegram", {}).get("enabled") is False
            and not adjacent_parameters.is_file()
        )
        if not invariants_hold:
            raise RuntimeError("execution safety contract failed; refusing bot startup")

        if not bool(self.config.get("dry_run", True)):
            if self.config.get("initial_state") != "paused":
                raise RuntimeError("live recovery must start paused")
            if self.config.get("cancel_open_orders_on_exit") is not False:
                raise RuntimeError("live recovery must preserve existing protection orders")

    @property
    def protections(self) -> list[dict[str, Any]]:
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 4},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 96,
                "trade_limit": 3,
                "stop_duration_candles": 16,
                "only_per_pair": True,
                "only_per_side": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 192,
                "trade_limit": 4,
                "stop_duration_candles": 32,
                "max_allowed_drawdown": 0.08,
                "calculation_mode": "equity",
                "only_per_pair": True,
            },
        ]

    def _kill_switch_path(self) -> Path:
        configured_path = os.getenv("AI_TRADING_KILL_SWITCH_FILE")
        if configured_path:
            return Path(configured_path).expanduser()
        user_data_dir = Path(str(self.config.get("user_data_dir", "user_data")))
        return user_data_dir / "STOP_ENTRIES"

    @staticmethod
    def _closed_profit_since(day_start_utc: datetime, pair: str) -> float:
        closed_today = Trade.get_trades_proxy(is_open=False, close_date=day_start_utc)
        return sum(
            float(trade.close_profit_abs or 0.0)
            for trade in closed_today
            if getattr(trade, "pair", None) == pair
        )

    @informative("1h")
    def populate_indicators_1h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        del metadata
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(8)
        ).astype(int)
        return dataframe

    @informative("4h")
    def populate_indicators_4h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        del metadata
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["momentum_30d"] = (
            dataframe["close"] / dataframe["close"].shift(180) - 1.0
        )
        dataframe["donchian_entry"] = (
            dataframe["high"].shift(1).rolling(120, min_periods=120).max()
        )
        dataframe["donchian_exit"] = (
            dataframe["low"].shift(1).rolling(60, min_periods=60).min()
        )
        dataframe["fresh_breakout"] = (
            (dataframe["close"] > dataframe["donchian_entry"])
            & (
                dataframe["close"].shift(1)
                <= dataframe["donchian_entry"].shift(1)
            )
        ).astype(int)
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(3)
        ).astype(int)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata
        dataframe["ema_exec"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["volume_mean"] = (
            dataframe["volume"].shift(1).rolling(20, min_periods=20).mean()
        )
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_mean"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))
        if pair not in self.ALLOWED_PAIRS:
            dataframe["regime_state"] = self.REGIME_NO_TRADE
            dataframe["route_family"] = self.FAMILY_NO_TRADE
            dataframe["no_trade_reason"] = "unsupported_pair"
            return dataframe

        asset = pair.split("/")[0].lower()
        fresh_signal = (
            (dataframe["fresh_breakout_4h"] > 0)
            & (dataframe["fresh_breakout_4h"].shift(1).fillna(0) <= 0)
        )
        trend_4h = (
            fresh_signal
            & (dataframe["close_4h"] > dataframe["ema_fast_4h"])
            & (dataframe["ema_fast_4h"] > dataframe["ema_slow_4h"])
            & (dataframe["ema_fast_rising_4h"] > 0)
            & (dataframe["adx_4h"] >= self.BUY_ADX_4H_MIN)
            & (dataframe["momentum_30d_4h"] >= self.BUY_MOMENTUM_30D)
            & (dataframe["rsi_4h"] >= 50)
            & (dataframe["rsi_4h"] <= self.BUY_RSI_4H_MAX)
        )
        trend_1h = (
            (dataframe["close_1h"] > dataframe["ema_fast_1h"])
            & (dataframe["ema_fast_1h"] > dataframe["ema_slow_1h"])
            & (dataframe["ema_fast_rising_1h"] > 0)
            & (dataframe["rsi_1h"] >= 48)
        )
        execution = (
            (dataframe["close"] > dataframe["ema_exec"])
            & (dataframe["ema_exec"] > dataframe["ema_fast"])
            & (dataframe["rsi"] >= 48)
            & (dataframe["rsi"] <= 78)
            & (dataframe["atr_pct"] >= self.BUY_ATR_MIN)
            & (dataframe["atr_pct"] <= self.BUY_ATR_MAX)
            & (dataframe["volume"] > 0)
        )
        signal = trend_4h & trend_1h & execution

        dataframe["regime_state"] = self.REGIME_NO_TRADE
        dataframe["route_family"] = self.FAMILY_NO_TRADE
        dataframe["no_trade_reason"] = "wait_fresh_4h_donchian"
        dataframe.loc[trend_4h & trend_1h, "regime_state"] = self.REGIME_TREND
        dataframe.loc[trend_4h & trend_1h, "no_trade_reason"] = "wait_execution_gate"
        dataframe.loc[signal, "route_family"] = self.FAMILY_DONCHIAN
        dataframe.loc[signal, "no_trade_reason"] = ""
        dataframe.loc[
            signal,
            ["enter_long", "enter_tag"],
        ] = (1, f"v12_4_{asset}_donchian")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata
        structure_exit = dataframe["close_4h"] < dataframe["donchian_exit_4h"]
        regime_exit = (
            (dataframe["close_4h"] < dataframe["ema_fast_4h"])
            & (dataframe["momentum_30d_4h"] < 0.0)
        )
        dataframe.loc[
            (structure_exit | regime_exit) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "v12_4_slow_trend_exit")
        return dataframe

    def order_filled(
        self,
        pair: str,
        trade: Trade,
        order: Any,
        current_time: datetime,
        **kwargs: Any,
    ) -> None:
        del pair, current_time, kwargs
        try:
            if (
                trade.nr_of_successful_entries != 1
                or getattr(order, "ft_order_side", None) != trade.entry_side
                or self.dp is None
            ):
                return
            dataframe, _ = self.dp.get_analyzed_dataframe(
                trade.pair, self.timeframe
            )
            if dataframe.empty:
                return
            candle = dataframe.iloc[-1].squeeze()
            level = float(candle["donchian_entry_4h"])
            atr = float(candle["atr_4h"])
            if math.isfinite(level) and math.isfinite(atr) and atr > 0:
                trade.set_custom_data(key="entry_breakout_level", value=level)
                trade.set_custom_data(key="entry_atr_4h", value=atr)
        except Exception:
            return

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> str | None:
        del pair, kwargs
        try:
            age_hours = (
                current_time - trade.open_date_utc
            ).total_seconds() / 3600.0
            if age_hours > 48 or current_profit >= 0:
                return None
            level = trade.get_custom_data(
                key="entry_breakout_level", default=None
            )
            atr = trade.get_custom_data(key="entry_atr_4h", default=None)
            if level is None or atr is None:
                return None
            failure = float(level) - self.BUY_FAILURE_ATR * float(atr)
            if float(current_rate) < failure:
                return "v12_4_failed_4h_breakout"
        except Exception:
            return None
        return None

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
        del pair, current_time, current_rate, entry_tag, kwargs
        try:
            if side != "long" or float(leverage) != 1.0:
                return 0.0
            capped_stake = min(
                float(proposed_stake), float(max_stake), self.MAX_STAKE_USDT
            )
            if min_stake is not None and capped_stake < float(min_stake):
                return 0.0
            return max(0.0, capped_stake)
        except Exception:
            return 0.0

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
        del entry_tag, kwargs
        try:
            if side != "long":
                return False
            if not self._runtime_entry_guards_enabled():
                return True
            if self._runmode_value(self.config) not in {"live", "dry_run"}:
                return False
            if str(self.config.get("trading_mode", "")).lower() != "spot":
                return False
            if str(self.config.get("margin_mode", "")):
                return False
            if str(self.config.get("stake_currency", "")).upper() != "USDT":
                return False
            if pair not in self.ALLOWED_PAIRS:
                return False
            if order_type != "limit" or time_in_force != "GTC":
                return False
            if bool(self.config.get("position_adjustment_enable", False)):
                return False
            max_open = int(self.config.get("max_open_trades", -1))
            if not 1 <= max_open <= self.MAX_OPEN_POSITIONS:
                return False
            if float(self.config.get("stake_amount", 0.0)) > self.MAX_STAKE_USDT:
                return False
            if self._kill_switch_path().is_file():
                return False

            now_utc = current_time.astimezone(UTC)
            day_start_utc = now_utc.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            if (
                self._closed_profit_since(day_start_utc, pair)
                <= -self.MAX_DAILY_LOSS_USDT_PER_PAIR
            ):
                return False

            requested_stake = max(0.0, float(amount) * float(rate))
            if requested_stake > self.MAX_STAKE_USDT + 1e-6:
                return False
            configured_cap = min(
                float(
                    self.config.get(
                        "available_capital",
                        self.MAX_TOTAL_CAPITAL_USDT,
                    )
                ),
                self.MAX_TOTAL_CAPITAL_USDT,
            )
            open_stake = float(Trade.total_open_trades_stakes())
            open_positions = int(Trade.get_open_trade_count())
            return (
                open_positions < self.MAX_OPEN_POSITIONS
                and (open_stake + requested_stake)
                <= (
                    min(configured_cap, self.MAX_TOTAL_EXPOSURE_USDT)
                    + 1e-6
                )
            )
        except Exception:
            return False
