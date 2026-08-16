"""Value objects and contracts for the deterministic V8 replay."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

PAIRS = ("BTC/USDT", "ETH/USDT", "SOL/USDT")


def utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def iso(value: datetime) -> str:
    return utc(value).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class MinuteBar:
    pair: str
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        if self.pair not in PAIRS:
            raise ValueError(f"unsupported pair: {self.pair}")
        object.__setattr__(self, "open_time", utc(self.open_time))
        for name in ("open", "high", "low", "close", "volume"):
            number = float(getattr(self, name))
            if not math.isfinite(number) or number < 0:
                raise ValueError(f"invalid {name}: {number!r}")
            object.__setattr__(self, name, number)
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high is below another OHLC value")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low is above another OHLC value")

    @property
    def close_time(self) -> datetime:
        return self.open_time + timedelta(minutes=1)


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    """One exact-strategy decision known at a completed 15m candle close."""

    pair: str
    candle_open: datetime
    reference_price: float
    enter_long: bool = False
    exit_long: bool = False
    enter_tag: str | None = None
    exit_tag: str | None = None
    breakout_level: float | None = None
    atr_4h: float | None = None
    features: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.pair not in PAIRS:
            raise ValueError(f"unsupported pair: {self.pair}")
        object.__setattr__(self, "candle_open", utc(self.candle_open))
        price = float(self.reference_price)
        if not math.isfinite(price) or price <= 0:
            raise ValueError("reference_price must be positive and finite")
        object.__setattr__(self, "reference_price", price)
        if self.breakout_level is not None:
            object.__setattr__(self, "breakout_level", float(self.breakout_level))
        if self.atr_4h is not None:
            object.__setattr__(self, "atr_4h", float(self.atr_4h))

    @property
    def known_at(self) -> datetime:
        return self.candle_open + timedelta(minutes=15)


@dataclass(slots=True)
class PendingOrder:
    order_id: str
    pair: str
    side: str
    kind: str
    requested_at: datetime
    limit_price: float
    expires_at: datetime
    timeout_count: int = 0
    stake: float = 0.0
    decision_candle_open: datetime | None = None
    enter_tag: str | None = None
    breakout_level: float | None = None
    atr_4h: float | None = None
    filled_stake: float = 0.0
    filled_amount: float = 0.0
    target_amount: float = 0.0
    cancel_reject_count: int = 0

    @property
    def remaining_stake(self) -> float:
        return max(0.0, self.stake - self.filled_stake)

    @property
    def remaining_amount(self) -> float:
        return max(0.0, self.target_amount - self.filled_amount)


@dataclass(slots=True)
class Position:
    trade_id: str
    pair: str
    opened_at: datetime
    entry_price: float
    stake: float
    amount: float
    entry_fee: float
    enter_tag: str | None
    breakout_level: float | None
    atr_4h: float | None
    highest_rate: float
    lowest_rate: float
    entry_order_id: str | None = None
    initial_stake: float = 0.0
    initial_amount: float = 0.0
    exit_value_accumulated: float = 0.0
    exit_fee_accumulated: float = 0.0
    exit_amount_accumulated: float = 0.0

    @property
    def stop_price(self) -> float:
        return self.entry_price * (1.0 - 0.055)

    @property
    def roi_price(self) -> float:
        # runtime config intentionally overrides the strategy class ROI with 50%.
        return self.entry_price * 1.50


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    trade_id: str
    pair: str
    opened_at: datetime
    closed_at: datetime
    entry_price: float
    exit_price: float
    stake: float
    amount: float
    entry_fee: float
    exit_fee: float
    pnl_abs: float
    pnl_ratio: float
    exit_reason: str
    enter_tag: str | None
    duration_minutes: int
    mae_ratio: float
    mfe_ratio: float


@dataclass(frozen=True, slots=True)
class RiskDecision:
    allowed: bool
    reason: str


@dataclass(slots=True)
class ReplayPolicy:
    start_capital: float = 250.0
    stake_amount: float = 80.0
    max_total_exposure: float = 240.0
    max_open_positions: int = 3
    max_daily_loss: float = 10.0
    fee_per_side: float = 0.002
    slippage_bps: float = 0.0
    spread_bps: float = 0.0
    execution_delay_minutes: int = 0
    fill_fraction_per_touch: float = 1.0
    cancel_rejects_before_cancel: int = 0
    entry_timeout_minutes: int = 5
    exit_timeout_minutes: int = 5
    exit_timeout_count: int = 2
    cooldown_minutes: int = 30
    stoploss_guard_lookback_hours: int = 24
    stoploss_guard_trade_limit: int = 2
    stoploss_guard_block_hours: int = 6
    maxdd_lookback_hours: int = 48
    maxdd_trade_limit: int = 3
    maxdd_threshold: float = 0.08
    maxdd_block_hours: int = 12

    def __post_init__(self) -> None:
        if not (0 < self.start_capital <= 250):
            raise ValueError("start_capital must be in (0, 250]")
        if not (0 < self.stake_amount <= 80):
            raise ValueError("stake_amount must be in (0, 80]")
        if not (0 < self.max_total_exposure <= 240):
            raise ValueError("max_total_exposure must be in (0, 240]")
        if not (1 <= self.max_open_positions <= 3):
            raise ValueError("max_open_positions must be in [1, 3]")
        if not (0 <= self.fee_per_side < 0.05):
            raise ValueError("fee_per_side out of range")
        if not (0 <= self.slippage_bps <= 1_000):
            raise ValueError("slippage_bps must be in [0, 1000]")
        if not (0 <= self.spread_bps <= 1_000):
            raise ValueError("spread_bps must be in [0, 1000]")
        if not (0 <= self.execution_delay_minutes <= 60):
            raise ValueError("execution_delay_minutes must be in [0, 60]")
        if not (0 < self.fill_fraction_per_touch <= 1.0):
            raise ValueError("fill_fraction_per_touch must be in (0, 1]")
        if not (0 <= self.cancel_rejects_before_cancel <= 10):
            raise ValueError("cancel_rejects_before_cancel must be in [0, 10]")
        if not (0 < self.max_daily_loss <= 10):
            raise ValueError("max_daily_loss must be in (0, 10]")


class ReplaySink:
    """Minimal event sink protocol implemented by :mod:`replay_telemetry`."""

    def decision(self, payload: Mapping[str, Any]) -> None:  # pragma: no cover - protocol
        del payload

    def event(self, payload: Mapping[str, Any]) -> None:  # pragma: no cover - protocol
        del payload

    def error(self, payload: Mapping[str, Any]) -> None:  # pragma: no cover - protocol
        del payload

    def equity(self, payload: Mapping[str, Any]) -> None:  # pragma: no cover - protocol
        del payload


class NullSink(ReplaySink):
    pass


@dataclass(slots=True)
class ReplayState:
    now: datetime
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    orders: dict[str, PendingOrder] = field(default_factory=dict)
    closed_trades: list[ClosedTrade] = field(default_factory=list)
    pair_cooldown_until: dict[str, datetime] = field(default_factory=dict)
    stoploss_guard_until: datetime | None = None
    maxdd_guard_until: datetime | None = None
    kill_switch: bool = False
    data_healthy: bool = True
    last_prices: dict[str, float] = field(default_factory=dict)
    last_minute_close_time: datetime | None = None
    last_minute_fingerprint: str | None = None
    sequence: int = 0


CustomExit = Callable[[Position, datetime, float, float], str | None]
