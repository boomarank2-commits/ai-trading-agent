from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from local_trader.errors import ValidationError
from local_trader.mcp_server import (
    DATABASE_ENVIRONMENT_VARIABLE,
    ResearchRegistryTools,
    create_server,
    resolve_database_path,
)
from local_trader.registry import StrategyRegistry


class McpResearchToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "registry.sqlite3"
        self.candidates = self.root / "candidate"
        self.promoted = self.root / "promoted"
        self.registry = StrategyRegistry.initialize(
            self.database,
            self.candidates,
            self.promoted,
        )
        self.tools = ResearchRegistryTools(self.database)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def source(self, name: str = "alpha.py") -> Path:
        path = self.candidates / name
        path.write_text("SIGNAL = 'closed-candle-only'\n", encoding="utf-8")
        return path

    def register(self, name: str = "alpha") -> dict:
        return self.tools.register_strategy(
            name,
            str(self.source(f"{name}.py")),
            description="research candidate",
            metadata={"family": "breakout"},
        )

    def evaluate(self, name: str = "alpha") -> dict:
        return self.tools.record_evaluation(
            name,
            symbol="BTCUSDT",
            timeframe="1h",
            sample_type="BACKTEST",
            net_profit=1.0,
            profit_factor=1.1,
            max_drawdown=2.0,
            win_rate=50.0,
            trade_count=1,
            avg_trade=1.0,
            max_daily_loss_abs=1.0,
        )

    def test_registry_operations_return_structured_dicts(self) -> None:
        registered = self.register()
        self.assertEqual(registered["registered"]["lifecycle"], "IDEA")
        evaluation = self.evaluate()
        self.assertEqual(evaluation["evaluation"]["symbol"], "BTCUSDT")

        listed = self.tools.list_strategies()
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["strategies"][0]["strategy"], "alpha")
        verified = self.tools.verify_artifacts("alpha")
        self.assertTrue(verified["valid"])
        self.assertTrue(verified["artifacts"][0]["valid"])
        status = self.tools.strategy_status("alpha")
        self.assertEqual(status["evaluation_summary"]["trade_count"], 1)

        configuration = self.tools.configuration()
        self.assertEqual(configuration["mode"], "research_only")
        self.assertEqual(configuration["maximum_mcp_stage"], "PAPER")
        self.assertEqual(
            configuration["live_stages_blocked"], ["CANARY", "PRODUCTION"]
        )
        self.assertTrue(configuration["database_integrity"]["valid"])

    def test_registration_is_restricted_to_candidate_source_root(self) -> None:
        candidate_source = self.source("handoff.py")
        candidate = self.registry.register("handoff", candidate_source)
        promoted_source = self.promoted / "handoff.py"
        promoted_source.write_bytes(candidate_source.read_bytes())
        metadata = {
            "deployment_manifest": {
                "config_sha256": "a" * 64,
                "lock_sha256": "b" * 64,
                "imports_sha256": "c" * 64,
                "freqtrade_version": "2026.7",
            }
        }

        with self.assertRaisesRegex(
            ValidationError, "registration requires source_root=candidate"
        ):
            self.tools.register_strategy(
                "handoff",
                str(promoted_source),
                parent_version=int(candidate["version"]),
                metadata=metadata,
            )

        versions = self.registry.list_versions("handoff")
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["source_root"], "candidate")

    def test_live_evidence_types_are_rejected_without_a_write(self) -> None:
        class ExplodingRegistry:
            def evaluate(self, *args: object, **kwargs: object) -> None:
                raise AssertionError("registry must not receive a live evidence type")

        tools = ResearchRegistryTools(
            self.database, registry_factory=lambda _database: ExplodingRegistry()
        )
        for sample_type in ("CANARY", "production"):
            with (
                self.subTest(sample_type=sample_type),
                self.assertRaisesRegex(ValidationError, "blocked through MCP"),
            ):
                tools.record_evaluation(
                    "alpha",
                    symbol="BTCUSDT",
                    timeframe="1h",
                    sample_type=sample_type,
                    net_profit=1,
                    profit_factor=1.3,
                    max_drawdown=3,
                    win_rate=55,
                    trade_count=50,
                    avg_trade=0.02,
                    max_daily_loss_abs=1,
                )

    def test_evaluation_enables_atomic_research_only_guard(self) -> None:
        class GuardProbeRegistry:
            def evaluate(
                self, *args: object, research_only: bool = False, **kwargs: object
            ) -> None:
                if not research_only:
                    raise AssertionError("MCP must enable the registry research-only guard")
                raise ValidationError("MCP cannot record evidence for a live version")

        tools = ResearchRegistryTools(
            self.database, registry_factory=lambda _database: GuardProbeRegistry()
        )
        with self.assertRaisesRegex(ValidationError, "live version"):
            tools.record_evaluation(
                "alpha",
                symbol="BTCUSDT",
                timeframe="1h",
                sample_type="BACKTEST",
                net_profit=1,
                profit_factor=1.3,
                max_drawdown=3,
                win_rate=55,
                trade_count=50,
                avg_trade=0.02,
                max_daily_loss_abs=1,
            )

    def test_research_lifecycle_can_advance_only_through_paper(self) -> None:
        self.register()
        self.tools.promote_research_stage(
            "alpha", "RESEARCH", reason="begin research"
        )
        research_slices = (
            ("BTCUSDT", "1h", "BACKTEST", 40),
            ("ETHUSDT", "4h", "VALIDATION", 30),
            ("BTCUSDT", "4h", "OUT_OF_SAMPLE", 30),
        )
        for symbol, timeframe, sample_type, trade_count in research_slices:
            self.tools.record_evaluation(
                "alpha",
                symbol=symbol,
                timeframe=timeframe,
                sample_type=sample_type,
                net_profit=5,
                profit_factor=1.3,
                max_drawdown=5,
                win_rate=55,
                trade_count=trade_count,
                avg_trade=0.1,
                max_daily_loss_abs=1.0,
            )
        for target in ("VALIDATED",):
            assessment = self.tools.assess_research_promotion("alpha", target)
            self.assertTrue(assessment["decision"]["eligible"])
            self.tools.promote_research_stage(
                "alpha", target, reason="automated research gate"
            )

        for symbol in ("BTCUSDT", "ETHUSDT"):
            self.tools.record_evaluation(
                "alpha",
                symbol=symbol,
                timeframe="1h",
                sample_type="HOLDOUT",
                net_profit=1,
                profit_factor=1.3,
                max_drawdown=3,
                win_rate=55,
                trade_count=50,
                avg_trade=0.02,
                max_daily_loss_abs=1.0,
            )
        for target in ("HOLDOUT_PASSED", "SHADOW"):
            assessment = self.tools.assess_research_promotion("alpha", target)
            self.assertTrue(assessment["decision"]["eligible"])
            self.tools.promote_research_stage(
                "alpha", target, reason="automated research gate"
            )

        for symbol in ("BTCUSDT", "ETHUSDT"):
            self.tools.record_evaluation(
                "alpha",
                symbol=symbol,
                timeframe="1h",
                sample_type="SHADOW",
                net_profit=1,
                profit_factor=1.3,
                max_drawdown=3,
                win_rate=55,
                trade_count=50,
                avg_trade=0.02,
                max_daily_loss_abs=1.0,
            )
        assessment = self.tools.assess_research_promotion("alpha", "PAPER")
        self.assertTrue(assessment["decision"]["eligible"])
        promotion = self.tools.promote_research_stage(
            "alpha", "PAPER", reason="automated research gate"
        )
        self.assertEqual(promotion["promotion"]["to_state"], "PAPER")
        self.assertEqual(
            self.tools.strategy_status("alpha")["version"]["lifecycle"], "PAPER"
        )

    def test_canary_and_production_are_blocked_before_registry_access(self) -> None:
        class ExplodingRegistry:
            def assess_promotion(self, *args: object, **kwargs: object) -> None:
                raise AssertionError("registry must not receive a live-stage assessment")

            def promote(self, *args: object, **kwargs: object) -> None:
                raise AssertionError("registry must not receive a live-stage promotion")

        tools = ResearchRegistryTools(
            self.database, registry_factory=lambda _database: ExplodingRegistry()
        )
        for target in ("CANARY", "canary", "PRODUCTION", "Production"):
            with (
                self.subTest(target=target, operation="assess"),
                self.assertRaisesRegex(ValidationError, "permanently blocked"),
            ):
                tools.assess_research_promotion("alpha", target)
            with (
                self.subTest(target=target, operation="promote"),
                self.assertRaisesRegex(ValidationError, "permanently blocked"),
            ):
                tools.promote_research_stage("alpha", target)

    def test_other_non_research_transitions_are_not_exposed(self) -> None:
        for target in ("PAUSED", "DEGRADED", "IDEA"):
            with (
                self.subTest(target=target),
                self.assertRaisesRegex(ValidationError, "through PAPER"),
            ):
                self.tools.promote_research_stage("missing", target)

    def test_secret_like_free_form_fields_are_rejected_and_outputs_redacted(self) -> None:
        with self.assertRaisesRegex(ValidationError, "secret fields"):
            self.tools.register_strategy(
                "unsafe",
                str(self.source("unsafe.py")),
                metadata={"nested": {"api_key": "do-not-store"}},
            )
        self.assertEqual(self.tools.list_strategies()["count"], 0)

        source = self.source("legacy.py")
        self.registry.register(
            "legacy", source, metadata={"api_key": "must-never-be-returned"}
        )
        serialized = json.dumps(self.tools.strategy_status("legacy"), sort_keys=True)
        self.assertNotIn("must-never-be-returned", serialized)
        self.assertIn("[REDACTED]", serialized)

        with self.assertRaisesRegex(ValidationError, "credentials or secrets"):
            self.tools.record_evaluation(
                "legacy",
                symbol="BTCUSDT",
                timeframe="1h",
                sample_type="BACKTEST",
                net_profit=1,
                profit_factor=1,
                max_drawdown=1,
                win_rate=50,
                trade_count=1,
                avg_trade=1,
                max_daily_loss_abs=1,
                notes="api_key=do-not-store",
            )

    def test_fastmcp_schema_has_only_research_registry_tools(self) -> None:
        server = create_server(self.database)
        definitions = asyncio.run(server.list_tools())
        names = {tool.name for tool in definitions}
        self.assertEqual(
            names,
            {
                "registry_configuration",
                "strategy_status",
                "list_strategies",
                "verify_artifacts",
                "register_strategy",
                "record_evaluation",
                "assess_research_promotion",
                "promote_research_stage",
            },
        )
        forbidden = {"order", "exchange", "binance", "credential", "secret", "live"}
        for name in names:
            self.assertFalse(any(part in name for part in forbidden))

        promotion = next(
            tool for tool in definitions if tool.name == "promote_research_stage"
        )
        self.assertNotIn("manual_approval", promotion.inputSchema["properties"])
        self.assertNotIn("approved_by", promotion.inputSchema["properties"])
        self.assertFalse(promotion.annotations.openWorldHint)

        _, structured = asyncio.run(server.call_tool("registry_configuration", {}))
        self.assertIsInstance(structured, dict)
        self.assertEqual(structured["mode"], "research_only")


class McpConfigurationTests(unittest.TestCase):
    def test_cli_database_wins_over_environment(self) -> None:
        result = resolve_database_path(
            "cli.sqlite3",
            environ={DATABASE_ENVIRONMENT_VARIABLE: "environment.sqlite3"},
        )
        self.assertEqual(result.name, "cli.sqlite3")

    def test_environment_database_is_supported(self) -> None:
        result = resolve_database_path(
            None, environ={DATABASE_ENVIRONMENT_VARIABLE: "environment.sqlite3"}
        )
        self.assertEqual(result.name, "environment.sqlite3")

    def test_database_is_required(self) -> None:
        with self.assertRaisesRegex(ValidationError, DATABASE_ENVIRONMENT_VARIABLE):
            resolve_database_path(None, environ={})


if __name__ == "__main__":
    unittest.main()
