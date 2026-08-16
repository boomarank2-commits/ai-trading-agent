from __future__ import annotations

import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from research_strategy_contract import (
    RegimeState,
    StrategyFamily,
    route_research_strategy,
)


def test_no_trade_is_default_for_uncertain_or_unhealthy_state() -> None:
    no_regime = route_research_strategy(RegimeState.NO_TRADE)
    assert not no_regime.allowed
    assert no_regime.strategy_family is StrategyFamily.NO_TRADE

    unhealthy = route_research_strategy(
        RegimeState.TREND_BREAKOUT,
        trend_family=StrategyFamily.ORB_RETEST,
        data_healthy=False,
    )
    assert not unhealthy.allowed
    assert unhealthy.strategy_family is StrategyFamily.NO_TRADE

    risk_reject = route_research_strategy(
        RegimeState.RANGE_MEAN_REVERSION,
        range_family=StrategyFamily.BOLLINGER_MR,
        risk_allowed=False,
    )
    assert not risk_reject.allowed
    assert risk_reject.strategy_family is StrategyFamily.NO_TRADE


def test_orb_and_ichimoku_remain_separate_registered_trend_families() -> None:
    orb = route_research_strategy(
        RegimeState.TREND_BREAKOUT,
        trend_family=StrategyFamily.ORB_RETEST,
    )
    ichimoku = route_research_strategy(
        RegimeState.TREND_BREAKOUT,
        trend_family=StrategyFamily.ICHIMOKU_TREND,
    )
    assert orb.allowed and orb.strategy_family is StrategyFamily.ORB_RETEST
    assert ichimoku.allowed and ichimoku.strategy_family is StrategyFamily.ICHIMOKU_TREND


def test_family_mismatch_fails_closed_instead_of_falling_through() -> None:
    wrong_trend = route_research_strategy(
        RegimeState.TREND_BREAKOUT,
        trend_family=StrategyFamily.BOLLINGER_MR,
    )
    wrong_range = route_research_strategy(
        RegimeState.RANGE_MEAN_REVERSION,
        range_family=StrategyFamily.ORB_RETEST,
    )
    assert not wrong_trend.allowed
    assert wrong_trend.strategy_family is StrategyFamily.NO_TRADE
    assert wrong_trend.reason == "trend_family_not_registered"
    assert not wrong_range.allowed
    assert wrong_range.strategy_family is StrategyFamily.NO_TRADE
    assert wrong_range.reason == "range_family_not_registered"
