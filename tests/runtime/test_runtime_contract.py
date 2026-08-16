from __future__ import annotations

import ast
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from local_trader import RiskPolicy
from runtime.generate_deployment_manifest import generate
from runtime.validate_runtime import validate

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = REPO_ROOT / "runtime"
USER_DATA = RUNTIME / "user_data"
CONFIG_PATH = USER_DATA / "config.json"
LIVE_OVERLAY_PATH = USER_DATA / "config-live.example.json"
PUBLIC_OVERLAY_PATH = USER_DATA / "config-public.json"
ANALYSIS_OVERLAY_PATH = USER_DATA / "config-analysis.json"
STRATEGY_PATH = USER_DATA / "strategies" / "CompressionBreakout250.py"

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def class_node(tree: ast.Module, name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"Class {name!r} not found")


def literal_class_assignment(cls: ast.ClassDef, name: str):
    for node in cls.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"Class assignment {name!r} not found")


def numeric_literal(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
    ):
        return -float(node.operand.value)
    return None


class RuntimeConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG_PATH)
        cls.live = load_json(LIVE_OVERLAY_PATH)
        cls.public = load_json(PUBLIC_OVERLAY_PATH)
        cls.analysis = load_json(ANALYSIS_OVERLAY_PATH)

    def test_dryrun_capital_and_spot_contract(self) -> None:
        config = self.config
        self.assertIs(config["dry_run"], True)
        self.assertEqual(config["dry_run_wallet"], 250)
        self.assertEqual(config["available_capital"], 250)
        self.assertEqual(config["stake_amount"], 80)
        self.assertEqual(config["max_open_trades"], 3)
        self.assertLessEqual(config["stake_amount"] * config["max_open_trades"], 250)
        self.assertEqual(config["stake_currency"], "USDT")
        self.assertEqual(config["trading_mode"], "spot")
        self.assertEqual(config["margin_mode"], "")
        self.assertIs(config["position_adjustment_enable"], False)
        self.assertEqual(config["max_entry_position_adjustment"], 0)

    def test_binance_static_allowlist_only(self) -> None:
        exchange = self.config["exchange"]
        self.assertEqual(exchange["name"], "binance")
        self.assertEqual(exchange["pair_whitelist"], PAIRS)
        self.assertEqual(exchange["pair_blacklist"], [])
        self.assertEqual(self.config["pairlists"], [{"method": "StaticPairList"}])
        self.assertEqual(exchange["ccxt_config"]["options"]["defaultType"], "spot")
        self.assertEqual(exchange["ccxt_async_config"]["options"]["defaultType"], "spot")

    def test_starts_stopped_with_local_disabled_api(self) -> None:
        self.assertEqual(self.config["initial_state"], "stopped")
        self.assertIs(self.config["force_entry_enable"], False)
        api = self.config["api_server"]
        self.assertIs(api["enabled"], False)
        self.assertEqual(api["listen_ip_address"], "127.0.0.1")
        self.assertEqual(api["CORS_origins"], [])

    def test_stop_and_protection_contract(self) -> None:
        orders = self.config["order_types"]
        self.assertEqual(orders["stoploss"], "limit")
        self.assertIs(orders["stoploss_on_exchange"], True)
        self.assertEqual(orders["emergency_exit"], "market")
        self.assertGreaterEqual(orders["stoploss_on_exchange_interval"], 60)
        self.assertGreaterEqual(orders["stoploss_on_exchange_limit_ratio"], 0.95)
        self.assertLess(orders["stoploss_on_exchange_limit_ratio"], 1.0)

        self.assertNotIn("protections", self.config)

    def test_live_overlay_has_no_embedded_secret_and_remains_paused(self) -> None:
        live = self.live
        self.assertIs(live["dry_run"], False)
        self.assertEqual(live["initial_state"], "paused")
        self.assertEqual(live["available_capital"], 250)
        self.assertEqual(live["stake_amount"], 80)
        self.assertEqual(live["max_open_trades"], 3)
        self.assertEqual(live["trading_mode"], "spot")
        self.assertIs(live["position_adjustment_enable"], False)
        self.assertIs(live["cancel_open_orders_on_exit"], False)
        self.assertEqual(live["exchange"]["pair_whitelist"], PAIRS)
        self.assertEqual(live["exchange"].get("key", ""), "")
        self.assertEqual(live["exchange"].get("secret", ""), "")
        self.assertIn("FREQTRADE__EXCHANGE__KEY", live["_comment"])
        self.assertIn("FREQTRADE__EXCHANGE__SECRET", live["_comment"])
        self.assertIs(live["api_server"]["enabled"], False)
        self.assertEqual(live["api_server"]["listen_ip_address"], "127.0.0.1")

    def test_public_overlay_forces_public_ccxt_market_discovery(self) -> None:
        exchange = self.public["exchange"]
        self.assertIsNone(exchange["ccxt_config"]["apiKey"])
        self.assertIsNone(exchange["ccxt_async_config"]["apiKey"])
        self.assertNotIn("secret", exchange["ccxt_config"])
        self.assertNotIn("secret", exchange["ccxt_async_config"])

        scripts_dir = RUNTIME / "scripts"
        for filename in (
            "download-data.ps1",
            "backtest.ps1",
            "lookahead-analysis.ps1",
            "recursive-analysis.ps1",
            "start-dryrun.ps1",
        ):
            with self.subTest(filename=filename):
                source = (scripts_dir / filename).read_text(encoding="utf-8")
                self.assertIn("$script:PublicOverlayPath", source)

        live_launcher = (scripts_dir / "start-live-paused.ps1").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("$script:PublicOverlayPath", live_launcher)

    def test_analysis_overlay_is_lookahead_only_and_uses_other_side(self) -> None:
        self.assertEqual(self.analysis["entry_pricing"]["price_side"], "other")
        self.assertEqual(self.analysis["exit_pricing"]["price_side"], "other")
        scripts_dir = RUNTIME / "scripts"
        lookahead = (scripts_dir / "lookahead-analysis.ps1").read_text(encoding="utf-8")
        self.assertIn("$script:AnalysisOverlayPath", lookahead)
        self.assertIn('$env:FREQTRADE__AVAILABLE_CAPITAL = "1000000000"', lookahead)
        self.assertIn('"lookahead-analysis"', lookahead)
        self.assertNotIn('"trade"', lookahead)
        for filename in (
            "download-data.ps1",
            "backtest.ps1",
            "recursive-analysis.ps1",
            "start-dryrun.ps1",
            "start-live-paused.ps1",
        ):
            with self.subTest(filename=filename):
                source = (scripts_dir / filename).read_text(encoding="utf-8")
                self.assertNotIn("$script:AnalysisOverlayPath", source)

    def test_dependency_and_image_are_pinned_to_2026_7(self) -> None:
        requirement_lines = [
            line.strip()
            for line in (RUNTIME / "requirements-freqtrade.txt").read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(requirement_lines, ["freqtrade==2026.7"])
        compose = (RUNTIME / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("image: freqtradeorg/freqtrade:2026.7", compose)
        self.assertNotIn("127.0.0.1:8080", compose)

    def test_no_strategy_hash_is_currently_trusted_for_live_use(self) -> None:
        trust = load_json(RUNTIME / "trusted-live-artifacts.json")
        self.assertEqual(trust, {"schema_version": 1, "artifacts": []})


class StrategySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = STRATEGY_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(STRATEGY_PATH))
        cls.strategy = class_node(cls.tree, "CompressionBreakout250")

    def test_long_only_fixed_caps_and_no_dca(self) -> None:
        self.assertIs(literal_class_assignment(self.strategy, "can_short"), False)
        self.assertIs(
            literal_class_assignment(self.strategy, "position_adjustment_enable"), False
        )
        self.assertEqual(
            literal_class_assignment(self.strategy, "max_entry_position_adjustment"), 0
        )
        self.assertEqual(literal_class_assignment(self.strategy, "MAX_STAKE_USDT"), 80.0)
        self.assertEqual(
            literal_class_assignment(self.strategy, "MAX_TOTAL_CAPITAL_USDT"), 250.0
        )
        self.assertEqual(
            literal_class_assignment(self.strategy, "MAX_TOTAL_EXPOSURE_USDT"), 240.0
        )
        self.assertEqual(
            literal_class_assignment(self.strategy, "MAX_OPEN_POSITIONS"), 3
        )
        self.assertEqual(
            literal_class_assignment(self.strategy, "MAX_DAILY_LOSS_USDT"), 10.0
        )
        self.assertNotIn("enter_short", self.source)

    def test_required_strategy_and_guard_callbacks_exist(self) -> None:
        methods = {
            node.name for node in self.strategy.body if isinstance(node, ast.FunctionDef)
        }
        self.assertTrue(
            {
                "populate_indicators",
                "populate_entry_trend",
                "populate_exit_trend",
                "custom_stake_amount",
                "confirm_trade_entry",
                "bot_start",
                "protections",
            }.issubset(methods)
        )
        self.assertIn("Trade.total_open_trades_stakes()", self.source)
        self.assertIn("Trade.get_open_trade_count()", self.source)
        self.assertIn("Trade.get_trades_proxy", self.source)
        self.assertIn("STOP_ENTRIES", self.source)
        self.assertIn('{"live", "dry_run"}', self.source)
        self.assertIn('"method": "CooldownPeriod"', self.source)
        self.assertIn('"method": "StoplossGuard"', self.source)
        self.assertIn('"method": "MaxDrawdown"', self.source)
        self.assertIn('"max_allowed_drawdown": 0.08', self.source)
        self.assertGreaterEqual(self.source.count("except Exception:"), 2)
        self.assertIn("execution safety contract failed", self.source)
        self.assertIn("adjacent_parameters", self.source)

    def test_no_negative_shift_or_centered_rolling_window(self) -> None:
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr == "shift" and node.args:
                value = numeric_literal(node.args[0])
                if value is not None:
                    self.assertGreaterEqual(value, 0, "Negative shift would use future data")
            if node.func.attr == "rolling":
                for keyword in node.keywords:
                    if keyword.arg == "center":
                        self.assertIsNot(
                            ast.literal_eval(keyword.value),
                            True,
                            "Centered rolling windows can use future data",
                        )
        # Last-row access is legitimate inside post-fill callbacks such as
        # order_filled(), where Freqtrade exposes only information available at
        # that callback time. Keep the strict prohibition where signals and
        # indicators are generated, because there it could leak the dataframe's
        # future endpoint into historical rows.
        causal_signal_methods = {
            "populate_indicators",
            "populate_indicators_1h",
            "populate_indicators_4h",
            "populate_indicators_btc_4h",
            "populate_entry_trend",
            "populate_exit_trend",
        }
        for node in self.strategy.body:
            if not isinstance(node, ast.FunctionDef) or node.name not in causal_signal_methods:
                continue
            method_source = ast.get_source_segment(self.source, node) or ""
            compact = method_source.replace(" ", "")
            self.assertNotIn("iloc[-1]", compact, node.name)
            self.assertNotIn("iat[-1]", compact, node.name)

    def test_hyperopt_parameters_are_explicit_or_v11_profiles_are_fixed(self) -> None:
        parameter_calls = []
        for node in self.strategy.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            if isinstance(node.value.func, ast.Name) and node.value.func.id in {
                "DecimalParameter",
                "IntParameter",
            }:
                parameter_calls.append(node.value)

        strategy_version = literal_class_assignment(self.strategy, "STRATEGY_VERSION")
        if strategy_version == "V11":
            self.assertEqual(parameter_calls, [])
            self.assertIn("PAIR_PROFILES", self.source)
            self.assertNotIn("DecimalParameter(", self.source)
            self.assertNotIn("IntParameter(", self.source)
            return

        self.assertGreaterEqual(len(parameter_calls), 6)
        for call in parameter_calls:
            keywords = {keyword.arg: keyword.value for keyword in call.keywords}
            self.assertIn("space", keywords)
            self.assertIn(ast.literal_eval(keywords["space"]), {"buy", "sell"})
            self.assertIs(ast.literal_eval(keywords["optimize"]), True)


class ScriptContractTests(unittest.TestCase):
    def test_required_native_scripts_call_expected_commands(self) -> None:
        expected = {
            "download-data.ps1": "download-data",
            "backtest.ps1": "backtesting",
            "lookahead-analysis.ps1": "lookahead-analysis",
            "recursive-analysis.ps1": "recursive-analysis",
            "start-dryrun.ps1": "trade",
        }
        scripts_dir = RUNTIME / "scripts"
        for filename, command in expected.items():
            source = (scripts_dir / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertIn(f'"{command}"', source)
                self.assertIn("Invoke-FreqtradeCommand", source)

        for filename in ("backtest.ps1", "lookahead-analysis.ps1"):
            source = (scripts_dir / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename, cost_ratio=True):
                self.assertIn('"--fee", "0.002"', source)

    def test_live_launcher_requires_env_credentials_and_forces_paused(self) -> None:
        source = (RUNTIME / "scripts" / "start-live-paused.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("FREQTRADE__EXCHANGE__SECRET", source)
        self.assertIn('$env:FREQTRADE__INITIAL_STATE = "paused"', source)
        self.assertIn("Assert-NoFreqtradeOverrides", source)
        self.assertIn("FREQTRADE__EXCHANGE__KEY", source)
        self.assertIn("FREQTRADE__EXCHANGE__SECRET", source)
        self.assertIn("STOP_ENTRIES", source)
        self.assertIn("AI_TRADING_KILL_SWITCH_FILE", source)
        self.assertIn("authorize", source)
        self.assertIn("--expected-strategy-sha256", source)
        self.assertIn("--expected-config-sha256", source)
        self.assertIn("--expected-lock-sha256", source)
        self.assertNotIn('"--strategy-path",', source)
        self.assertIn("locked_freqtrade.py", source)
        self.assertIn("trusted-live-artifacts.json", source)
        self.assertIn("FileShare]::None", source)
        self.assertIn('Remove-Item "Env:FREQTRADE__EXCHANGE__KEY"', source)
        self.assertIn("FileShare]::Read", source)
        self.assertNotIn("EnableEntries", source)

        dryrun = (RUNTIME / "scripts" / "start-dryrun.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn('FREQTRADE__DRY_RUN = "true"', dryrun)
        self.assertIn("Assert-NoFreqtradeOverrides", dryrun)

    def test_live_preflight_validates_exact_effective_invariants(self) -> None:
        result = validate(
            CONFIG_PATH,
            LIVE_OVERLAY_PATH,
            STRATEGY_PATH,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "live_recovery_paused")
        self.assertEqual(result["maximum_exposure_usdt"], 240)

        source = (RUNTIME / "scripts" / "start-live-paused.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("validate_runtime.py", source)
        self.assertIn("--strategy", source)

    def test_live_preflight_binds_strategy_config_lock_and_policy(self) -> None:
        first = validate(CONFIG_PATH, LIVE_OVERLAY_PATH, STRATEGY_PATH)
        lock_hash = hashlib.sha256((REPO_ROOT / "uv.lock").read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            frozen = Path(temporary) / "effective.json"
            result = validate(
                CONFIG_PATH,
                LIVE_OVERLAY_PATH,
                STRATEGY_PATH,
                expected_strategy_sha256=first["strategy_sha256"],
                expected_config_sha256=first["effective_config_sha256"],
                lock_path=REPO_ROOT / "uv.lock",
                expected_lock_sha256=lock_hash,
                expected_imports_sha256=hashlib.sha256(b"").hexdigest(),
                risk_policy=RiskPolicy().to_dict(),
                effective_config_output=frozen,
            )
            self.assertEqual(result["dependency_lock_sha256"], lock_hash)
            self.assertEqual(
                hashlib.sha256(frozen.read_bytes()).hexdigest(),
                first["effective_config_sha256"],
            )

        with self.assertRaisesRegex(ValueError, "strategy SHA-256"):
            validate(
                CONFIG_PATH,
                LIVE_OVERLAY_PATH,
                STRATEGY_PATH,
                expected_strategy_sha256="0" * 64,
            )

    def test_live_preflight_rejects_weakened_overlay_and_parameter_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = root / "unsafe.json"
            live = load_json(LIVE_OVERLAY_PATH)
            live["stoploss"] = -0.99
            overlay.write_text(json.dumps(live), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stoploss"):
                validate(CONFIG_PATH, overlay, STRATEGY_PATH)

            strategy_dir = root / "strategy"
            strategy_dir.mkdir()
            staged = strategy_dir / STRATEGY_PATH.name
            shutil.copyfile(STRATEGY_PATH, staged)
            staged.with_suffix(".json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "adjacent strategy parameters"):
                validate(CONFIG_PATH, LIVE_OVERLAY_PATH, staged)

    def test_generated_runtime_artifacts_are_ignored(self) -> None:
        source = (RUNTIME / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            ".venv/",
            "user_data/data/",
            "user_data/logs/",
            "user_data/backtest_results/",
            "user_data/*.sqlite",
            "user_data/STOP_ENTRIES",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, source)

    def test_deployment_manifest_generator_binds_all_execution_inputs(self) -> None:
        payload = generate(STRATEGY_PATH, "CompressionBreakout250", REPO_ROOT)
        manifest = payload["metadata"]["deployment_manifest"]
        self.assertEqual(
            payload["artifact_sha256"],
            hashlib.sha256(STRATEGY_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            manifest["lock_sha256"],
            hashlib.sha256((REPO_ROOT / "uv.lock").read_bytes()).hexdigest(),
        )
        self.assertEqual(manifest["imports_sha256"], hashlib.sha256(b"").hexdigest())
        self.assertEqual(manifest["freqtrade_version"], "2026.7")
        self.assertIn("not a source audit", payload["warning"])


if __name__ == "__main__":
    unittest.main()
