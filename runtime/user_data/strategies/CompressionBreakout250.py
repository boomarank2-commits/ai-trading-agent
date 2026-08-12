"""Conservative, long-only volatility-compression breakout baseline.

This is a research baseline, not a profit claim.  Signals are calculated from
closed candles only.  Every rolling breakout boundary is shifted by one candle
so the candle being evaluated cannot define the level it must break.
"""

from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy
from pandas import DataFrame


class CompressionBreakout250(IStrategy):
    """15-minute trend/volume breakout after recent volatility compression."""

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

    # Tight, interpretable search spaces.  Window lengths remain fixed so
    # hyperopt does not accidentally reuse indicators calculated for another
    # period.
    buy_compression_width = DecimalParameter(
        0.020, 0.080, default=0.045, decimals=3, space="buy", optimize=True, load=True
    )
    buy_volume_factor = DecimalParameter(
        1.05, 2.20, default=1.30, decimals=2, space="buy", optimize=True, load=True
    )
    buy_breakout_buffer = DecimalParameter(
        0.000, 0.008, default=0.001, decimals=3, space="buy", optimize=True, load=True
    )
    buy_rsi_max = IntParameter(
        58, 78, default=72, space="buy", optimize=True, load=True
    )
    buy_atr_min = DecimalParameter(
        0.002, 0.020, default=0.006, decimals=3, space="buy", optimize=True, load=True
    )
    buy_atr_max = DecimalParameter(
        0.020, 0.080, default=0.050, decimals=3, space="buy", optimize=True, load=True
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
            "Compression": {"bb_width": {}, "compression_floor": {}},
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

        # Current candle is excluded from all reference levels and baselines.
        dataframe["compression_floor"] = (
            dataframe["bb_width"].shift(1).rolling(32, min_periods=32).min()
        )
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

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata

        trend_is_up = (
            (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["ema_fast"] > dataframe["ema_fast"].shift(1))
        )
        recent_compression = (
            dataframe["compression_floor"] <= self.buy_compression_width.value
        )
        confirmed_breakout = dataframe["close"] > (
            dataframe["breakout_high"] * (1.0 + self.buy_breakout_buffer.value)
        )
        healthy_volatility = (
            (dataframe["atr_pct"] >= self.buy_atr_min.value)
            & (dataframe["atr_pct"] <= self.buy_atr_max.value)
        )

        dataframe.loc[
            (
                trend_is_up
                & recent_compression
                & confirmed_breakout
                & healthy_volatility
                & (dataframe["volume_ratio"] >= self.buy_volume_factor.value)
                & (dataframe["rsi"] <= self.buy_rsi_max.value)
                & (dataframe["close"] > dataframe["open"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "compression_breakout")

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

        dataframe.loc[
            (
                (trend_failure | channel_breakdown)
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "trend_or_channel_failure")

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
            # stake on exceptions.  Swallow expected conversion/state errors
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
