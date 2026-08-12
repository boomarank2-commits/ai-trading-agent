from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from local_trader import (  # noqa: E402
    ALLOWED_TRANSITIONS,
    GateCriteria,
    Lifecycle,
    RiskPolicy,
    RiskPolicyError,
    ValidationError,
)


class LifecycleTests(unittest.TestCase):
    def test_complete_lifecycle_and_coercion(self) -> None:
        self.assertEqual(
            [state.value for state in Lifecycle],
            [
                "IDEA",
                "RESEARCH",
                "VALIDATED",
                "HOLDOUT_PASSED",
                "SHADOW",
                "PAPER",
                "CANARY",
                "PRODUCTION",
                "DEGRADED",
                "PAUSED",
            ],
        )
        self.assertIs(Lifecycle.coerce("holdout-passed"), Lifecycle.HOLDOUT_PASSED)
        self.assertIn(Lifecycle.RESEARCH, ALLOWED_TRANSITIONS[Lifecycle.IDEA])
        self.assertNotIn(Lifecycle.PRODUCTION, ALLOWED_TRANSITIONS[Lifecycle.IDEA])

    def test_unknown_lifecycle_fails(self) -> None:
        with self.assertRaises(ValidationError):
            Lifecycle.coerce("LIVE")


class RiskPolicyTests(unittest.TestCase):
    def test_safe_defaults_are_exact(self) -> None:
        policy = RiskPolicy()
        self.assertEqual(policy.exchange, "BINANCE")
        self.assertEqual(policy.market_type, "SPOT")
        self.assertEqual(policy.quote_asset, "USDT")
        self.assertEqual(policy.max_capital, 250.0)
        self.assertEqual(policy.max_position, 80.0)
        self.assertEqual(policy.max_exposure, 240.0)
        self.assertEqual(policy.max_open_positions, 3)
        self.assertEqual(policy.leverage, 1.0)
        self.assertFalse(policy.allow_shorts)
        self.assertFalse(policy.allow_dca)
        self.assertFalse(policy.allow_martingale)
        self.assertGreater(policy.max_daily_loss, 0)
        self.assertGreater(policy.max_drawdown, 0)

    def test_lower_limits_are_allowed(self) -> None:
        policy = RiskPolicy(
            max_capital=100,
            max_position=25,
            max_exposure=75,
            max_open_positions=2,
            max_daily_loss=5,
            max_drawdown=8,
        )
        self.assertEqual(policy.max_total_exposure, 75.0)

    def test_hard_limits_fail_closed(self) -> None:
        cases = [
            {"max_capital": 250.01},
            {"max_position": 80.01},
            {"max_exposure": 240.01},
            {"max_open_positions": 4},
            {"leverage": 2},
            {"allow_shorts": True},
            {"allow_dca": True},
            {"allow_martingale": True},
            {"max_daily_loss": 0},
            {"max_daily_loss": 10.01},
            {"max_drawdown": 0},
            {"max_drawdown": 15.01},
            {"market_type": "FUTURES"},
            {"quote_asset": "BUSD"},
            {"exchange": "BYBIT"},
        ]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(RiskPolicyError):
                RiskPolicy(**values)

    def test_policy_rejects_non_finite_and_boolean_numbers(self) -> None:
        for value in (float("nan"), float("inf"), True):
            with self.subTest(value=value), self.assertRaises(RiskPolicyError):
                RiskPolicy(max_capital=value)

    def test_from_dict_supports_clear_aliases_but_rejects_unknowns(self) -> None:
        policy = RiskPolicy.from_dict(
            {
                "max_position_notional": 50,
                "max_total_exposure": 150,
                "max_daily_loss_quote": 5,
                "max_drawdown_pct": 10,
            }
        )
        self.assertEqual(policy.max_position, 50.0)
        self.assertEqual(policy.max_exposure, 150.0)
        with self.assertRaises(RiskPolicyError):
            RiskPolicy.from_dict({"mystery_limit": 1})


class GateCriteriaTests(unittest.TestCase):
    def test_conservative_defaults(self) -> None:
        criteria = GateCriteria()
        self.assertEqual(criteria.min_trade_count, 100)
        self.assertEqual(criteria.min_profit_factor, 1.2)
        self.assertEqual(criteria.max_drawdown_pct, 15.0)
        self.assertGreaterEqual(criteria.min_symbols, 2)
        self.assertGreaterEqual(criteria.min_timeframes, 2)
        self.assertTrue(criteria.require_positive_holdout)

    def test_invalid_criteria_fail(self) -> None:
        for values in (
            {"min_trade_count": 99},
            {"min_profit_factor": 1.19},
            {"min_profit_factor": float("nan")},
            {"max_drawdown_pct": 15.01},
            {"min_symbols": 1},
            {"min_timeframes": 1},
            {"require_positive_holdout": 1},
            {"require_positive_holdout": False},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                GateCriteria(**values)


if __name__ == "__main__":
    unittest.main()
