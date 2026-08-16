"""Cold-path contract for later Deep-Research strategy families.

This module is intentionally not wired into the live/paper V8 strategy. It
makes the future three-state regime architecture explicit and fail-closed while
keeping all current V8 trading decisions untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RegimeState(StrEnum):
    TREND_BREAKOUT = "TREND/BREAKOUT"
    RANGE_MEAN_REVERSION = "RANGE/MEAN_REVERSION"
    NO_TRADE = "NO_TRADE"


class StrategyFamily(StrEnum):
    V8_CHAMPION = "V8_CHAMPION"
    ORB_RETEST = "ORB_RETEST"
    ICHIMOKU_TREND = "ICHIMOKU_TREND"
    BOLLINGER_MR = "BOLLINGER_MR"
    NO_TRADE = "NO_TRADE"


TREND_FAMILIES = frozenset(
    {StrategyFamily.ORB_RETEST, StrategyFamily.ICHIMOKU_TREND}
)
RANGE_FAMILIES = frozenset({StrategyFamily.BOLLINGER_MR})


@dataclass(frozen=True, slots=True)
class RouteDecision:
    regime: RegimeState
    strategy_family: StrategyFamily
    allowed: bool
    reason: str


def route_research_strategy(
    regime: RegimeState,
    *,
    trend_family: StrategyFamily | None = None,
    range_family: StrategyFamily | None = None,
    data_healthy: bool = True,
    risk_allowed: bool = True,
) -> RouteDecision:
    """Return a deterministic research-route decision with NO_TRADE fallback.

    A missing or mismatched family never falls through to another strategy. The
    caller must explicitly provide the family pre-registered for the requested
    regime. This is a design contract for future challengers, not a live router.
    """

    if not data_healthy:
        return RouteDecision(regime, StrategyFamily.NO_TRADE, False, "data_unhealthy")
    if not risk_allowed:
        return RouteDecision(regime, StrategyFamily.NO_TRADE, False, "risk_reject")
    if regime is RegimeState.NO_TRADE:
        return RouteDecision(regime, StrategyFamily.NO_TRADE, False, "regime_no_trade")
    if regime is RegimeState.TREND_BREAKOUT:
        if trend_family not in TREND_FAMILIES:
            return RouteDecision(
                regime,
                StrategyFamily.NO_TRADE,
                False,
                "trend_family_not_registered",
            )
        return RouteDecision(regime, trend_family, True, "trend_route")
    if regime is RegimeState.RANGE_MEAN_REVERSION:
        if range_family not in RANGE_FAMILIES:
            return RouteDecision(
                regime,
                StrategyFamily.NO_TRADE,
                False,
                "range_family_not_registered",
            )
        return RouteDecision(regime, range_family, True, "range_route")
    return RouteDecision(regime, StrategyFamily.NO_TRADE, False, "unknown_regime")
