from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_PATH = (
    REPO_ROOT
    / "runtime"
    / "user_data"
    / "strategies"
    / "PaperTrendBreakout250V1.py"
)
SPEC = importlib.util.spec_from_file_location("paper_strategy_guard_test", STRATEGY_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PaperTrendBreakout250V1 = MODULE.PaperTrendBreakout250V1
PaperTrendBreakout250V1.__file__ = str(STRATEGY_PATH)


class PaperStrategyGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.config = {
            "runmode": "dry_run",
            "strategy": "PaperTrendBreakout250V1",
            "timeframe": "1h",
            "trading_mode": "spot",
            "margin_mode": "",
            "stake_currency": "USDT",
            "position_adjustment_enable": False,
            "max_entry_position_adjustment": 0,
            "max_open_trades": 3,
            "stake_amount": 80,
            "available_capital": 250,
            "force_entry_enable": False,
            "dry_run": True,
            "initial_state": "running",
            "cancel_open_orders_on_exit": True,
            "exchange": {
                "name": "binance",
                "pair_whitelist": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            },
            "order_types": dict(PaperTrendBreakout250V1.order_types),
            "order_time_in_force": {"entry": "GTC", "exit": "GTC"},
            "unfilledtimeout": {
                "entry": 5,
                "exit": 5,
                "exit_timeout_count": 2,
                "unit": "minutes",
            },
            "api_server": {
                "enabled": True,
                "listen_ip_address": "127.0.0.1",
                "listen_port": 8080,
                "enable_openapi": False,
                "CORS_origins": [],
            },
            "telegram": {"enabled": False},
            "user_data_dir": self.temporary.name,
        }
        self.strategy = PaperTrendBreakout250V1(self.config)

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

    def test_exact_paper_contract_starts_and_non_dry_run_is_impossible(self) -> None:
        self.strategy.bot_start()
        # Freqtrade 2026.7 converts minimal_roi's JSON keys to integers during
        # normal strategy resolution.  The runtime guard must accept that
        # semantically identical representation without weakening any value.
        self.strategy.minimal_roi = {
            int(minutes): profit
            for minutes, profit in self.strategy.minimal_roi.items()
        }
        self.strategy.bot_start()
        self.strategy.config.update(
            {"runmode": "live", "dry_run": False, "initial_state": "paused"}
        )
        with self.assertRaisesRegex(RuntimeError, "paper-only"):
            self.strategy.bot_start()
        self.assertFalse(self.confirm())

    def test_paper_entry_guard_caps_exposure_daily_loss_and_stake(self) -> None:
        with (
            patch.object(self.strategy, "_closed_profit_since", return_value=0.0),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=160.0),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=2),
        ):
            self.assertTrue(self.confirm())
        with (
            patch.object(self.strategy, "_closed_profit_since", return_value=-10.0),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=0.0),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=0),
        ):
            self.assertFalse(self.confirm())
        self.assertEqual(
            self.strategy.custom_stake_amount(
                "BTC/USDT",
                datetime.now(UTC),
                100.0,
                120.0,
                10.0,
                200.0,
                1.0,
                None,
                "long",
            ),
            80.0,
        )

    def test_missing_closed_profit_blocks_new_entry(self) -> None:
        with patch.object(
            MODULE.Trade,
            "get_trades_proxy",
            return_value=[SimpleNamespace(close_profit_abs=None)],
        ), self.assertRaisesRegex(RuntimeError, "no realized profit"):
            self.strategy._closed_profit_since(datetime(2026, 8, 12, tzinfo=UTC))

        with (
            patch.object(
                self.strategy,
                "_closed_profit_since",
                side_effect=RuntimeError("corrupt trade"),
            ),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=0.0),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=0),
        ):
            self.assertFalse(self.confirm())

    def test_shifted_donchian_and_exact_signal_hypothesis(self) -> None:
        rows = 230
        frame = pd.DataFrame(
            {
                "open": [100.0] * rows,
                "high": [101.0] * rows,
                "low": [99.0] * rows,
                "close": [100.0] * rows,
                "volume": [1000.0] * rows,
            }
        )
        frame.loc[rows - 1, ["open", "high", "low", "close", "volume"]] = [
            101.0,
            103.0,
            100.0,
            102.0,
            1300.0,
        ]
        indicators = self.strategy.populate_indicators(frame.copy(), {})
        self.assertEqual(indicators.loc[rows - 1, "breakout_high"], 101.0)
        self.assertEqual(indicators.loc[rows - 1, "volume_mean"], 1000.0)
        self.assertEqual(indicators.loc[rows - 1, "exit_low"], 99.0)

        signal = pd.DataFrame(
            {
                "open": [100.0] * 25,
                "close": [102.0] * 25,
                "volume": [1200.0] * 25,
                "breakout_high": [101.0] * 25,
                "ema_fast": [101.0] * 25,
                "ema_slow": [99.0] + [100.0] * 24,
                "adx": [20.0] * 25,
                "atr_pct": [0.01] * 25,
                "volume_ratio": [1.2] * 25,
            }
        )
        entered = self.strategy.populate_entry_trend(signal, {})
        self.assertEqual(entered.loc[24, "enter_long"], 1)

    def test_fixed_roi_stop_and_protections(self) -> None:
        self.assertEqual(
            self.strategy.minimal_roi,
            {
                "0": 0.08,
                "120": 0.08,
                "360": 0.08,
                "1440": 0.04,
                "4320": 0.0,
            },
        )
        self.assertEqual(self.strategy.stoploss, -0.055)
        self.assertEqual(
            [protection["method"] for protection in self.strategy.protections],
            ["CooldownPeriod", "StoplossGuard", "MaxDrawdown"],
        )


if __name__ == "__main__":
    unittest.main()
