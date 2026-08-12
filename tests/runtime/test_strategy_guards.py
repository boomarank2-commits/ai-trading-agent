from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_PATH = (
    REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
)
SPEC = importlib.util.spec_from_file_location("compression_breakout_guard_test", STRATEGY_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CompressionBreakout250 = MODULE.CompressionBreakout250
CompressionBreakout250.__file__ = str(STRATEGY_PATH)


class StrategyRuntimeGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.config = {
            "runmode": "live",
            "strategy": "CompressionBreakout250",
            "timeframe": "15m",
            "trading_mode": "spot",
            "margin_mode": "",
            "stake_currency": "USDT",
            "position_adjustment_enable": False,
            "max_entry_position_adjustment": 0,
            "max_open_trades": 3,
            "stake_amount": 80,
            "available_capital": 250,
            "force_entry_enable": False,
            "dry_run": False,
            "initial_state": "paused",
            "cancel_open_orders_on_exit": False,
            "exchange": {
                "name": "binance",
                "pair_whitelist": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            },
            "order_types": {
                "entry": "limit",
                "exit": "limit",
                "force_exit": "market",
                "emergency_exit": "market",
                "stoploss": "limit",
                "stoploss_on_exchange": True,
                "stoploss_on_exchange_interval": 60,
                "stoploss_on_exchange_limit_ratio": 0.99,
            },
            "order_time_in_force": {"entry": "GTC", "exit": "GTC"},
            "unfilledtimeout": {
                "entry": 5,
                "exit": 5,
                "exit_timeout_count": 2,
                "unit": "minutes",
            },
            "api_server": {"enabled": False},
            "telegram": {"enabled": False},
            "user_data_dir": self.temporary.name,
        }
        self.strategy = CompressionBreakout250(self.config)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def confirm(self) -> bool:
        return self.strategy.confirm_trade_entry(
            pair="BTC/USDT",
            order_type="limit",
            amount=0.8,
            rate=100.0,
            time_in_force="GTC",
            current_time=datetime(2026, 8, 12, 12, tzinfo=UTC),
            entry_tag="test",
            side="long",
        )

    def test_stake_guard_caps_and_fails_closed(self) -> None:
        common = {
            "pair": "BTC/USDT",
            "current_time": datetime.now(UTC),
            "current_rate": 100.0,
            "min_stake": 10.0,
            "max_stake": 200.0,
            "entry_tag": None,
            "side": "long",
        }
        self.assertEqual(
            self.strategy.custom_stake_amount(
                proposed_stake=120.0, leverage=1.0, **common
            ),
            80.0,
        )
        self.assertEqual(
            self.strategy.custom_stake_amount(
                proposed_stake=120.0, leverage=2.0, **common
            ),
            0.0,
        )
        self.assertEqual(
            self.strategy.custom_stake_amount(
                proposed_stake="invalid", leverage=1.0, **common
            ),
            0.0,
        )

    def test_entry_guard_enforces_240_exposure_and_three_positions(self) -> None:
        with (
            patch.object(self.strategy, "_closed_profit_since", return_value=0.0),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=160.0),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=2),
        ):
            self.assertTrue(self.confirm())

        with (
            patch.object(self.strategy, "_closed_profit_since", return_value=0.0),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=160.01),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=2),
        ):
            self.assertFalse(self.confirm())

        with (
            patch.object(self.strategy, "_closed_profit_since", return_value=0.0),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=100.0),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=3),
        ):
            self.assertFalse(self.confirm())

    def test_entry_guard_rejects_overrides_kill_switch_and_state_errors(self) -> None:
        for key, unsafe in (
            ("trading_mode", "futures"),
            ("margin_mode", "isolated"),
            ("max_open_trades", -1),
            ("max_open_trades", 4),
            ("stake_amount", 81),
            ("position_adjustment_enable", True),
        ):
            with self.subTest(key=key, value=unsafe):
                original = self.strategy.config[key]
                self.strategy.config[key] = unsafe
                self.assertFalse(self.confirm())
                self.strategy.config[key] = original

        (Path(self.temporary.name) / "STOP_ENTRIES").touch()
        self.assertFalse(self.confirm())
        (Path(self.temporary.name) / "STOP_ENTRIES").unlink()

        with patch.object(
            self.strategy, "_closed_profit_since", side_effect=RuntimeError("db offline")
        ):
            self.assertFalse(self.confirm())

    def test_bot_start_accepts_contract_and_rejects_weakened_runtime(self) -> None:
        self.strategy.bot_start()

        unsafe_values = (
            ("trading_mode", "futures"),
            ("stake_amount", 81),
            ("available_capital", 251),
            ("max_open_trades", 4),
            ("initial_state", "running"),
            ("cancel_open_orders_on_exit", True),
        )
        for key, unsafe in unsafe_values:
            with self.subTest(key=key, value=unsafe):
                original = self.strategy.config[key]
                self.strategy.config[key] = unsafe
                with self.assertRaisesRegex(
                    RuntimeError, "safety contract|start paused|protection orders"
                ):
                    self.strategy.bot_start()
                self.strategy.config[key] = original

        original_stoploss = self.strategy.stoploss
        self.strategy.stoploss = -0.99
        with self.assertRaisesRegex(RuntimeError, "safety contract"):
            self.strategy.bot_start()
        self.strategy.stoploss = original_stoploss


if __name__ == "__main__":
    unittest.main()
