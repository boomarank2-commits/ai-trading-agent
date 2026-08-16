"""V10 independent multi-pair momentum/pullback strategy for the 250 USDT testbot.

BTC, ETH and SOL make entry/exit decisions only from their own candles.
There is no BTC regime gate for altcoins. V10 is intentionally more active
than the V8/V9 20-day Donchian family and accepts a wider drawdown envelope
in exchange for more opportunities. The bot remains spot, long-only and paper-only.
"""

from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy, informative
from pandas import DataFrame


class CompressionBreakout250(IStrategy):
    """V10: independent 15m breakout + pullback/reclaim engines per pair."""

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "V10"

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
    MAX_DAILY_LOSS_USDT = 10.0
    MAX_DAILY_LOSS_USDT_PER_PAIR = 10.0

    PAIR_RULES: ClassVar[dict[str, dict[str, float]]] = {
        "BTC/USDT": {
            "volume_min": 0.78,
            "rsi_min": 50.0,
            "rsi_max": 73.0,
            "adx_1h_min": 17.0,
            "atr_min": 0.0020,
            "atr_max": 0.040,
            "breakout_column": "breakout_24",
            "take_profit": 0.045,
            "pullback_touch_atr": 0.35,
        },
        "ETH/USDT": {
            "volume_min": 0.68,
            "rsi_min": 48.0,
            "rsi_max": 75.0,
            "adx_1h_min": 15.0,
            "atr_min": 0.0025,
            "atr_max": 0.055,
            "breakout_column": "breakout_20",
            "take_profit": 0.055,
            "pullback_touch_atr": 0.45,
        },
        "SOL/USDT": {
            "volume_min": 0.58,
            "rsi_min": 46.0,
            "rsi_max": 77.0,
            "adx_1h_min": 13.0,
            "atr_min": 0.0030,
            "atr_max": 0.080,
            "breakout_column": "breakout_16",
            "take_profit": 0.065,
            "pullback_touch_atr": 0.55,
        },
    }

    # Config currently suppresses ROI exits; V10 manages turnover explicitly
    # through exit signals and custom_exit while keeping the emergency stop intact.
    minimal_roi: ClassVar[dict[str, float]] = {"0": 0.50}
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

    # Explicit research spaces retained for controlled later tuning.
    buy_volume_min = DecimalParameter(
        0.45, 1.20, default=0.65, decimals=2, space="buy", optimize=True, load=True
    )
    buy_adx_min = IntParameter(
        10, 30, default=15, space="buy", optimize=True, load=True
    )
    buy_rsi_min = IntParameter(
        42, 58, default=48, space="buy", optimize=True, load=True
    )
    buy_rsi_max = IntParameter(
        68, 82, default=76, space="buy", optimize=True, load=True
    )
    buy_atr_min = DecimalParameter(
        0.001, 0.012, default=0.002, decimals=3, space="buy", optimize=True, load=True
    )
    buy_atr_max = DecimalParameter(
        0.025, 0.100, default=0.070, decimals=3, space="buy", optimize=True, load=True
    )
    sell_rsi_floor = IntParameter(
        36, 52, default=44, space="sell", optimize=True, load=True
    )
    sell_structure_window = IntParameter(
        6, 20, default=12, space="sell", optimize=True, load=True
    )

    plot_config: ClassVar[dict[str, Any]] = {
        "main_plot": {
            "ema_exec": {},
            "ema_fast": {},
            "ema_slow": {},
            "breakout_24": {},
        },
        "subplots": {
            "Momentum": {"rsi": {}, "adx": {}},
            "Volume": {"volume_ratio": {}},
        },
    }

    @staticmethod
    def _runmode_value(config: dict[str, Any]) -> str:
        runmode = config.get("runmode", "")
        return str(getattr(runmode, "value", runmode)).lower()

    def _runtime_entry_guards_enabled(self) -> bool:
        return self._runmode_value(self.config) in {"live", "dry_run"}

    @classmethod
    def _rules(cls, pair: str) -> dict[str, float]:
        try:
            return cls.PAIR_RULES[pair]
        except KeyError as exc:
            raise ValueError(f"unsupported pair: {pair}") from exc

    def bot_start(self, **kwargs: Any) -> None:
        """Abort runtime startup if any execution invariant was weakened."""

        del kwargs
        if not self._runtime_entry_guards_enabled():
            return

        exchange = self.config.get("exchange", {})
        order_types = self.config.get("order_types", {})
        time_in_force = self.config.get("order_time_in_force", {})
        pairs = exchange.get("pair_whitelist", []) if isinstance(exchange, dict) else []
        allowed_pairs = set(self.PAIR_RULES)
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
            and set(pairs).issubset(allowed_pairs)
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
        """Pair-local locks: one coin can no longer pause another coin."""

        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 1,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 96,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "only_per_pair": True,
                "only_per_side": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 192,
                "trade_limit": 4,
                "stop_duration_candles": 24,
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
        dataframe["ema_exec"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(3)
        ).astype(int)
        return dataframe

    @informative("4h")
    def populate_indicators_4h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        del metadata
        dataframe["ema_exec"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(2)
        ).astype(int)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata
        dataframe["ema_exec"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["volume_mean"] = (
            dataframe["volume"].shift(1).rolling(20, min_periods=20).mean()
        )
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_mean"]
        dataframe["breakout_24"] = (
            dataframe["high"].shift(1).rolling(24, min_periods=24).max()
        )
        dataframe["breakout_20"] = (
            dataframe["high"].shift(1).rolling(20, min_periods=20).max()
        )
        dataframe["breakout_16"] = (
            dataframe["high"].shift(1).rolling(16, min_periods=16).max()
        )
        dataframe["exit_low"] = (
            dataframe["low"]
            .shift(1)
            .rolling(int(self.sell_structure_window.value), min_periods=6)
            .min()
        )
        candle_range = (dataframe["high"] - dataframe["low"]).replace(
            0.0, float("nan")
        )
        dataframe["close_location"] = (
            dataframe["close"] - dataframe["low"]
        ) / candle_range
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))
        rules = self._rules(pair)
        breakout_level = dataframe[str(rules["breakout_column"])]

        trend_1h = (
            (dataframe["close_1h"] > dataframe["ema_fast_1h"])
            & (dataframe["ema_exec_1h"] > dataframe["ema_fast_1h"])
            & (dataframe["ema_fast_rising_1h"] > 0)
            & (dataframe["rsi_1h"] >= 46)
            & (dataframe["adx_1h"] >= rules["adx_1h_min"])
        )

        if pair == "BTC/USDT":
            trend_4h = (
                (dataframe["close_4h"] > dataframe["ema_fast_4h"])
                & (dataframe["ema_fast_4h"] > dataframe["ema_slow_4h"])
                & (dataframe["ema_fast_rising_4h"] > 0)
            )
        elif pair == "ETH/USDT":
            trend_4h = (
                (dataframe["close_4h"] > dataframe["ema_fast_4h"])
                & (dataframe["ema_exec_4h"] > dataframe["ema_fast_4h"])
                & (dataframe["ema_fast_rising_4h"] > 0)
            )
        else:
            trend_4h = (
                (dataframe["close_4h"] > dataframe["ema_exec_4h"])
                & (dataframe["ema_exec_4h"] > dataframe["ema_fast_4h"])
                & (dataframe["ema_fast_rising_4h"] > 0)
            )

        local_trend = (
            (dataframe["ema_exec"] > dataframe["ema_fast"])
            & (dataframe["ema_fast"] > dataframe["ema_fast"].shift(3))
            & (dataframe["close"] > dataframe["ema_fast"])
        )
        healthy = (
            (dataframe["atr_pct"] >= rules["atr_min"])
            & (dataframe["atr_pct"] <= rules["atr_max"])
            & (dataframe["volume_ratio"] >= rules["volume_min"])
            & (dataframe["rsi"] >= rules["rsi_min"])
            & (dataframe["rsi"] <= rules["rsi_max"])
            & (dataframe["volume"] > 0)
        )

        breakout = (
            (dataframe["close"] > breakout_level)
            & (dataframe["close"].shift(1) <= breakout_level.shift(1))
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["close_location"] >= 0.55)
        )

        recent_pullback = False
        for offset in range(1, 4):
            recent_pullback = recent_pullback | (
                dataframe["low"].shift(offset)
                <= dataframe["ema_exec"].shift(offset)
                + rules["pullback_touch_atr"] * dataframe["atr"].shift(offset)
            )
        reclaim = (
            recent_pullback
            & (dataframe["close"] > dataframe["ema_exec"])
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["close"] > dataframe["close"].shift(1))
            & (dataframe["rsi"] > dataframe["rsi"].shift(1))
            & (dataframe["close_location"] >= 0.58)
        )

        common = trend_1h & trend_4h & local_trend & healthy
        dataframe.loc[
            common & breakout,
            ["enter_long", "enter_tag"],
        ] = (1, f"v10_{pair.split('/')[0].lower()}_breakout")
        dataframe.loc[
            common & reclaim & (dataframe.get("enter_long", 0) != 1),
            ["enter_long", "enter_tag"],
        ] = (1, f"v10_{pair.split('/')[0].lower()}_pullback")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))
        rules = self._rules(pair)
        trend_loss = (
            (dataframe["close"] < dataframe["ema_fast"])
            & (dataframe["close_1h"] < dataframe["ema_fast_1h"])
            & (dataframe["rsi"] < self.sell_rsi_floor.value)
        )
        structure_break = dataframe["close"] < dataframe["exit_low"]
        momentum_fade = (
            (dataframe["rsi"].shift(1) > rules["rsi_max"])
            & (dataframe["rsi"] < dataframe["rsi"].shift(1))
            & (dataframe["close"] < dataframe["ema_exec"])
        )
        has_volume = dataframe["volume"] > 0
        dataframe.loc[
            trend_loss & has_volume,
            ["exit_long", "exit_tag"],
        ] = (1, f"v10_{pair.split('/')[0].lower()}_trend_loss")
        dataframe.loc[
            structure_break & has_volume,
            ["exit_long", "exit_tag"],
        ] = (1, f"v10_{pair.split('/')[0].lower()}_structure")
        dataframe.loc[
            momentum_fade & has_volume,
            ["exit_long", "exit_tag"],
        ] = (1, f"v10_{pair.split('/')[0].lower()}_fade")
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
        """Increase turnover with pair-specific profit/time exits."""

        del current_rate, kwargs
        try:
            rules = self._rules(pair)
            age_hours = (current_time - trade.open_date_utc).total_seconds() / 3600.0
            if current_profit >= rules["take_profit"]:
                return f"v10_{pair.split('/')[0].lower()}_take_profit"
            if age_hours >= 36 and current_profit >= 0.01:
                return "v10_time_profit_36h"
            if age_hours >= 72 and current_profit > -0.02:
                return "v10_stale_release_72h"
            if age_hours >= 48 and current_profit <= -0.035:
                return "v10_cut_stale_loser"
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
            if pair not in self.PAIR_RULES:
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
            day_start_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            if (
                self._closed_profit_since(day_start_utc, pair)
                <= -self.MAX_DAILY_LOSS_USDT_PER_PAIR
            ):
                return False

            requested_stake = max(0.0, float(amount) * float(rate))
            if requested_stake > self.MAX_STAKE_USDT + 1e-6:
                return False
            configured_cap = min(
                float(self.config.get("available_capital", self.MAX_TOTAL_CAPITAL_USDT)),
                self.MAX_TOTAL_CAPITAL_USDT,
            )
            open_stake = float(Trade.total_open_trades_stakes())
            open_positions = int(Trade.get_open_trade_count())
            return (
                open_positions < self.MAX_OPEN_POSITIONS
                and (open_stake + requested_stake)
                <= (min(configured_cap, self.MAX_TOTAL_EXPOSURE_USDT) + 1e-6)
            )
        except Exception:
            return False
