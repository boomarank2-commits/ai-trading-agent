"""V12.15 V12.12 core with a late champion-profit ratchet.

V12.9 keeps every V12.8 champion entry path intact, removes the SOL +5% -> +1%
profit ratchet after the exact 1m-detail backtest showed that it clipped the
economics of the broader SOL core, and adds one deliberately simple challenger:
a causal 15m EMA20 reclaim inside an already-established 1h/4h uptrend.

The V12.12 pair universe, signal thresholds, BTC/ETH reclaim paths, exits and
loss protections remain unchanged. The only decision change is a deliberately
late profit ratchet for champion-Donchian trades: after at least +30% open
profit, the stop may rise to +5% from entry. Reclaims do not use the ratchet.
Before +30%, the original hard stop remains unchanged.

Research target: >1 USDT/day on a 250 USDT single-pair backtest account is a
stretch objective, not an optimization constraint. No threshold is allowed to
be changed merely to force that number on already-seen history.

Safety: Binance Spot, long-only, 1x, max 80 USDT per position, max three
positions / 240 USDT total exposure, hard stop -5.5%, no DCA.
"""

from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import (
    DecimalParameter,
    IntParameter,
    IStrategy,
    informative,
    stoploss_from_open,
)
from pandas import DataFrame


class CompressionBreakout250(IStrategy):
    """V12.15: V12.12 signals with a +30% to +5% champion ratchet."""

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "V12.15"

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
    MAX_DAILY_LOSS_USDT_PER_PAIR = MAX_DAILY_LOSS_USDT

    ALLOWED_PAIRS: ClassVar[set[str]] = {
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "XRP/USDT",
        "BNB/USDT",
        "DOGE/USDT",
    }
    BROAD_CORE_PAIRS: ClassVar[set[str]] = {
        "SOL/USDT",
        "XRP/USDT",
        "BNB/USDT",
        "DOGE/USDT",
    }

    buy_momentum_30d = DecimalParameter(
        -0.02, 0.20, default=0.03, decimals=2, space="buy", optimize=True, load=True
    )
    buy_adx_4h_min = IntParameter(
        12, 32, default=16, space="buy", optimize=True, load=True
    )
    buy_rsi_4h_max = IntParameter(
        66, 84, default=78, space="buy", optimize=True, load=True
    )
    buy_atr_min = DecimalParameter(
        0.002, 0.020, default=0.003, decimals=3, space="buy", optimize=True, load=True
    )
    buy_atr_max = DecimalParameter(
        0.020, 0.080, default=0.060, decimals=3, space="buy", optimize=True, load=True
    )
    buy_failure_atr = DecimalParameter(
        0.20, 1.00, default=0.50, decimals=2, space="buy", optimize=True, load=True
    )

    PAIR_PROFILES: ClassVar[dict[str, dict[str, float | int]]] = {
        "BTC/USDT": {
            "adx_min": 16,
            "momentum_min": 0.03,
            "rsi_min": 50,
            "rsi_max": 78,
            "persistence_bars": 3,
            "volume_min": 1.00,
            "breakout_strength_min_atr": 0.03,
            "breakout_strength_max_atr": 2.50,
        },
        "ETH/USDT": {
            "adx_min": 18,
            "momentum_min": 0.04,
            "rsi_min": 50,
            "rsi_max": 78,
            "persistence_bars": 4,
            "volume_min": 0.0,
            "breakout_strength_min_atr": 0.02,
            "breakout_strength_max_atr": 2.50,
        },
        "SOL/USDT": {
            "adx_min": 21,
            "momentum_min": 0.07,
            "rsi_min": 52,
            "rsi_max": 76,
            "persistence_bars": 6,
            "volume_min": 0.70,
            "breakout_strength_min_atr": 0.06,
            "breakout_strength_max_atr": 2.20,
        },
    }

    RECLAIM_PROFILES: ClassVar[dict[str, dict[str, float]]] = {
        "BTC/USDT": {
            "adx_min": 20.0,
            "momentum_min": 0.04,
            "rsi_4h_max": 76.0,
            "volume_min": 0.80,
        },
        "ETH/USDT": {
            "adx_min": 20.0,
            "momentum_min": 0.04,
            "rsi_4h_max": 76.0,
            "volume_min": 0.0,
        },
    }

    REGIME_TREND = "TREND/BREAKOUT"
    REGIME_NO_TRADE = "NO_TRADE"
    FAMILY_DONCHIAN = "DONCHIAN_TREND"
    FAMILY_RECLAIM = "TREND_RECLAIM"
    FAMILY_NO_TRADE = "NO_TRADE"

    minimal_roi: ClassVar[dict[str, float]] = {"0": 0.50}
    stoploss = -0.055
    trailing_stop = False
    use_custom_stoploss = True
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
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 1344,
                "trade_limit": 2,
                "stop_duration_candles": 288,
                "required_profit": 0.0,
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
            & (dataframe["close"].shift(1) <= dataframe["donchian_entry"].shift(1))
        ).astype(int)
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(3)
        ).astype(int)
        for bars in (3, 4, 6):
            dataframe[f"trend_persist_{bars}"] = (
                (dataframe["close"] > dataframe["ema_fast"])
                & (dataframe["ema_fast"] > dataframe["ema_slow"])
                & (
                    dataframe["close"].shift(bars - 1)
                    > dataframe["ema_fast"].shift(bars - 1)
                )
                & (dataframe["ema_fast"] > dataframe["ema_fast"].shift(bars))
            ).astype(int)
        dataframe["volume_mean"] = (
            dataframe["volume"].shift(1).rolling(20, min_periods=20).mean()
        )
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_mean"]
        dataframe["breakout_strength_atr"] = (
            (dataframe["close"] - dataframe["donchian_entry"]) / dataframe["atr"]
        )
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

        prior_touch = (
            (dataframe["low"] <= dataframe["ema_exec"])
            & (dataframe["close"] > dataframe["ema_fast"])
        ).shift(1)
        dataframe["pullback_touch_recent"] = (
            prior_touch.rolling(12, min_periods=1).max().fillna(False).astype(int)
        )
        dataframe["ema20_reclaim"] = (
            (dataframe["close"] > dataframe["ema_exec"])
            & (dataframe["close"].shift(1) <= dataframe["ema_exec"].shift(1))
        ).astype(int)
        dataframe["ema_exec_rising"] = (
            dataframe["ema_exec"] > dataframe["ema_exec"].shift(4)
        ).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Run unchanged champions plus one separately tagged reclaim challenger."""
        pair = str(metadata.get("pair", ""))
        dataframe["regime_state"] = self.REGIME_NO_TRADE
        dataframe["route_family"] = self.FAMILY_NO_TRADE
        dataframe["no_trade_reason"] = "wait_signal"

        if pair not in self.ALLOWED_PAIRS:
            dataframe["no_trade_reason"] = "unsupported_pair"
            return dataframe

        asset = pair.split("/")[0].lower()

        fresh_slow = (
            (dataframe["fresh_breakout_4h"] > 0)
            & (dataframe["fresh_breakout_4h"].shift(1).fillna(0) <= 0)
        )
        base_4h = (
            fresh_slow
            & (dataframe["close_4h"] > dataframe["ema_fast_4h"])
            & (dataframe["ema_fast_4h"] > dataframe["ema_slow_4h"])
            & (dataframe["ema_fast_rising_4h"] > 0)
            & (dataframe["adx_4h"] >= self.buy_adx_4h_min.value)
            & (dataframe["momentum_30d_4h"] >= self.buy_momentum_30d.value)
            & (dataframe["rsi_4h"] >= 50)
            & (dataframe["rsi_4h"] <= self.buy_rsi_4h_max.value)
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
            & (dataframe["atr_pct"] >= self.buy_atr_min.value)
            & (dataframe["atr_pct"] <= self.buy_atr_max.value)
            & (dataframe["volume"] > 0)
        )

        if pair == "BTC/USDT":
            champion_quality = dataframe["volume_ratio"] >= 1.00
        elif pair == "ETH/USDT":
            profile = self.PAIR_PROFILES[pair]
            persistence_col = f"trend_persist_{int(profile['persistence_bars'])}_4h"
            champion_quality = (
                (dataframe["adx_4h"] >= float(profile["adx_min"]))
                & (dataframe["momentum_30d_4h"] >= float(profile["momentum_min"]))
                & (dataframe["rsi_4h"] >= float(profile["rsi_min"]))
                & (dataframe["rsi_4h"] <= float(profile["rsi_max"]))
                & (dataframe[persistence_col] > 0)
                & (
                    dataframe["breakout_strength_atr_4h"]
                    >= float(profile["breakout_strength_min_atr"])
                )
                & (
                    dataframe["breakout_strength_atr_4h"]
                    <= float(profile["breakout_strength_max_atr"])
                )
            )
        elif pair in self.BROAD_CORE_PAIRS:
            champion_quality = dataframe["volume"] > 0
        else:  # Defensive: ALLOWED_PAIRS and routing must never drift apart.
            dataframe["no_trade_reason"] = "missing_pair_route"
            return dataframe

        champion_qualified = base_4h & trend_1h & champion_quality
        champion_signal = champion_qualified & execution

        dataframe.loc[champion_qualified, "regime_state"] = self.REGIME_TREND
        dataframe.loc[champion_qualified, "no_trade_reason"] = "wait_execution_gate"
        dataframe.loc[champion_signal, "route_family"] = self.FAMILY_DONCHIAN
        dataframe.loc[champion_signal, "no_trade_reason"] = ""
        dataframe.loc[champion_signal, ["enter_long", "enter_tag"]] = (
            1,
            f"v12_15_{asset}_champion_donchian",
        )

        if pair in self.RECLAIM_PROFILES:
            reclaim_profile = self.RECLAIM_PROFILES[pair]
            reclaim_4h = (
                (dataframe["close_4h"] > dataframe["ema_fast_4h"])
                & (dataframe["ema_fast_4h"] > dataframe["ema_slow_4h"])
                & (dataframe["ema_fast_rising_4h"] > 0)
                & (dataframe["adx_4h"] >= reclaim_profile["adx_min"])
                & (
                    dataframe["momentum_30d_4h"]
                    >= reclaim_profile["momentum_min"]
                )
                & (dataframe["rsi_4h"] >= 50)
                & (dataframe["rsi_4h"] <= reclaim_profile["rsi_4h_max"])
            )
            reclaim_execution = (
                (dataframe["pullback_touch_recent"] > 0)
                & (dataframe["ema20_reclaim"] > 0)
                & (dataframe["ema_exec_rising"] > 0)
                & (dataframe["ema_exec"] > dataframe["ema_fast"])
                & (dataframe["close"] > dataframe["ema_fast"])
                & (dataframe["rsi"] >= 52)
                & (dataframe["rsi"] <= 78)
                & (dataframe["atr_pct"] >= self.buy_atr_min.value)
                & (dataframe["atr_pct"] <= self.buy_atr_max.value)
                & (dataframe["volume"] > 0)
            )
            reclaim_volume = (
                dataframe["volume_ratio"] >= reclaim_profile["volume_min"]
                if reclaim_profile["volume_min"] > 0
                else dataframe["volume"] > 0
            )
            reclaim_signal = (
                reclaim_4h
                & trend_1h
                & reclaim_execution
                & reclaim_volume
                & ~champion_signal
            )
            dataframe.loc[reclaim_signal, "regime_state"] = self.REGIME_TREND
            dataframe.loc[reclaim_signal, "route_family"] = self.FAMILY_RECLAIM
            dataframe.loc[reclaim_signal, "no_trade_reason"] = ""
            dataframe.loc[reclaim_signal, ["enter_long", "enter_tag"]] = (
                1,
                f"v12_15_{asset}_trend_reclaim",
            )

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
        ] = (1, "v12_15_slow_trend_exit")
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
            dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if dataframe.empty:
                return
            candle = dataframe.iloc[-1].squeeze()

            level = float(candle["donchian_entry_4h"])
            atr_4h = float(candle["atr_4h"])
            if math.isfinite(level) and math.isfinite(atr_4h) and atr_4h > 0:
                trade.set_custom_data(key="entry_breakout_level", value=level)
                trade.set_custom_data(key="entry_atr_4h", value=atr_4h)

            ema_fast = float(candle["ema_fast"])
            atr_15m = float(candle["atr"])
            if math.isfinite(ema_fast) and math.isfinite(atr_15m) and atr_15m > 0:
                trade.set_custom_data(key="entry_ema_fast_15m", value=ema_fast)
                trade.set_custom_data(key="entry_atr_15m", value=atr_15m)
        except Exception:
            return

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
        """Lock one initial risk unit only after an exceptional champion move."""

        del pair, current_time, current_rate, after_fill, kwargs
        enter_tag = str(getattr(trade, "enter_tag", "") or "")
        if "_champion_donchian" not in enter_tag or current_profit < 0.30:
            return None
        return stoploss_from_open(
            0.05,
            current_profit,
            is_short=bool(getattr(trade, "is_short", False)),
            leverage=float(getattr(trade, "leverage", 1.0) or 1.0),
        )

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> str | None:
        """Use distinct failure logic for champion and reclaim entries."""
        del kwargs
        try:
            age_hours = (
                current_time - trade.open_date_utc
            ).total_seconds() / 3600.0
            enter_tag = str(getattr(trade, "enter_tag", "") or "")

            if "_trend_reclaim" in enter_tag:
                if current_profit >= 0:
                    return None
                ema_fast = trade.get_custom_data(
                    key="entry_ema_fast_15m", default=None
                )
                atr_15m = trade.get_custom_data(key="entry_atr_15m", default=None)
                if (
                    age_hours <= 24.0
                    and ema_fast is not None
                    and atr_15m is not None
                    and float(current_rate)
                    < float(ema_fast) - 0.50 * float(atr_15m)
                ):
                    return f"v12_15_{pair.split('/')[0].lower()}_reclaim_failed"
                if age_hours >= 48.0:
                    return f"v12_15_{pair.split('/')[0].lower()}_reclaim_time_stop"
                return None

            if current_profit >= 0:
                return None
            if pair == "ETH/USDT":
                failure_atr = 0.45
                failure_hours = 36.0
            else:
                failure_atr = 0.50
                failure_hours = 48.0

            if age_hours > failure_hours:
                return None
            level = trade.get_custom_data(key="entry_breakout_level", default=None)
            atr = trade.get_custom_data(key="entry_atr_4h", default=None)
            if level is None or atr is None:
                return None
            failure = float(level) - failure_atr * float(atr)
            if float(current_rate) < failure:
                return f"v12_15_{pair.split('/')[0].lower()}_failed_breakout"
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
