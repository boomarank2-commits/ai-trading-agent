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


class HixtonCleanResetContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.strategy_text = STRATEGY.read_text(encoding="utf-8")
        cls.adapter_text = ADAPTER.read_text(encoding="utf-8")
        cls.base_text = BASE_API.read_text(encoding="utf-8")
        cls.ui_text = UI.read_text(encoding="utf-8")
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_strategy_is_exact_hixton_baseline_not_v1233_routes(self) -> None:
        required = (
            'STRATEGY_VERSION = "HIXTON-V1"',
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
        )
        for marker in required:
            self.assertIn(marker, self.strategy_text)
        for forbidden in (
            "PAIR_PROFILES", "PYRAMIDING_PAIRS", "DONCHIAN_TREND",
            "TREND_RECLAIM", "Supertrend20", "EMA30/EMA80",
        ):
            self.assertNotIn(forbidden, self.strategy_text)

    def test_strategy_hash_matches_isolated_trial_ledger(self) -> None:
        digest = hashlib.sha256(STRATEGY.read_bytes()).hexdigest()
        with TRIAL.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["experiment_id"], "HIXTON-V1-ORIGINAL-BASELINE")
        self.assertEqual(rows[0]["strategy_hash"], digest)
        self.assertEqual(rows[0]["parameter_hash"], "vidya10_mom20_sma15_atr200_x2")

    def test_execution_contract_is_250_wallet_with_three_80_slots(self) -> None:
        cfg = self.config
        self.assertEqual(cfg["strategy"], "CompressionBreakout250")
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
        self.assertIn("Alle 10 + 3×80 Portfolio testen", self.ui_text)
        self.assertIn("TARGET_PER_DAY = 2.40", self.ui_text)
        self.assertIn("Die zehn Einzelgewinne werden ausdrücklich nicht", self.ui_text)

    def test_duplicate_governance_is_isolated_from_v1233_history(self) -> None:
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
