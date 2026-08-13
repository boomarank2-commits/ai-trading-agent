"""Paper-only 1-hour Donchian trend-breakout forward-test hypothesis.

This version is intentionally separated from the live-capable baseline.  Its
rolling reference levels exclude the current candle, and its runtime callbacks
refuse every non-dry-run entry and startup path.
"""

from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from pandas import DataFrame


class PaperTrendBreakout250V1(IStrategy):
    """Closed-candle 72-hour Donchian breakout for paper forward testing."""

    INTERFACE_VERSION = 3

    can_short = False
    timeframe = "1h"
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
        "0": 0.08,
        # The paper overlay is deep-merged with the untouched baseline config.
        # These two semantically redundant points preserve 8% until day one.
        "120": 0.08,
        "360": 0.08,
        "1440": 0.04,
        "4320": 0.0,
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
        "main_plot": {
            "ema_fast": {"color": "#2f80ed"},
            "ema_slow": {"color": "#f2994a"},
            "breakout_high": {"color": "#27ae60"},
            "exit_low": {"color": "#eb5757"},
        },
        "subplots": {
            "Trend": {"adx": {}},
            "Volatility": {"atr_pct": {}},
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
        """Refuse startup unless this exact paper-only contract is in force."""

        del kwargs
        if not self._runtime_entry_guards_enabled():
            return
        if self._runmode_value(self.config) != "dry_run" or not bool(
            self.config.get("dry_run", False)
        ):
            raise RuntimeError("paper-only strategy refuses non-dry-run startup")

        exchange = self.config.get("exchange", {})
        order_types = self.config.get("order_types", {})
        time_in_force = self.config.get("order_time_in_force", {})
        api_server = self.config.get("api_server", {})
        pairs = exchange.get("pair_whitelist", []) if isinstance(exchange, dict) else []
        configured_source = getattr(type(self), "__file__", None)
        if not isinstance(configured_source, str) or not configured_source:
            raise RuntimeError("Freqtrade did not expose the resolved strategy source")
        strategy_source = Path(configured_source).resolve(strict=True)
        adjacent_parameters = strategy_source.with_suffix(".json")
        stake_amount = float(self.config.get("stake_amount", 0.0))
        available_capital = float(self.config.get("available_capital", 0.0))
        max_open_trades = int(self.config.get("max_open_trades", -1))

        invariants_hold = (
            self.can_short is False
            and self.position_adjustment_enable is False
            and self.max_entry_position_adjustment == 0
            and self.timeframe == "1h"
            and self.config.get("strategy") == type(self).__name__
            and self.config.get("timeframe") == "1h"
            and str(self.config.get("trading_mode", "")).lower() == "spot"
            and not str(self.config.get("margin_mode", ""))
            and str(self.config.get("stake_currency", "")).upper() == "USDT"
            and 0.0 < stake_amount <= self.MAX_STAKE_USDT
            and 0.0 < available_capital <= self.MAX_TOTAL_CAPITAL_USDT
            and 1 <= max_open_trades <= self.MAX_OPEN_POSITIONS
            and stake_amount * max_open_trades <= self.MAX_TOTAL_EXPOSURE_USDT
            and math.isclose(float(self.stoploss), -0.055, abs_tol=1e-12)
            and self.minimal_roi
            == {"0": 0.08, "120": 0.08, "360": 0.08, "1440": 0.04, "4320": 0.0}
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
            and pairs == ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            and self.config.get("force_entry_enable") is False
            and self.config.get("initial_state") == "running"
            and self.config.get("cancel_open_orders_on_exit") is True
            and isinstance(api_server, dict)
            and api_server.get("enabled") is True
            and api_server.get("listen_ip_address") == "127.0.0.1"
            and api_server.get("listen_port") == 8080
            and api_server.get("enable_openapi") is False
            and api_server.get("CORS_origins") == []
            and self.config.get("telegram", {}).get("enabled") is False
            and not adjacent_parameters.is_file()
        )
        if not invariants_hold:
            raise RuntimeError("paper execution safety contract failed; refusing bot startup")

    @property
    def protections(self) -> list[dict[str, Any]]:
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 6,
                "only_per_pair": False,
                "only_per_side": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 3,
                "stop_duration_candles": 12,
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
        realized_profit = 0.0
        for trade in closed_today:
            if trade.close_profit_abs is None:
                raise RuntimeError("closed trade has no realized profit")
            realized_profit += float(trade.close_profit_abs)
        return realized_profit

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["volume_mean"] = (
            dataframe["volume"].shift(1).rolling(24, min_periods=24).mean()
        )
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_mean"]
        dataframe["breakout_high"] = (
            dataframe["high"].shift(1).rolling(72, min_periods=72).max()
        )
        dataframe["exit_low"] = (
            dataframe["low"].shift(1).rolling(12, min_periods=12).min()
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["breakout_high"] * 1.001)
                & (dataframe["ema_fast"] > dataframe["ema_slow"])
                & (dataframe["ema_slow"] > dataframe["ema_slow"].shift(24))
                & (dataframe["adx"] >= 20)
                & (dataframe["atr_pct"] >= 0.003)
                & (dataframe["atr_pct"] <= 0.05)
                & (dataframe["volume_ratio"] >= 1.2)
                & (dataframe["close"] > dataframe["open"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "paper_trend_donchian_72h")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata
        ema_crossed_below = (dataframe["close"] < dataframe["ema_fast"]) & (
            dataframe["close"].shift(1) >= dataframe["ema_fast"].shift(1)
        )
        dataframe.loc[
            (
                ((dataframe["close"] < dataframe["exit_low"]) | ema_crossed_below)
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "paper_channel_or_trend_exit")
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
            if self._runmode_value(self.config) != "dry_run":
                return False
            if not bool(self.config.get("dry_run", False)):
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
                and open_stake + requested_stake
                <= min(configured_cap, self.MAX_TOTAL_EXPOSURE_USDT) + 1e-6
            )
        except Exception:
            return False
