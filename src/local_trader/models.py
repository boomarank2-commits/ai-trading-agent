"""Validated value objects used by the local trading registry."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, ClassVar

from .errors import RiskPolicyError, ValidationError


class Lifecycle(StrEnum):
    """A strategy version's complete research-to-production lifecycle."""

    IDEA = "IDEA"
    RESEARCH = "RESEARCH"
    VALIDATED = "VALIDATED"
    HOLDOUT_PASSED = "HOLDOUT_PASSED"
    SHADOW = "SHADOW"
    PAPER = "PAPER"
    CANARY = "CANARY"
    PRODUCTION = "PRODUCTION"
    DEGRADED = "DEGRADED"
    PAUSED = "PAUSED"

    @classmethod
    def coerce(cls, value: Lifecycle | str) -> Lifecycle:
        if isinstance(value, cls):
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("lifecycle must be a non-empty string")
        normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
        try:
            return cls(normalized)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in cls)
            raise ValidationError(
                f"unknown lifecycle {value!r}; expected one of: {allowed}"
            ) from exc


# Every state change is explicit. Safety transitions are intentionally broad,
# while capital-increasing transitions remain strictly one step at a time.
ALLOWED_TRANSITIONS: dict[Lifecycle, frozenset[Lifecycle]] = {
    Lifecycle.IDEA: frozenset({Lifecycle.RESEARCH, Lifecycle.PAUSED}),
    Lifecycle.RESEARCH: frozenset({Lifecycle.VALIDATED, Lifecycle.PAUSED}),
    Lifecycle.VALIDATED: frozenset(
        {Lifecycle.HOLDOUT_PASSED, Lifecycle.RESEARCH, Lifecycle.PAUSED}
    ),
    Lifecycle.HOLDOUT_PASSED: frozenset(
        {Lifecycle.SHADOW, Lifecycle.RESEARCH, Lifecycle.PAUSED}
    ),
    Lifecycle.SHADOW: frozenset(
        {Lifecycle.PAPER, Lifecycle.DEGRADED, Lifecycle.PAUSED}
    ),
    Lifecycle.PAPER: frozenset(
        {Lifecycle.CANARY, Lifecycle.DEGRADED, Lifecycle.PAUSED}
    ),
    Lifecycle.CANARY: frozenset(
        {Lifecycle.PRODUCTION, Lifecycle.DEGRADED, Lifecycle.PAUSED}
    ),
    Lifecycle.PRODUCTION: frozenset({Lifecycle.DEGRADED, Lifecycle.PAUSED}),
    Lifecycle.DEGRADED: frozenset({Lifecycle.RESEARCH, Lifecycle.PAUSED}),
    Lifecycle.PAUSED: frozenset({Lifecycle.RESEARCH}),
}

