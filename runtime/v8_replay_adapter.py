"""Exact-source signal adapter for deterministic historical live replay.

The adapter never reimplements strategy formulas. It loads the exact hashed
strategy source and calls its own indicators/signals. Legacy strategies may
optionally request BTC 4h context; independent strategies such as V10 do not.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from freqtrade.enums import CandleType, TradingMode
from locked_freqtrade import _load_exact_strategy
from replay_core import Position, StrategyDecision


@dataclass(slots=True)
class _ReplayTradeProxy:
    pair: str
    open_date_utc: datetime
    breakout_level: float | None
    atr_4h: float | None

    def get_custom_data(self, *, key: str, default: Any = None) -> Any:
        if key == "entry_breakout_level":
            return self.breakout_level if self.breakout_level is not None else default
        if key == "entry_atr_4h":
            return self.atr_4h if self.atr_4h is not None else default
        return default


class V8ReplayAdapter:
    """Compatibility name for the exact-source replay adapter."""

    def __init__(
        self,
        *,
        strategy_source: Path,
        strategy_sha256: str,
        strategy_class: str,
        config: dict[str, Any],
    ) -> None:
        self.strategy_source = strategy_source
        self.strategy_sha256 = strategy_sha256
        self.strategy_class = strategy_class
        self.config = dict(config)
        trading_mode_value = self.config.get("trading_mode", "spot")
        try:
            trading_mode = (
                trading_mode_value
                if isinstance(trading_mode_value, TradingMode)
                else TradingMode(str(trading_mode_value))
            )
        except ValueError as exc:
            raise RuntimeError(
                f"unsupported replay trading mode: {trading_mode_value!r}"
            ) from exc
        self.config.setdefault("candle_type_def", CandleType.get_default(trading_mode))
        strategy_type, source_text = _load_exact_strategy(
            strategy_source, strategy_sha256, strategy_class
        )
        self.source_text = source_text
        self._assert_source_has_no_obvious_future_access(source_text)
        self.strategy = strategy_type(config=self.config)
        self.strategy.ft_set_special_params_from_file = lambda: None

    @staticmethod
    def _assert_source_has_no_obvious_future_access(source_text: str) -> None:
        forbidden = (
            r"\.shift\(\s*-",
            r"center\s*=\s*True",
            r"\.iloc\[\s*[^\]]*\+\s*1\s*\]",
        )
        for pattern in forbidden:
            if re.search(pattern, source_text):
                raise RuntimeError(
                    "strict replay refuses strategy source matching future-access "
                    f"pattern: {pattern}"
                )

    @staticmethod
    def _normalize(frame: Any) -> Any:
        import pandas as pd

        result = frame.copy()
        result["date"] = pd.to_datetime(result["date"], utc=True, errors="raise")
        result = result.sort_values("date", kind="stable").reset_index(drop=True)
        if result["date"].duplicated().any():
            raise RuntimeError("duplicate candles are forbidden in strict replay")
        return result

    @staticmethod
    def _merge_informative(
        base: Any, informative: Any, *, minutes: int, prefix: str
    ) -> Any:
        """As-of merge where an informative candle becomes visible only after close."""
        import pandas as pd

        left = base.copy()
        right = informative.copy()
        left["_base_known_at"] = left["date"] + pd.to_timedelta(15, unit="m")
        right["_available_at"] = right["date"] + pd.to_timedelta(minutes, unit="m")
        renamed: dict[str, str] = {}
        suffix = "1h" if minutes == 60 else "4h"
        for column in right.columns:
            if column in {"date", "_available_at"}:
                continue
            renamed[column] = f"{prefix}{column}_{suffix}"
        right = right.rename(columns=renamed)
        right = right.drop(columns=["date"])
        merged = pd.merge_asof(
            left.sort_values("_base_known_at"),
            right.sort_values("_available_at"),
            left_on="_base_known_at",
            right_on="_available_at",
            direction="backward",
            allow_exact_matches=True,
        )
        return merged.drop(columns=["_available_at"], errors="ignore")

    @staticmethod
    def _finite_float(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def decisions(
        self,
        *,
        pair: str,
        candles_15m: Any,
        candles_1h: Any,
        candles_4h: Any,
        btc_4h: Any,
        decision_start: datetime,
        decision_end: datetime,
    ) -> list[StrategyDecision]:
        base = self._normalize(candles_15m)
        one_hour = self._normalize(candles_1h)
        four_hour = self._normalize(candles_4h)

        base = self.strategy.populate_indicators(base, {"pair": pair})
        one_hour = self.strategy.populate_indicators_1h(one_hour, {"pair": pair})
        four_hour = self.strategy.populate_indicators_4h(four_hour, {"pair": pair})

        merged = self._merge_informative(base, one_hour, minutes=60, prefix="")
        merged = self._merge_informative(merged, four_hour, minutes=240, prefix="")

        # Legacy V8/V9 strategies explicitly depend on BTC 4h for altcoin regime.
        # V10 deliberately has no such callback, so BTC data is not merged and
        # cannot influence its ETH/SOL decisions.
        btc_callback = getattr(self.strategy, "populate_indicators_btc_4h", None)
        if callable(btc_callback):
            btc = self._normalize(btc_4h)
            btc = btc_callback(btc, {"pair": "BTC/USDT"})
            merged = self._merge_informative(
                merged, btc, minutes=240, prefix="btc_"
            )

        merged = self.strategy.populate_entry_trend(merged, {"pair": pair})
        merged = self.strategy.populate_exit_trend(merged, {"pair": pair})

        start = decision_start.astimezone(UTC)
        end = decision_end.astimezone(UTC)
        feature_names = (
            "fresh_breakout_4h",
            "donchian_entry_4h",
            "breakout_24",
            "breakout_20",
            "breakout_16",
            "atr_4h",
            "adx_4h",
            "rsi_4h",
            "momentum_30d_4h",
            "ema_fast_rising_4h",
            "ema_exec_4h",
            "ema_fast_4h",
            "ema_slow_4h",
            "ema_exec_1h",
            "ema_fast_1h",
            "ema_slow_1h",
            "adx_1h",
            "rsi_1h",
            "ema_exec",
            "ema_fast",
            "atr_pct",
            "rsi",
            "adx",
            "volume",
            "volume_ratio",
            "btc_close_4h",
            "btc_ema_fast_4h",
            "btc_ema_slow_4h",
            "btc_ema_fast_rising_4h",
            "btc_momentum_30d_4h",
            "close_4h",
        )
        decisions: list[StrategyDecision] = []
        for _, row in merged.iterrows():
            candle_open = row["date"].to_pydatetime().astimezone(UTC)
            known_at = candle_open + timedelta(minutes=15)
            if known_at < start or known_at >= end:
                continue
            enter = bool(row.get("enter_long", 0) == 1)
            exit_long = bool(row.get("exit_long", 0) == 1)
            features: dict[str, Any] = {}
            for name in feature_names:
                value = row.get(name)
                if value is None:
                    continue
                try:
                    number = float(value)
                    if math.isfinite(number):
                        features[name] = number
                except (TypeError, ValueError):
                    features[name] = str(value)

            breakout = row.get("donchian_entry_4h")
            if breakout is None:
                for candidate in ("breakout_24", "breakout_20", "breakout_16"):
                    candidate_value = row.get(candidate)
                    if candidate_value is not None:
                        breakout = candidate_value
                        break
            breakout_value = self._finite_float(breakout)
            atr_value = self._finite_float(row.get("atr_4h"))
            close_4h = features.get("close_4h")
            if (
                breakout_value is not None
                and atr_value is not None
                and atr_value > 0
                and isinstance(close_4h, float)
            ):
                features["breakout_distance_atr"] = (
                    close_4h - breakout_value
                ) / atr_value

            btc_values = [
                features.get("btc_close_4h"),
                features.get("btc_ema_fast_4h"),
                features.get("btc_ema_slow_4h"),
                features.get("btc_ema_fast_rising_4h"),
                features.get("btc_momentum_30d_4h"),
            ]
            if all(isinstance(value, float) for value in btc_values):
                btc_close, btc_fast, btc_slow, btc_rising, btc_momentum = btc_values
                features["btc_regime_up"] = float(
                    btc_close > btc_fast > btc_slow
                    and btc_rising > 0
                    and btc_momentum > 0
                )

            decisions.append(
                StrategyDecision(
                    pair=pair,
                    candle_open=candle_open,
                    reference_price=float(row["close"]),
                    enter_long=enter,
                    exit_long=exit_long,
                    enter_tag=str(row.get("enter_tag")) if enter else None,
                    exit_tag=str(row.get("exit_tag")) if exit_long else None,
                    breakout_level=breakout_value,
                    atr_4h=atr_value,
                    features=features,
                )
            )
        return decisions

    def custom_exit(
        self, position: Position, when: datetime, rate: float, current_profit: float
    ) -> str | None:
        proxy = _ReplayTradeProxy(
            pair=position.pair,
            open_date_utc=position.opened_at,
            breakout_level=position.breakout_level,
            atr_4h=position.atr_4h,
        )
        result = self.strategy.custom_exit(
            pair=position.pair,
            trade=proxy,
            current_time=when,
            current_rate=rate,
            current_profit=current_profit,
        )
        return str(result) if result else None
