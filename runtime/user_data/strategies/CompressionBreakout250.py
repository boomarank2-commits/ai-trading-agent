"""V11 adaptive multi-strategy engine for the 250 USDT testbot.

BTC, ETH and SOL are independent decision engines.  Each pair classifies only
its own market into TREND/BREAKOUT, RANGE/MEAN_REVERSION or NO_TRADE and then
routes to one of three deterministic strategy families:

- ORB_RETEST
- ICHIMOKU_TREND
- BOLLINGER_MR

The same hashed strategy source is used by paper trading and historical
backtesting.  No cross-pair regime input is used.
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
    """V11: pair-local adaptive regime router with three strategy families."""

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "V11"

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

    BASE_FEE_PER_SIDE = 0.002
    COST_STRESS_MULTIPLIER = 1.50
    ROUNDTRIP_COST_STRESS = BASE_FEE_PER_SIDE * 2.0 * COST_STRESS_MULTIPLIER

    REGIME_TREND = "TREND/BREAKOUT"
    REGIME_RANGE = "RANGE/MEAN_REVERSION"
    REGIME_NO_TRADE = "NO_TRADE"

    FAMILY_ORB = "ORB_RETEST"
    FAMILY_ICHIMOKU = "ICHIMOKU_TREND"
    FAMILY_BOLLINGER = "BOLLINGER_MR"
    FAMILY_NO_TRADE = "NO_TRADE"

    # All thresholds are pair-local. They are intentionally fixed for the
    # first V11 candidate so the initial evidence is not contaminated by
    # implicit Hyperopt/sidecar parameters.
    PAIR_PROFILES: ClassVar[dict[str, dict[str, float]]] = {
        "BTC/USDT": {
            "trend_adx_4h": 21.0,
            "trend_adx_1h": 18.0,
            "range_adx_4h_max": 16.0,
            "range_adx_1h_max": 19.0,
            "range_ema_spread_max": 0.012,
            "range_bb_width_max": 0.035,
            "min_gross_move": 0.008,
            "orb_volume_min": 1.05,
            "ichi_volume_min": 0.90,
            "mr_volume_min": 0.65,
            "mr_rsi_max": 38.0,
            "orb_rsi_min": 50.0,
            "orb_rsi_max": 72.0,
            "ichi_rsi_min": 49.0,
            "ichi_rsi_max": 71.0,
            "orb_retest_atr": 0.35,
            "orb_range_min": 0.004,
            "orb_range_max": 0.030,
            "orb_target_atr": 2.5,
            "ichi_target_atr": 3.0,
            "orb_take_profit": 0.025,
            "ichi_take_profit": 0.035,
            "mr_soft_stop": 0.018,
            "orb_soft_stop": 0.025,
            "ichi_soft_stop": 0.030,
        },
        "ETH/USDT": {
            "trend_adx_4h": 20.0,
            "trend_adx_1h": 17.0,
            "range_adx_4h_max": 15.0,
            "range_adx_1h_max": 18.0,
            "range_ema_spread_max": 0.015,
            "range_bb_width_max": 0.045,
            "min_gross_move": 0.009,
            "orb_volume_min": 1.00,
            "ichi_volume_min": 0.85,
            "mr_volume_min": 0.60,
            "mr_rsi_max": 40.0,
            "orb_rsi_min": 49.0,
            "orb_rsi_max": 73.0,
            "ichi_rsi_min": 48.0,
            "ichi_rsi_max": 72.0,
            "orb_retest_atr": 0.40,
            "orb_range_min": 0.005,
            "orb_range_max": 0.040,
            "orb_target_atr": 2.5,
            "ichi_target_atr": 3.0,
            "orb_take_profit": 0.030,
            "ichi_take_profit": 0.045,
            "mr_soft_stop": 0.022,
            "orb_soft_stop": 0.030,
            "ichi_soft_stop": 0.035,
        },
        "SOL/USDT": {
            "trend_adx_4h": 22.0,
            "trend_adx_1h": 19.0,
            "range_adx_4h_max": 16.0,
            "range_adx_1h_max": 20.0,
            "range_ema_spread_max": 0.020,
            "range_bb_width_max": 0.060,
            "min_gross_move": 0.011,
            "orb_volume_min": 1.05,
            "ichi_volume_min": 0.90,
            "mr_volume_min": 0.65,
            "mr_rsi_max": 42.0,
            "orb_rsi_min": 50.0,
            "orb_rsi_max": 75.0,
            "ichi_rsi_min": 49.0,
            "ichi_rsi_max": 74.0,
            "orb_retest_atr": 0.45,
            "orb_range_min": 0.006,
            "orb_range_max": 0.055,
            "orb_target_atr": 2.8,
            "ichi_target_atr": 3.2,
            "orb_take_profit": 0.040,
            "ichi_take_profit": 0.060,
            "mr_soft_stop": 0.028,
            "orb_soft_stop": 0.035,
            "ichi_soft_stop": 0.040,
        },
    }

    minimal_roi: ClassVar[dict[str, float]] = {"0": 0.50}
    stoploss = -0.055
    trailing_stop = False
    use_exit_signal = False
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
            "ema_exec": {},
            "ema_fast": {},
            "bb_upper": {},
            "bb_mid": {},
            "bb_lower": {},
            "orb_high": {},
            "orb_low": {},
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
    def _profile(cls, pair: str) -> dict[str, float]:
        try:
            return cls.PAIR_PROFILES[pair]
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
        allowed_pairs = set(self.PAIR_PROFILES)
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
        """Pair-local protection locks; one asset cannot pause another."""

        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 4,
            },
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

    @staticmethod
    def _add_ichimoku(dataframe: DataFrame) -> DataFrame:
        """Add causal Ichimoku fields without using future candles.

        ``cloud_a``/``cloud_b`` are the cloud visible at the current timestamp,
        hence they are shifted from values computed 26 candles earlier.
        ``future_cloud_*`` uses the cloud projection that is knowable now.
        ``chikou_clear`` compares today's close with the historical price region
        26 candles ago; it does not shift future data backward into the signal.
        """

        high9 = dataframe["high"].rolling(9, min_periods=9).max()
        low9 = dataframe["low"].rolling(9, min_periods=9).min()
        high26 = dataframe["high"].rolling(26, min_periods=26).max()
        low26 = dataframe["low"].rolling(26, min_periods=26).min()
        high52 = dataframe["high"].rolling(52, min_periods=52).max()
        low52 = dataframe["low"].rolling(52, min_periods=52).min()

        dataframe["tenkan"] = (high9 + low9) / 2.0
        dataframe["kijun"] = (high26 + low26) / 2.0
        projected_a = (dataframe["tenkan"] + dataframe["kijun"]) / 2.0
        projected_b = (high52 + low52) / 2.0
        dataframe["cloud_a"] = projected_a.shift(26)
        dataframe["cloud_b"] = projected_b.shift(26)
        dataframe["cloud_top"] = dataframe[["cloud_a", "cloud_b"]].max(axis=1)
        dataframe["cloud_bottom"] = dataframe[["cloud_a", "cloud_b"]].min(axis=1)
        dataframe["future_cloud_bull"] = (projected_a > projected_b).astype(int)
        dataframe["chikou_clear"] = (
            dataframe["close"] > dataframe["high"].shift(26)
        ).astype(int)
        return dataframe

    @staticmethod
    def _add_common_indicators(dataframe: DataFrame) -> DataFrame:
        dataframe["ema_exec"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["ema_fast_rising"] = (
            dataframe["ema_fast"] > dataframe["ema_fast"].shift(3)
        ).astype(int)

        bands = ta.BBANDS(
            dataframe,
            timeperiod=20,
            nbdevup=2.0,
            nbdevdn=2.0,
            matype=0,
        )
        dataframe["bb_upper"] = bands["upperband"]
        dataframe["bb_mid"] = bands["middleband"]
        dataframe["bb_lower"] = bands["lowerband"]
        dataframe["bb_width"] = (
            dataframe["bb_upper"] - dataframe["bb_lower"]
        ) / dataframe["bb_mid"]
        return CompressionBreakout250._add_ichimoku(dataframe)

    @informative("1h")
    def populate_indicators_1h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        del metadata
        return self._add_common_indicators(dataframe)

    @informative("4h")
    def populate_indicators_4h(
        self, dataframe: DataFrame, metadata: dict
    ) -> DataFrame:
        del metadata
        return self._add_common_indicators(dataframe)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata
        dataframe = self._add_common_indicators(dataframe)
        dataframe["volume_mean"] = (
            dataframe["volume"].shift(1).rolling(20, min_periods=20).mean()
        )
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_mean"]

        candle_range = (dataframe["high"] - dataframe["low"]).replace(
            0.0, float("nan")
        )
        dataframe["close_location"] = (
            dataframe["close"] - dataframe["low"]
        ) / candle_range

        # Crypto has no exchange opening bell. V11 therefore defines the ORB
        # deterministically as the first four closed 15m candles of each UTC day.
        day_key = dataframe["date"].dt.floor("D")
        minutes_utc = dataframe["date"].dt.hour * 60 + dataframe["date"].dt.minute
        opening_mask = minutes_utc < 60
        dataframe["orb_high"] = (
            dataframe["high"].where(opening_mask).groupby(day_key).transform("max")
        )
        dataframe["orb_low"] = (
            dataframe["low"].where(opening_mask).groupby(day_key).transform("min")
        )
        dataframe["orb_ready"] = (minutes_utc >= 60).astype(int)
        dataframe["orb_range_pct"] = (
            dataframe["orb_high"] - dataframe["orb_low"]
        ) / dataframe["close"]

        breakout_event = (
            (dataframe["orb_ready"] > 0)
            & (dataframe["close"] > dataframe["orb_high"])
            & (dataframe["close"].shift(1) <= dataframe["orb_high"].shift(1))
        ).astype(int)
        dataframe["orb_breakout_recent"] = (
            breakout_event.groupby(day_key)
            .transform(lambda values: values.shift(1).rolling(8, min_periods=1).max())
            .fillna(0)
            .astype(int)
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = str(metadata.get("pair", ""))
        profile = self._profile(pair)
        asset = pair.split("/")[0].lower()

        trend_4h = (
            (dataframe["close_4h"] > dataframe["ema_fast_4h"])
            & (dataframe["ema_exec_4h"] > dataframe["ema_fast_4h"])
            & (dataframe["ema_fast_rising_4h"] > 0)
            & (dataframe["adx_4h"] >= profile["trend_adx_4h"])
        )
        trend_1h = (
            (dataframe["close_1h"] > dataframe["ema_fast_1h"])
            & (dataframe["ema_exec_1h"] > dataframe["ema_fast_1h"])
            & (dataframe["ema_fast_rising_1h"] > 0)
            & (dataframe["adx_1h"] >= profile["trend_adx_1h"])
        )
        trend_regime = trend_4h & trend_1h

        ema_spread_4h = (
            (dataframe["ema_exec_4h"] - dataframe["ema_fast_4h"]).abs()
            / dataframe["close_4h"]
        )
        range_regime = (
            (dataframe["adx_4h"] <= profile["range_adx_4h_max"])
            & (dataframe["adx_1h"] <= profile["range_adx_1h_max"])
            & (ema_spread_4h <= profile["range_ema_spread_max"])
            & (dataframe["bb_width_1h"] <= profile["range_bb_width_max"])
            & (dataframe["close_4h"] >= dataframe["ema_slow_4h"] * 0.96)
        )

        dataframe["regime_state"] = self.REGIME_NO_TRADE
        dataframe.loc[range_regime, "regime_state"] = self.REGIME_RANGE
        dataframe.loc[trend_regime, "regime_state"] = self.REGIME_TREND
        dataframe["route_family"] = self.FAMILY_NO_TRADE
        dataframe["no_trade_reason"] = "regime_unclear"

        orb_projected_move = dataframe[["orb_range_pct", "atr_pct"]].max(axis=1)
        orb_projected_move = orb_projected_move.combine(
            dataframe["atr_pct"] * profile["orb_target_atr"], max
        )
        orb_raw = (
            trend_regime
            & (dataframe["orb_ready"] > 0)
            & (dataframe["orb_breakout_recent"] > 0)
            & (dataframe["orb_range_pct"] >= profile["orb_range_min"])
            & (dataframe["orb_range_pct"] <= profile["orb_range_max"])
            & (
                dataframe["low"]
                <= dataframe["orb_high"]
                + profile["orb_retest_atr"] * dataframe["atr"]
            )
            & (dataframe["close"] > dataframe["orb_high"])
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["close_location"] >= 0.58)
            & (dataframe["volume_ratio"] >= profile["orb_volume_min"])
            & (dataframe["rsi"] >= profile["orb_rsi_min"])
            & (dataframe["rsi"] <= profile["orb_rsi_max"])
            & (dataframe["volume"] > 0)
        )
        orb_signal = orb_raw & (
            orb_projected_move
            >= max(self.ROUNDTRIP_COST_STRESS, profile["min_gross_move"])
        )

        ichi_cross = (
            (dataframe["tenkan"] > dataframe["kijun"])
            & (dataframe["tenkan"].shift(1) <= dataframe["kijun"].shift(1))
        )
        ichi_raw = (
            trend_regime
            & ichi_cross
            & (dataframe["close"] > dataframe["cloud_top"])
            & (dataframe["future_cloud_bull"] > 0)
            & (dataframe["chikou_clear"] > 0)
            & (dataframe["close_1h"] > dataframe["cloud_top_1h"])
            & (dataframe["tenkan_1h"] > dataframe["kijun_1h"])
            & (dataframe["future_cloud_bull_1h"] > 0)
            & (dataframe["chikou_clear_1h"] > 0)
            & (dataframe["close_4h"] > dataframe["cloud_top_4h"])
            & (dataframe["future_cloud_bull_4h"] > 0)
            & (dataframe["volume_ratio"] >= profile["ichi_volume_min"])
            & (dataframe["rsi"] >= profile["ichi_rsi_min"])
            & (dataframe["rsi"] <= profile["ichi_rsi_max"])
            & (dataframe["volume"] > 0)
        )
        ichi_projected_move = dataframe["atr_pct"] * profile["ichi_target_atr"]
        ichi_signal = ichi_raw & (
            ichi_projected_move
            >= max(self.ROUNDTRIP_COST_STRESS, profile["min_gross_move"])
        )

        mr_projected_move = (
            (dataframe["bb_mid"] - dataframe["close"]) / dataframe["close"]
        ).clip(lower=0)
        mr_raw = (
            range_regime
            & (dataframe["low"] <= dataframe["bb_lower"])
            & (dataframe["close"] > dataframe["bb_lower"])
            & (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1))
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["rsi"] <= profile["mr_rsi_max"])
            & (dataframe["rsi"] > dataframe["rsi"].shift(1))
            & (dataframe["volume_ratio"] >= profile["mr_volume_min"])
            & (dataframe["volume"] > 0)
        )
        mr_signal = mr_raw & (
            mr_projected_move
            >= max(self.ROUNDTRIP_COST_STRESS, profile["min_gross_move"])
        )

        dataframe.loc[trend_regime, "no_trade_reason"] = "trend_wait_setup"
        dataframe.loc[range_regime, "no_trade_reason"] = "range_wait_setup"
        dataframe.loc[
            (orb_raw | ichi_raw | mr_raw) & ~(orb_signal | ichi_signal | mr_signal),
            "no_trade_reason",
        ] = "cost_gate"

        dataframe.loc[orb_signal, "route_family"] = self.FAMILY_ORB
        dataframe.loc[orb_signal, "no_trade_reason"] = ""
        dataframe.loc[
            orb_signal,
            ["enter_long", "enter_tag"],
        ] = (1, f"v11_{asset}_orb_retest")

        ichi_selected = ichi_signal & (dataframe.get("enter_long", 0) != 1)
        dataframe.loc[ichi_selected, "route_family"] = self.FAMILY_ICHIMOKU
        dataframe.loc[ichi_selected, "no_trade_reason"] = ""
        dataframe.loc[
            ichi_selected,
            ["enter_long", "enter_tag"],
        ] = (1, f"v11_{asset}_ichimoku")

        mr_selected = mr_signal & (dataframe.get("enter_long", 0) != 1)
        dataframe.loc[mr_selected, "route_family"] = self.FAMILY_BOLLINGER
        dataframe.loc[mr_selected, "no_trade_reason"] = ""
        dataframe.loc[
            mr_selected,
            ["enter_long", "enter_tag"],
        ] = (1, f"v11_{asset}_bollinger_mr")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        del metadata
        dataframe["exit_long"] = 0
        return dataframe

    def _latest_causal_row(self, pair: str, current_time: datetime) -> Any | None:
        try:
            if self.dp is None:
                return None
            frame, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
            if frame is None or frame.empty or "date" not in frame.columns:
                return None
            eligible = frame.loc[frame["date"] <= current_time]
            return None if eligible.empty else eligible.iloc[-1]
        except Exception:
            return None

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> str | None:
        """Exit according to the family that actually opened the trade."""

        del kwargs
        try:
            profile = self._profile(pair)
            asset = pair.split("/")[0].lower()
            tag = str(getattr(trade, "enter_tag", "") or "")
            age_hours = (current_time - trade.open_date_utc).total_seconds() / 3600.0
            row = self._latest_causal_row(pair, current_time)

            if "_bollinger_mr" in tag:
                if row is not None and current_rate >= float(row["bb_mid"]):
                    return f"v11_{asset}_mr_midband"
                if current_profit <= -profile["mr_soft_stop"]:
                    return f"v11_{asset}_mr_soft_stop"
                if age_hours >= 24:
                    return f"v11_{asset}_mr_timeout"
                return None

            if "_orb_retest" in tag:
                if current_profit >= profile["orb_take_profit"]:
                    return f"v11_{asset}_orb_take_profit"
                if (
                    row is not None
                    and age_hours >= 2
                    and current_rate < float(row["orb_high"])
                ):
                    return f"v11_{asset}_orb_invalidation"
                if age_hours >= 6 and current_profit <= -profile["orb_soft_stop"]:
                    return f"v11_{asset}_orb_soft_stop"
                if age_hours >= 36:
                    return f"v11_{asset}_orb_timeout"
                return None

            if "_ichimoku" in tag:
                if current_profit >= profile["ichi_take_profit"]:
                    return f"v11_{asset}_ichi_take_profit"
                if row is not None:
                    local_break = (
                        current_rate < float(row["kijun"])
                        and current_rate < float(row["ema_exec"])
                    )
                    higher_tf_break = (
                        float(row["tenkan_1h"]) < float(row["kijun_1h"])
                        and current_profit < 0.01
                    )
                    if local_break and age_hours >= 2:
                        return f"v11_{asset}_ichi_local_break"
                    if higher_tf_break:
                        return f"v11_{asset}_ichi_1h_break"
                if age_hours >= 12 and current_profit <= -profile["ichi_soft_stop"]:
                    return f"v11_{asset}_ichi_soft_stop"
                if age_hours >= 96:
                    return f"v11_{asset}_ichi_timeout"
                return None

            if age_hours >= 24:
                return "v11_unknown_family_timeout"
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
            if pair not in self.PAIR_PROFILES:
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