MANUAL_APPROVAL_STATES = frozenset({Lifecycle.CANARY, Lifecycle.PRODUCTION})
METRICS_GATED_STATES = frozenset(
    {
        Lifecycle.VALIDATED,
        Lifecycle.HOLDOUT_PASSED,
        Lifecycle.SHADOW,
        Lifecycle.PAPER,
        Lifecycle.CANARY,
        Lifecycle.PRODUCTION,
    }
)
HOLDOUT_REQUIRED_STATES = frozenset(
    {
        Lifecycle.HOLDOUT_PASSED,
        Lifecycle.SHADOW,
        Lifecycle.PAPER,
        Lifecycle.CANARY,
        Lifecycle.PRODUCTION,
    }
)
SAFETY_STATES = frozenset({Lifecycle.DEGRADED, Lifecycle.PAUSED})


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValidationError(f"{name} must be a finite number")
    return converted


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Hard, deterministic Binance Spot risk limits.

    Values below the hard ceilings are accepted; values above them are never
    accepted.  Feature flags are deny-only so configuration mistakes cannot
    silently enable leverage, shorts, DCA, or martingale behavior.
    """

    exchange: str = "BINANCE"
    market_type: str = "SPOT"
    quote_asset: str = "USDT"
    max_capital: float = 250.0
    max_position: float = 80.0
    max_exposure: float = 240.0
    max_open_positions: int = 3
    leverage: float = 1.0
    allow_shorts: bool = False
    allow_dca: bool = False
    allow_martingale: bool = False
    max_daily_loss: float = 10.0
    max_drawdown: float = 15.0

    HARD_MAX_CAPITAL: ClassVar[float] = 250.0
    HARD_MAX_POSITION: ClassVar[float] = 80.0
    HARD_MAX_EXPOSURE: ClassVar[float] = 240.0
    HARD_MAX_OPEN_POSITIONS: ClassVar[int] = 3

    def __post_init__(self) -> None:
        for field_name, expected in (
            ("exchange", "BINANCE"),
            ("market_type", "SPOT"),
            ("quote_asset", "USDT"),
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or value.strip().upper() != expected:
                raise RiskPolicyError(f"{field_name} must be exactly {expected}")
            object.__setattr__(self, field_name, expected)

        capital = self._positive("max_capital", self.max_capital)
        position = self._positive("max_position", self.max_position)
        exposure = self._positive("max_exposure", self.max_exposure)
        leverage = self._positive("leverage", self.leverage)
        daily_loss = self._positive("max_daily_loss", self.max_daily_loss)
        drawdown = self._positive("max_drawdown", self.max_drawdown)

        if capital > self.HARD_MAX_CAPITAL:
            raise RiskPolicyError("max_capital cannot exceed 250 USDT")
        if position > self.HARD_MAX_POSITION:
            raise RiskPolicyError("max_position cannot exceed 80 USDT")
        if position > capital:
            raise RiskPolicyError("max_position cannot exceed max_capital")
        if exposure > self.HARD_MAX_EXPOSURE:
            raise RiskPolicyError("max_exposure cannot exceed 240 USDT")
        if exposure > capital:
            raise RiskPolicyError("max_exposure cannot exceed max_capital")
        if type(self.max_open_positions) is not int or not (
            1 <= self.max_open_positions <= self.HARD_MAX_OPEN_POSITIONS
        ):
            raise RiskPolicyError("max_open_positions must be an integer from 1 to 3")
        if leverage != 1.0:
            raise RiskPolicyError("leverage must be exactly 1 for Spot trading")
        if daily_loss > capital:
            raise RiskPolicyError("max_daily_loss cannot exceed max_capital")
        if daily_loss > 10.0:
            raise RiskPolicyError("max_daily_loss cannot exceed 10 USDT")
        if drawdown > 15.0:
            raise RiskPolicyError("max_drawdown cannot exceed 15 percent")

        for field_name in ("allow_shorts", "allow_dca", "allow_martingale"):
            value = getattr(self, field_name)
            if type(value) is not bool:
                raise RiskPolicyError(f"{field_name} must be a boolean")
            if value:
                raise RiskPolicyError(f"{field_name} must remain false")

        # Store normalized floats even when integer literals were supplied.
        object.__setattr__(self, "max_capital", capital)
        object.__setattr__(self, "max_position", position)
        object.__setattr__(self, "max_exposure", exposure)
        object.__setattr__(self, "leverage", leverage)
        object.__setattr__(self, "max_daily_loss", daily_loss)
        object.__setattr__(self, "max_drawdown", drawdown)

    @staticmethod
    def _positive(name: str, value: Any) -> float:
        try:
            number = _finite_number(name, value)
        except ValidationError as exc:
            raise RiskPolicyError(str(exc)) from exc
        if number <= 0:
            raise RiskPolicyError(f"{name} must be positive")
        return number

    @property
    def max_position_notional(self) -> float:
        return self.max_position

    @property
    def max_total_exposure(self) -> float:
        return self.max_exposure

    @property
    def max_leverage(self) -> float:
        return self.leverage

    @property
    def max_daily_loss_quote(self) -> float:
        return self.max_daily_loss

    @property
    def max_drawdown_pct(self) -> float:
        return self.max_drawdown

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> RiskPolicy:
        if not isinstance(values, Mapping):
            raise RiskPolicyError("risk policy must be a JSON object")
        aliases = {
            "venue": "exchange",
            "max_position_notional": "max_position",
            "max_total_exposure": "max_exposure",
            "max_leverage": "leverage",
            "shorts_enabled": "allow_shorts",
            "dca_enabled": "allow_dca",
            "martingale_enabled": "allow_martingale",
            "max_daily_loss_quote": "max_daily_loss",
            "max_account_drawdown_pct": "max_drawdown",
            "max_drawdown_pct": "max_drawdown",
        }
        fields = {
            "exchange",
            "market_type",
            "quote_asset",
            "max_capital",
            "max_position",
            "max_exposure",
            "max_open_positions",
            "leverage",
            "allow_shorts",
            "allow_dca",
            "allow_martingale",
            "max_daily_loss",
            "max_drawdown",
        }
        normalized: dict[str, Any] = {}
        for raw_key, value in values.items():
            if not isinstance(raw_key, str):
                raise RiskPolicyError("risk policy keys must be strings")
            key = aliases.get(raw_key, raw_key)
            if key not in fields:
                raise RiskPolicyError(f"unknown risk policy field: {raw_key}")
            if key in normalized:
                raise RiskPolicyError(f"duplicate risk policy field: {key}")
            normalized[key] = value
        return cls(**normalized)


@dataclass(frozen=True, slots=True)
class GateCriteria:
    """Configurable, conservative promotion thresholds."""

    min_trade_count: int = 100
    min_profit_factor: float = 1.2
    max_drawdown_pct: float = 15.0
    min_symbols: int = 2
    min_timeframes: int = 2
    require_positive_holdout: bool = True

    def __post_init__(self) -> None:
        if type(self.min_trade_count) is not int or self.min_trade_count < 100:
            raise ValidationError("min_trade_count cannot be lower than 100")
        profit_factor = _finite_number("min_profit_factor", self.min_profit_factor)
        drawdown = _finite_number("max_drawdown_pct", self.max_drawdown_pct)
        if profit_factor < 1.2:
            raise ValidationError("min_profit_factor cannot be lower than 1.2")
        if not 0 < drawdown <= 15:
            raise ValidationError(
                "max_drawdown_pct must be greater than 0 and cannot exceed 15"
            )
        if type(self.min_symbols) is not int or self.min_symbols < 2:
            raise ValidationError("min_symbols cannot be lower than 2")
        if type(self.min_timeframes) is not int or self.min_timeframes < 2:
            raise ValidationError("min_timeframes cannot be lower than 2")
        if type(self.require_positive_holdout) is not bool:
            raise ValidationError("require_positive_holdout must be a boolean")
        if not self.require_positive_holdout:
            raise ValidationError("require_positive_holdout cannot be disabled")
        object.__setattr__(self, "min_profit_factor", profit_factor)
        object.__setattr__(self, "max_drawdown_pct", drawdown)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> GateCriteria:
        if not isinstance(values, Mapping):
            raise ValidationError("gate criteria must be a JSON object")
        fields = {
            "min_trade_count",
            "min_profit_factor",
            "max_drawdown_pct",
            "min_symbols",
            "min_timeframes",
            "require_positive_holdout",
        }
        unknown = set(values) - fields
        if unknown:
            raise ValidationError(
                "unknown gate criteria field(s): " + ", ".join(sorted(map(str, unknown)))
            )
        return cls(**dict(values))


@dataclass(frozen=True, slots=True)
class GateDecision:
    """A serializable explanation of a deterministic gate decision."""

    eligible: bool
    from_state: Lifecycle
    to_state: Lifecycle
    failures: tuple[str, ...]
    evidence: Mapping[str, Any]
    manual_approval_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "failures": list(self.failures),
            "evidence": dict(self.evidence),
            "manual_approval_required": self.manual_approval_required,
        }
