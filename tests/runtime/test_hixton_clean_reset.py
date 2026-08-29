from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
CONFIG = ROOT / "runtime" / "user_data" / "config.json"
ADAPTER = ROOT / "runtime" / "ten_pair_backtest_api.py"
BASE_API = ROOT / "runtime" / "testbot_backtest_api.py"
UI = ROOT / "runtime" / "ui" / "testbot-backtest.js"
TRIAL = ROOT / "research" / "hixton_trial_ledger.csv"
EXECUTED = ROOT / "research" / "hixton_executed_test_fingerprints.csv"
VALIDATOR = ROOT / "runtime" / "validate_dryrun_config.py"

EXPECTED_PAIRS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT",
    "DOGE/USDT", "LINK/USDT", "TRX/USDT", "LTC/USDT", "BCH/USDT",
]


class HixtonV5Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.strategy_text = STRATEGY.read_text(encoding="utf-8")
        cls.adapter_text = ADAPTER.read_text(encoding="utf-8")
        cls.base_text = BASE_API.read_text(encoding="utf-8")
        cls.ui_text = UI.read_text(encoding="utf-8")
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_strategy_keeps_original_hixton_motor(self) -> None:
        required = (
            'STRATEGY_VERSION = "HIXTON-V5"',
            "length=10, momentum_length=20",
            "_pine_sma_ignore_na(raw_vidya, length=15)",
            "_pine_atr(dataframe, length=200)",
            "alpha = 1.0 / length",
            "upper = vidya + atr * 2.0",
            "lower = vidya - atr * 2.0",
            '"hixton_flip_up"',
            '"hixton_flip_down"',
            "position_adjustment_enable = False",
            "max_entry_position_adjustment = 0",
            "use_custom_stoploss = False",
        )
        for marker in required:
            self.assertIn(marker, self.strategy_text)
        for forbidden in (
            "PROFIT_FLOOR_TRIGGER", "custom_stoploss(", "stoploss_from_absolute",
            "stoploss_from_open", "hixton_midline_cross_down", "hixton_midline_guard",
            "PYRAMIDING_PAIRS", "DONCHIAN_TREND", "TREND_RECLAIM",
        ):
            self.assertNotIn(forbidden, self.strategy_text)

    def test_v5_has_exact_three_route_groups(self) -> None:
        required = (
            'V3A_CONTROL_PAIRS: ClassVar[frozenset[str]]',
            '{"ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "LINK/USDT", "TRX/USDT"}',
            'FOUR_HOUR_GUARD_PAIRS: ClassVar[frozenset[str]]',
            '{"BTC/USDT", "BNB/USDT"}',
            'ONE_HOUR_ROUTE_PAIRS: ClassVar[frozenset[str]]',
            '{"LTC/USDT", "BCH/USDT"}',
            '@informative("1h")', '@informative("4h")',
            'dataframe["hixton_vidya_rising"] = (',
            'four_hour_guard = four_hour_bullish & four_hour_rising',
            'one_hour_flip_up_event = _first_forward_filled_true(',
            '"hixton_1h_flip_up_4h_guard"',
            '"hixton_15m_flip_up_1h_4h_guard"',
            '"hixton_15m_flip_up_1h_guard"',
            '"hixton_1h_flip_down"',
            '"hixton_15m_flip_down"',
        )
        for marker in required:
            self.assertIn(marker, self.strategy_text)
        self.assertNotIn('if pair == "ETH/USDT"', self.strategy_text)

    def test_current_strategy_hash_has_exact_v5_trial_entry(self) -> None:
        digest = hashlib.sha256(STRATEGY.read_bytes()).hexdigest()
        with TRIAL.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        matching = [row for row in rows if row["strategy_hash"] == digest]
        self.assertEqual(len(matching), 1, f"unregistered strategy sha256: {digest}")
        self.assertEqual(matching[0]["experiment_id"], "HIXTON-V5-PAIR-ROUTES")
        self.assertEqual(matching[0]["strategy_version"], "HIXTON-V5")
        self.assertEqual(
            matching[0]["parameter_hash"],
            "v3a_controls_btc_bnb_4h_ltc_bch_1h_routes",
        )
        self.assertEqual(matching[0]["status"], "PREREGISTERED_PENDING_BACKTEST")

    def test_execution_contract_is_250_wallet_with_three_80_slots(self) -> None:
        cfg = self.config
        self.assertEqual(cfg["strategy"], "CompressionBreakout250")
        self.assertEqual(cfg["bot_name"], "hixton-v5-ten-pair-250-dryrun")
        self.assertEqual(cfg["stake_currency"], "USDT")
        self.assertEqual(cfg["stake_amount"], 80)
        self.assertEqual(cfg["available_capital"], 250)
        self.assertEqual(cfg["dry_run_wallet"], 250)
        self.assertEqual(cfg["max_open_trades"], 3)
        self.assertEqual(cfg["stake_amount"] * cfg["max_open_trades"], 240)
        self.assertFalse(cfg["position_adjustment_enable"])
        self.assertEqual(cfg["max_entry_position_adjustment"], 0)
        self.assertTrue(cfg["dry_run"])
        self.assertEqual(cfg["trading_mode"], "spot")
        self.assertEqual(cfg["exchange"]["pair_whitelist"], EXPECTED_PAIRS)

    def test_data_download_contract_keeps_all_required_timeframes_and_warmup(self) -> None:
        self.assertIn('REQUIRED_TIMEFRAMES = ("15m", "1m", "1h", "4h")', self.base_text)
        self.assertIn("BACKTEST_WARMUP_DAYS = 75", self.base_text)
        self.assertIn('"download-data"', self.base_text)
        self.assertIn('"--prepend"', self.base_text)
        self.assertIn("_validate_candle_data", self.adapter_text)
        self.assertIn("unlink(missing_ok=True)", self.adapter_text)
        self.assertIn("Marktdaten", self.adapter_text)

    def test_big_button_runs_ten_individuals_then_shared_portfolio(self) -> None:
        self.assertIn("_run_individual_cases()", self.adapter_text)
        self.assertIn("_run_shared_portfolio()", self.adapter_text)
        self.assertIn("base.PORTFOLIO_TARGET", self.adapter_text)
        self.assertIn("portfolio_result", self.adapter_text)
        self.assertIn('base.STRATEGY_VERSION = "HIXTON-V5"', self.adapter_text)
        self.assertIn('ACTIVE_EXPERIMENT_ID = "HIXTON-V5-PAIR-ROUTES"', self.adapter_text)
        self.assertIn("Alle 10 + 3×80 Portfolio testen", self.ui_text)
        self.assertIn("Hixton V5 Pair Routes", self.ui_text)
        self.assertIn("TARGET_PER_DAY = 2.40", self.ui_text)
        self.assertIn("V3A-Kontrollen", self.ui_text)

    def test_duplicate_governance_stays_isolated_from_v1233_history(self) -> None:
        self.assertIn('"hixton_trial_ledger.csv"', self.adapter_text)
        self.assertIn('"hixton_executed_test_fingerprints.csv"', self.adapter_text)
        with EXECUTED.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows, [])

    def test_python_and_javascript_syntax(self) -> None:
        for path in (STRATEGY, ADAPTER, VALIDATOR):
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        node = subprocess.run(
            ["node", "--check", str(UI)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(node.returncode, 0, node.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
