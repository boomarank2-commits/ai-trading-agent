from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from freqtrade.enums import CandleType

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

TEN_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "DOGE/USDT",
    "LINK/USDT",
    "TRX/USDT",
    "LTC/USDT",
    "BCH/USDT",
]


class _DataProvider:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame

    def get_analyzed_dataframe(self, pair: str, timeframe: str):
        del pair, timeframe
        return self.frame, None


class StrategyRuntimeGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.config = {
            "runmode": "live",
            "strategy": "CompressionBreakout250",
            "timeframe": "15m",
            "trading_mode": "spot",
            "candle_type_def": CandleType.SPOT,
            "margin_mode": "",
            "stake_currency": "USDT",
            "position_adjustment_enable": True,
            "max_entry_position_adjustment": 2,
            "max_open_trades": 3,
            "stake_amount": 80,
            "available_capital": 250,
            "force_entry_enable": False,
            "dry_run": False,
            "initial_state": "paused",
            "cancel_open_orders_on_exit": False,
            "exchange": {"name": "binance", "pair_whitelist": list(TEN_PAIRS)},
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

    def confirm(self, pair: str = "BTC/USDT") -> bool:
        return self.strategy.confirm_trade_entry(
            pair=pair,
            order_type="limit",
            amount=0.8,
            rate=100.0,
            time_in_force="GTC",
            current_time=datetime(2026, 8, 23, 8, tzinfo=UTC),
            entry_tag="test",
            side="long",
        )

    def test_stake_guard_caps_each_chunk_at_80(self) -> None:
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

    def test_initial_entry_guard_enforces_global_240_exposure_and_three_trades(self) -> None:
        with (
            patch.object(self.strategy, "_closed_profit_since", return_value=0.0),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=160.0),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=2),
        ):
            self.assertTrue(self.confirm("LINK/USDT"))

        with (
            patch.object(self.strategy, "_closed_profit_since", return_value=0.0),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=160.01),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=2),
        ):
            self.assertFalse(self.confirm("LINK/USDT"))

        with (
            patch.object(self.strategy, "_closed_profit_since", return_value=0.0),
            patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=80.0),
            patch.object(MODULE.Trade, "get_open_trade_count", return_value=3),
        ):
            self.assertFalse(self.confirm("LINK/USDT"))

    def _adjust_trade(self, *, entries: int, last_filled: datetime, open_stake: float, signal: int):
        signal_time = datetime(2026, 8, 23, 9, 15, tzinfo=UTC)
        self.strategy.dp = _DataProvider(
            pd.DataFrame([{"date": signal_time, "enter_long": signal}])
        )
        trade = SimpleNamespace(
            pair="LINK/USDT",
            has_open_orders=False,
            nr_of_successful_entries=entries,
            date_last_filled_utc=last_filled,
        )
        with patch.object(MODULE.Trade, "total_open_trades_stakes", return_value=open_stake):
            return self.strategy.adjust_trade_position(
                trade=trade,
                current_time=signal_time,
                current_rate=10.0,
                current_profit=0.0,
                min_stake=10.0,
                max_stake=90.0,
                current_entry_rate=10.0,
                current_exit_rate=10.0,
                current_entry_profit=0.0,
                current_exit_profit=0.0,
            )

    def test_same_pair_second_chunk_requires_a_new_signal_candle(self) -> None:
        result = self._adjust_trade(
            entries=1,
            last_filled=datetime(2026, 8, 23, 8, 45, tzinfo=UTC),
            open_stake=80.0,
            signal=1,
        )
        self.assertEqual(result, (80.0, "v12_17_link_new_signal_chunk"))

        self.assertIsNone(
            self._adjust_trade(
                entries=1,
                last_filled=datetime(2026, 8, 23, 9, 15, tzinfo=UTC),
                open_stake=80.0,
                signal=1,
            )
        )
        self.assertIsNone(
            self._adjust_trade(
                entries=1,
                last_filled=datetime(2026, 8, 23, 8, 45, tzinfo=UTC),
                open_stake=80.0,
                signal=0,
            )
        )

    def test_same_pair_adjustment_stops_after_three_chunks_or_240_global_exposure(self) -> None:
        last = datetime(2026, 8, 23, 8, 45, tzinfo=UTC)
        self.assertIsNone(self._adjust_trade(entries=3, last_filled=last, open_stake=160.0, signal=1))
        self.assertIsNone(self._adjust_trade(entries=1, last_filled=last, open_stake=160.01, signal=1))

    def test_entry_guard_rejects_weakened_adjustment_and_market_contract(self) -> None:
        for key, unsafe in (
            ("trading_mode", "futures"),
            ("margin_mode", "isolated"),
            ("max_open_trades", 4),
            ("stake_amount", 81),
            ("position_adjustment_enable", False),
            ("max_entry_position_adjustment", 3),
        ):
            with self.subTest(key=key, value=unsafe):
                original = self.strategy.config[key]
                self.strategy.config[key] = unsafe
                self.assertFalse(self.confirm())
                self.strategy.config[key] = original

    def test_bot_start_accepts_exact_ten_pair_contract(self) -> None:
        self.strategy.bot_start()
        self.strategy.config["exchange"]["pair_whitelist"] = TEN_PAIRS[:-1]
        with self.assertRaisesRegex(RuntimeError, "safety contract"):
            self.strategy.bot_start()

    def test_dryrun_freq_ui_is_allowed_only_on_localhost(self) -> None:
        self.strategy.config.update(
            {
                "runmode": "dry_run",
                "dry_run": True,
                "initial_state": "running",
                "cancel_open_orders_on_exit": True,
                "api_server": {
                    "enabled": True,
                    "listen_ip_address": "127.0.0.1",
                    "listen_port": 8080,
                    "enable_openapi": False,
                    "CORS_origins": [],
                },
            }
        )
        self.strategy.bot_start()
        self.strategy.config["api_server"]["listen_ip_address"] = "0.0.0.0"
        with self.assertRaisesRegex(RuntimeError, "safety contract"):
            self.strategy.bot_start()


if __name__ == "__main__":
    unittest.main()
