"""Long-only confirmed multi-timeframe breakout for the 250 USDT testbot.

V3 keeps the existing safety envelope but no longer buys the first breakout
candle. A strong 15-minute setup must survive one additional closed candle,
hold its breakout support, and remain aligned with the higher-timeframe regime.
All signals are causal and calculated from closed candles only.
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
    """15m breakout setup followed by causal one-candle confirmation."""

    INTERFACE_VERSION = 3

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
        # Binance Spot supports on-exchange stop-limit, not stop-market.
        "stoploss": "limit",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_interval": 60,
        "stoploss_on_exchange_limit_ratio": 0.99,
    }
    order_time_in_force: ClassVar[dict[str, str]] = {"entry": "GTC", "exit": "GTC"}

    # Research parameters remain intentionally narrow and interpretable. The
    # production bot uses the defaults because adjacent parameter files are
    # prohibited by the runtime safety contract.
    buy_compression_width = DecimalParameter(
        0.015, 0.050, default=0.032, decimals=3, space="buy", optimize=True, load=True
    )
    buy_compression_relative = DecimalParameter(
        0.55, 0.95, default=0.80, decimals=2, space="buy", optimize=True, load=True
    )
    buy_expansion_factor = DecimalParameter(
        1.02, 1.35, default=1.10, decimals=2, space="buy", optimize=True, load=True
    )
    buy_volume_factor = DecimalParameter(
        1.05, 2.20, default=1.35, decimals=2, space="buy", optimize=True, load=True
    )
    buy_breakout_atr = DecimalParameter(
        0.05, 0.60, default=0.20, decimals=2, space="buy", optimize=True, load=True
    )
    buy_body_ratio = DecimalParameter(
        0.40, 0.80, default=0.55, decimals=2, space="buy", optimize=True, load=True
    )
    buy_close_location = DecimalParameter(
        0.60, 0.95, default=0.75, decimals=2, space="buy", optimize=True, load=True
    )
    buy_confirmation_hold_atr = DecimalParameter(
        0.05, 0.35, default=0.20, decimals=2, space="buy", optimize=True, load=True
    )
    buy_confirmation_close_atr = DecimalParameter(
        0.00, 0.30, default=0.05, decimals=2, space="buy", optimize=True, load=True
    )
    buy_rsi_max = IntParameter(
        60, 76, default=70, space="buy", optimize=True, load=True
    )
    buy_atr_min = DecimalParameter(
        0.004, 0.020, default=0.006, decimals=3, space="buy", optimize=True, load=True
    )
    buy_atr_max = DecimalParameter(
        0.020, 0.080, default=0.045, decimals=3, space="buy", optimize=True, load=True
    )
    sell_rsi_floor = IntParameter(
        35, 55, default=45, space="sell", optimize=True, load=True
    )

    plot_config: ClassVar[dict[str, Any]] = {
        "main_plot": {
            "ema_fast": {"color": "#2f80ed"},
            "ema_slow": {"color": "#f2994a"},
            "breakout_high": {"color": "#27ae60"},
            "exit_low": {"color": "#eb5757"},
        },
        "subplots": {
            "Compression": {"bb_width": {}, "compression_recent": {}},
            "Volume": {"volume_ratio": {}},
            "Momentum": {"rsi": {}},
        },
    }

    @staticmethod
    def _runmode_value(config: dict[str, Any]) -> str:
        runmode = config.get("runmode", "")
        return str(getattr(runmode, "value", runmode)).lower()

    def _runtime_entry_guards_enabled(self) -> bool:
        """Keep filesystem/DB guards out of backtest, hyperopt and analysis."""

        return self._runmode_value(self.config) in {"live", "dry_run"}

    def bot_start(self, **kwargs: Any) -> None:
        """Abort runtime startup if any execution invariant was weakened."""

        del kwargs
        if not self._runtime_entry_guards_enabled():
            return

        exchange = self.config.get("exchange", {})
        order_types = self.config.get("order_types", {})
        time_in_force = self.config.get("order_time_in_force", {})
        pairs = exchange.get("pair_whitelist", []) if isinstance(exchange, dict) else []
        allowed_pairs = {"BTC/USDT", "ETH/USDT", "SOL/USDT"}
        configured_source = getattr(type(self), "__file__", None)
        if not isinstance(configured_source, str) or not configured_source:
            raise RuntimeError("Freqtrade did not expose the resolved strategy source")
        strategy_source = Path(configured_source).resolve(strict=True)
        adjacent_parameters = strategy_source.with_suffix(".json")
        stake_amount = float(self.config.get("stake_amount", 0.0))
        available_capital = float(self.config.get("available_capital", 0.0))
        max_open_trades = int(self.config.get("max_open_trades", -1))

        # The paper-test UI may expose Freqtrade only on loopback. Live recovery
        # still requires the API to remain disabled. A disabled API is also safe
        # for other runtime invocations.
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
            and 1
            <= max_open_trades
            <= self.MAX_OPEN_POSITIONS
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
        """Defensive entry locks shared by live, dry-run and enabled backtests."""

        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 2,
            },
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

    @informative("1h")
    def populate_indicators_1h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        del metadata
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(1)
        ).astype(int)
        dataframe["ema_fast_rising_3"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(3)
        ).astype(int)
        return dataframe

    @informative("4h")
    def populate_indicators_4h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        del metadata
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(1)
        ).astype(int)
        dataframe["ema_fast_rising_3"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(3)
        ).astype(int)
        return dataframe

    @informative("4h", "BTC/{stake}", fmt="{base}_{column}_{timeframe}")
    def populate_indicators_btc_4h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        del metadata
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(1)
        ).astype(int)
        dataframe["ema_fast_rising_3"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(3)
        ).astype(int)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata

        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        bb_middle = dataframe["close"].rolling(20, min_periods=20).mean()
        bb_std = dataframe["close"].rolling(20, min_periods=20).std(ddof=0)
        dataframe["bb_upper"] = bb_middle + (2.0 * bb_std)
        dataframe["bb_lower"] = bb_middle - (2.0 * bb_std)
        dataframe["bb_width"] = (
            dataframe["bb_upper"] - dataframe["bb_lower"]
        ) / bb_middle

        # A valid squeeze must be recent (3h), materially tighter than the
        # surrounding 12h regime, and expanding on the setup candle.
        dataframe["compression_recent"] = (
            dataframe["bb_width"].shift(1).rolling(12, min_periods=12).min()
        )
        dataframe["compression_reference"] = (
            dataframe["bb_width"].shift(1).rolling(48, min_periods=48).median()
        )
        dataframe["compression_expansion"] = dataframe["bb_width"] / dataframe[
            "compression_recent"
        ].replace(0.0, float("nan"))

        # Current candle is excluded from reference levels and baselines.
        dataframe["breakout_high"] = (
            dataframe["high"].shift(1).rolling(20, min_periods=20).max()
        )
        dataframe["exit_low"] = (
            dataframe["low"].shift(1).rolling(10, min_periods=10).min()
        )
        dataframe["volume_mean"] = (
            dataframe["volume"].shift(1).rolling(20, min_periods=20).mean()
        )
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_mean"]

        candle_range = (dataframe["high"] - dataframe["low"]).replace(
            0.0, float("nan")
        )
        dataframe["body_ratio"] = (
            (dataframe["close"] - dataframe["open"]).abs() / candle_range
        )
        dataframe["close_location"] = (
            dataframe["close"] - dataframe["low"]
        ) / candle_range
        dataframe["breakout_distance_atr"] = (
            dataframe["close"] - dataframe["breakout_high"]
        ) / dataframe["atr"]

        # V3 enters one candle after the breakout setup. These shifted columns
        # are the original setup candle's support and ATR, so confirmation and
        # later failed-breakout exits reference the same causal level.
        dataframe["confirmation_breakout_level"] = dataframe["breakout_high"].shift(1)
        dataframe["confirmation_atr"] = dataframe["atr"].shift(1)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))

        trend_is_up = (
            (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["ema_fast"] > dataframe["ema_fast"].shift(1))
        )

        fresh_compression = (
            (dataframe["compression_recent"] <= self.buy_compression_width.value)
            & (
                dataframe["compression_recent"]
                <= (
                    dataframe["compression_reference"]
                    * self.buy_compression_relative.value
                )
            )
        )
        volatility_expanding = (
            dataframe["compression_expansion"] >= self.buy_expansion_factor.value
        ) & (dataframe["bb_width"] > dataframe["bb_width"].shift(1))
        confirmed_breakout = (
            dataframe["breakout_distance_atr"] >= self.buy_breakout_atr.value
        )
        healthy_volatility = (
            (dataframe["atr_pct"] >= self.buy_atr_min.value)
            & (dataframe["atr_pct"] <= self.buy_atr_max.value)
        )
        quality_candle = (
            (dataframe["body_ratio"] >= self.buy_body_ratio.value)
            & (dataframe["close_location"] >= self.buy_close_location.value)
            & (dataframe["close"] > dataframe["open"])
        )

        # Requiring a multi-bar EMA slope avoids treating one isolated higher
        # close as a higher-timeframe trend.
        one_hour_trend = (
            (dataframe["close_1h"] > dataframe["ema_fast_1h"])
            & (dataframe["ema_fast_1h"] > dataframe["ema_slow_1h"])
            & (dataframe["ema_fast_rising_3_1h"] > 0)
            & (dataframe["rsi_1h"] >= 50)
            & (dataframe["rsi_1h"] <= 72)
        )
        four_hour_trend = (
            (dataframe["close_4h"] > dataframe["ema_fast_4h"])
            & (dataframe["ema_fast_rising_3_4h"] > 0)
            & (dataframe["rsi_4h"] >= 50)
        )
        btc_market_up = (
            (dataframe["btc_close_4h"] > dataframe["btc_ema_fast_4h"])
            & (dataframe["btc_ema_fast_4h"] > dataframe["btc_ema_slow_4h"])
            & (dataframe["btc_ema_fast_rising_3_4h"] > 0)
            & (dataframe["btc_rsi_4h"] >= 50)
        )
        market_regime = four_hour_trend
        if pair != "BTC/USDT":
            market_regime = (
                market_regime
                & (dataframe["ema_fast_4h"] > dataframe["ema_slow_4h"])
                & btc_market_up
            )

        # The setup is V2's high-quality breakout, evaluated on a fully closed
        # candle. V3 deliberately does not enter on that first breakout candle.
        breakout_setup = (
            trend_is_up
            & one_hour_trend
            & market_regime
            & fresh_compression
            & volatility_expanding
            & confirmed_breakout
            & healthy_volatility
            & quality_candle
            & (dataframe["volume_ratio"] >= self.buy_volume_factor.value)
            & (dataframe["rsi"] >= 50)
            & (dataframe["rsi"] <= self.buy_rsi_max.value)
            & (dataframe["volume"] > 0)
        )
        prior_setup = breakout_setup.shift(1, fill_value=False)

        support = dataframe["confirmation_breakout_level"]
        setup_atr = dataframe["confirmation_atr"]
        confirmation_holds = dataframe["low"] >= (
            support - (self.buy_confirmation_hold_atr.value * setup_atr)
        )
        confirmation_closes_above = dataframe["close"] >= (
            support + (self.buy_confirmation_close_atr.value * setup_atr)
        )
        confirmation_quality = (
            (dataframe["close"] > dataframe["open"])
            & (dataframe["close_location"] >= 0.60)
            & (dataframe["volume_ratio"] >= 0.80)
        )

        dataframe.loc[
            (
                prior_setup
                & trend_is_up
                & one_hour_trend
                & market_regime
                & healthy_volatility
                & confirmation_holds
                & confirmation_closes_above
                & confirmation_quality
                & (dataframe["rsi"] >= 50)
                & (dataframe["rsi"] <= self.buy_rsi_max.value)
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "confirmed_regime_breakout")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata

        rsi_crossed_below_floor = (
            (dataframe["rsi"] < self.sell_rsi_floor.value)
            & (dataframe["rsi"].shift(1) >= self.sell_rsi_floor.value)
        )
        trend_failure = (
            (dataframe["close"] < dataframe["ema_fast"])
            & rsi_crossed_below_floor
        )
        channel_breakdown = dataframe["close"] < dataframe["exit_low"]
        has_volume = dataframe["volume"] > 0

        # Separate tags keep diagnostics useful without changing exit timing.
        dataframe.loc[
            trend_failure & has_volume,
            ["exit_long", "exit_tag"],
        ] = (1, "trend_failure")
        dataframe.loc[
            channel_breakdown & has_volume,
            ["exit_long", "exit_tag"],
        ] = (1, "channel_breakdown")

        return dataframe

    def order_filled(
        self,
        pair: str,
        trade: Trade,
        order: Any,
        current_time: datetime,
        **kwargs: Any,
    ) -> None:
        """Persist the confirmed setup support so false breakouts can fail fast."""

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
            last_candle = dataframe.iloc[-1].squeeze()
            breakout_level = float(last_candle["confirmation_breakout_level"])
            entry_atr = float(last_candle["confirmation_atr"])
            if math.isfinite(breakout_level) and math.isfinite(entry_atr) and entry_atr > 0:
                trade.set_custom_data(
                    key="entry_breakout_level", value=breakout_level
                )
                trade.set_custom_data(key="entry_atr", value=entry_atr)
        except Exception:
            # Missing analytical context must never interfere with order state.
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
        """Exit a young trade when price decisively loses confirmed support."""

        del pair, kwargs
        try:
            age_minutes = (current_time - trade.open_date_utc).total_seconds() / 60.0
            if age_minutes < 30 or age_minutes > 240 or current_profit >= 0:
                return None

            breakout_level = trade.get_custom_data(
                key="entry_breakout_level", default=None
            )
            entry_atr = trade.get_custom_data(key="entry_atr", default=None)
            if breakout_level is None or entry_atr is None:
                return None

            failure_level = float(breakout_level) - (0.15 * float(entry_atr))
            if float(current_rate) < failure_level:
                return "failed_breakout"
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
            # Freqtrade's outer callback wrapper falls back to the proposed
            # stake on exceptions. Swallow expected conversion/state errors
            # here and deny the order instead.
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

            # Backtests and hyperopt already enforce the configured wallet and
            # stake. Avoid filesystem/DB state in deterministic analysis modes.
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
            if pair not in {"BTC/USDT", "ETH/USDT", "SOL/USDT"}:
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
            if self._closed_profit_since(day_start_utc) <= -self.MAX_DAILY_LOSS_USDT:
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
            # Freqtrade's outer wrapper defaults confirm_trade_entry to True
            # when callbacks raise. Expected local state failures must be
            # converted into an explicit denial here.
            return False
