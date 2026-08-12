from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from local_trader import (  # noqa: E402
    AlreadyInitializedError,
    ApprovalArtifactError,
    ArtifactPathError,
    ArtifactVerificationError,
    DeploymentAuthorizationError,
    GateCriteria,
    GateRejectedError,
    Lifecycle,
    ManualApprovalRequired,
    StrategyRegistry,
    ValidationError,
)


class RegistryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.candidates = self.root / "candidates"
        self.promoted = self.root / "promoted"
        self.database = self.root / "state" / "registry.sqlite3"
        self.registry = StrategyRegistry.initialize(
            self.database, self.candidates, self.promoted
        )
        self.source = self.candidates / "alpha.py"
        self.source.write_text("SIGNAL = 'alpha'\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def register_alpha(self) -> dict[str, object]:
        return self.registry.register(
            "alpha", self.source, description="test strategy", metadata={"seed": 7}
        )

    def add_passing_research_matrix(
        self, strategy: str = "alpha", *, version: int | None = None
    ) -> None:
        evaluations = [
            ("BTCUSDT", "1h", "BACKTEST", 10.0, 1.30, 10.0, 55.0, 40, 0.25),
            ("ETHUSDT", "4h", "VALIDATION", 6.0, 1.25, 12.0, 52.0, 30, 0.20),
            ("BTCUSDT", "4h", "OUT_OF_SAMPLE", 4.0, 1.28, 9.0, 54.0, 30, 0.13),
        ]
        for symbol, timeframe, sample, net, factor, drawdown, wins, count, avg in evaluations:
            self.registry.evaluate(
                strategy,
                version=version,
                symbol=symbol,
                timeframe=timeframe,
                sample_type=sample,
                net_profit=net,
                profit_factor=factor,
                max_drawdown=drawdown,
                win_rate=wins,
                trade_count=count,
                avg_trade=avg,
                max_daily_loss_abs=1,
                evidence_id=f"{strategy}-{sample}-{symbol}-{timeframe}",
            )

    def add_stage_evidence(
        self,
        sample_type: str,
        *,
        strategy: str = "alpha",
        version: int | None = None,
        net_profit: float = 2.0,
        suffix: str = "readiness",
    ) -> None:
        for symbol in ("BTCUSDT", "ETHUSDT"):
            self.registry.evaluate(
                strategy,
                version=version,
                symbol=symbol,
                timeframe="1h",
                sample_type=sample_type,
                net_profit=net_profit / 2,
                profit_factor=1.3,
                max_drawdown=5,
                win_rate=55,
                trade_count=50,
                avg_trade=net_profit / 100,
                max_daily_loss_abs=1,
                evidence_id=f"{strategy}-{sample_type}-{symbol}-{suffix}",
            )

    @staticmethod
    def deployment_manifest() -> dict[str, object]:
        return {
            "deployment_manifest": {
                "config_sha256": "a" * 64,
                "lock_sha256": "b" * 64,
                "imports_sha256": "c" * 64,
                "freqtrade_version": "2026.7",
            }
        }

    def write_approval(
        self,
        strategy: str,
        version: int,
        target: str,
        artifact_sha256: str,
        approver: str,
    ) -> Path:
        approval_dir = self.root / "human-approvals"
        approval_dir.mkdir(exist_ok=True)
        path = approval_dir / f"{strategy}-{version}-{target}.json"
        path.write_text(
            json.dumps(
                {
                    "strategy": strategy,
                    "version": version,
                    "target": target,
                    "artifact_sha256": artifact_sha256,
                    "approver": approver,
                    "expires_at": (
                        datetime.now(UTC) + timedelta(minutes=5)
                    ).isoformat().replace("+00:00", "Z"),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return path


class InitializationAndArtifactTests(RegistryTestCase):
    def test_initialization_creates_expected_tables_and_metadata(self) -> None:
        self.assertTrue(self.database.is_file())
        config = self.registry.configuration()
        self.assertEqual(config["candidate_root"], str(self.candidates.resolve()))
        self.assertEqual(config["promoted_root"], str(self.promoted.resolve()))
        with closing(sqlite3.connect(self.database)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertTrue(
            {"strategies", "versions", "evaluations", "trials", "promotion_events"}
            <= tables
        )
        self.assertTrue(self.registry.database_integrity()["valid"])

    def test_initialization_never_overwrites(self) -> None:
        with self.assertRaises(AlreadyInitializedError):
            StrategyRegistry.initialize(
                self.database, self.candidates, self.promoted
            )

    def test_roots_must_be_distinct_and_non_overlapping(self) -> None:
        another_db = self.root / "other.sqlite3"
        with self.assertRaises(ValidationError):
            StrategyRegistry.initialize(
                another_db, self.root / "artifacts", self.root / "artifacts" / "live"
            )

    def test_register_records_exact_sha_and_verifies(self) -> None:
        version = self.register_alpha()
        expected = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.assertEqual(version["artifact_sha256"], expected)
        self.assertEqual(version["lifecycle"], "IDEA")
        self.assertEqual(version["source_root"], "candidate")
        self.assertTrue(self.registry.verify("alpha")["valid"])

    def test_artifact_must_be_under_safe_root(self) -> None:
        outside = self.root / "outside.py"
        outside.write_text("unsafe = True\n", encoding="utf-8")
        with self.assertRaises(ArtifactPathError):
            self.registry.register("outside", outside)

    def test_promoted_root_is_also_valid(self) -> None:
        candidate = self.candidates / "live.py"
        candidate.write_text("LIVE = False\n", encoding="utf-8")
        first = self.registry.register("live", candidate)
        source = self.promoted / "live.py"
        source.write_bytes(candidate.read_bytes())
        version = self.registry.register(
            "live",
            source,
            parent_version=int(first["version"]),
            metadata=self.deployment_manifest(),
        )
        self.assertEqual(version["source_root"], "promoted")
        self.assertEqual(version["artifact_sha256"], first["artifact_sha256"])

    def test_promoted_handoff_requires_exact_candidate_parent_and_manifest(self) -> None:
        candidate = self.register_alpha()
        promoted = self.promoted / "alpha.py"
        promoted.write_bytes(self.source.read_bytes())
        with self.assertRaisesRegex(ValidationError, "parent-version"):
            self.registry.register(
                "alpha", promoted, metadata=self.deployment_manifest()
            )
        with self.assertRaisesRegex(ValidationError, "deployment_manifest"):
            self.registry.register(
                "alpha", promoted, parent_version=int(candidate["version"])
            )
        promoted.write_text("SIGNAL = 'different'\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "SHA-256"):
            self.registry.register(
                "alpha",
                promoted,
                parent_version=int(candidate["version"]),
                metadata=self.deployment_manifest(),
            )

    def test_promoted_handoff_is_fresh_idea_without_inherited_ledger(self) -> None:
        candidate = self.register_alpha()
        self.registry.promote("alpha", Lifecycle.RESEARCH, version=1)
        self.add_passing_research_matrix(version=1)
        self.registry.promote("alpha", Lifecycle.VALIDATED, version=1)
        promoted = self.promoted / "alpha.py"
        promoted.write_bytes(self.source.read_bytes())
        promoted_version = self.registry.register(
            "alpha",
            promoted,
            parent_version=1,
            metadata=self.deployment_manifest(),
        )
        self.assertEqual(promoted_version["lifecycle"], "IDEA")
        self.assertEqual(promoted_version["parent_version_id"], candidate["version_id"])
        status = self.registry.status("alpha", version=2)
        self.assertEqual(status["evaluation_summary"]["evaluation_count"], 0)
        self.assertEqual(status["promotion_events"], [])
        self.assertEqual(status["trials"], [])
        self.assertFalse(promoted_version["active"])
        with self.assertRaisesRegex(ValidationError, "already registered"):
            self.registry.register(
                "alpha",
                promoted,
                parent_version=1,
                metadata=self.deployment_manifest(),
            )

    def test_candidate_cannot_descend_from_promoted_version(self) -> None:
        self.register_alpha()
        promoted = self.promoted / "alpha.py"
        promoted.write_bytes(self.source.read_bytes())
        self.registry.register(
            "alpha",
            promoted,
            parent_version=1,
            metadata=self.deployment_manifest(),
        )
        next_candidate = self.candidates / "alpha_v3.py"
        next_candidate.write_text("SIGNAL = 'new candidate'\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "cannot descend"):
            self.registry.register("alpha", next_candidate, parent_version=2)

    def test_tampering_blocks_verify_evaluation_and_advancement(self) -> None:
        self.register_alpha()
        self.source.write_text("SIGNAL = 'tampered'\n", encoding="utf-8")
        with self.assertRaises(ArtifactVerificationError):
            self.registry.verify("alpha")
        with self.assertRaises(ArtifactVerificationError):
            self.registry.evaluate(
                "alpha",
                symbol="BTCUSDT",
                timeframe="1h",
                sample_type="BACKTEST",
                net_profit=1,
                profit_factor=1.3,
                max_drawdown=5,
                win_rate=50,
                trade_count=10,
                avg_trade=0.1,
            )
        with self.assertRaises(ArtifactVerificationError):
            self.registry.promote("alpha", Lifecycle.RESEARCH)
        # A stop action must remain possible even when integrity is lost.
        paused = self.registry.promote("alpha", Lifecycle.PAUSED, reason="hash alarm")
        self.assertEqual(paused["to_state"], "PAUSED")

    def test_hash_and_ledger_rows_are_sqlite_immutable(self) -> None:
        version = self.register_alpha()
        evaluation = self.registry.evaluate(
            "alpha",
            symbol="BTCUSDT",
            timeframe="1h",
            sample_type="BACKTEST",
            net_profit=1,
            profit_factor=1.3,
            max_drawdown=5,
            win_rate=50,
            trade_count=10,
            avg_trade=0.1,
        )
        with closing(sqlite3.connect(self.database)) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE versions SET artifact_sha256 = ? WHERE id = ?",
                    ("0" * 64, version["version_id"]),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM evaluations WHERE id = ?",
                    (evaluation["evaluation_id"],),
                )

    def test_direct_lifecycle_update_without_event_is_blocked(self) -> None:
        version = self.register_alpha()
        with (
            closing(sqlite3.connect(self.database)) as connection,
            self.assertRaises(sqlite3.IntegrityError),
        ):
            connection.execute(
                "UPDATE versions SET lifecycle = 'RESEARCH' WHERE id = ?",
                (version["version_id"],),
            )

    def test_direct_sql_event_insert_without_registry_gate_is_blocked(self) -> None:
        version = self.register_alpha()
        with closing(sqlite3.connect(self.database)) as connection:
            with self.assertRaisesRegex(
                sqlite3.DatabaseError,
                "_local_trader_gate_authorized|registry gate authorization",
            ):
                connection.execute(
                    """
                    INSERT INTO promotion_events(
                        strategy_id, version_id, from_state, to_state,
                        approved_by, manual_approval, approval_file_path,
                        approval_sha256, approval_json, evaluation_cutoff_id,
                        reason, gate_snapshot_json, recorded_at
                    ) VALUES (?, ?, 'IDEA', 'RESEARCH', 'raw-sql', 0, '',
                              NULL, '{}', 0, '', '{}', ?)
                    """,
                    (
                        version["strategy_id"],
                        version["version_id"],
                        datetime.now(UTC).isoformat(),
                    ),
                )
            count = connection.execute(
                "SELECT COUNT(*) FROM promotion_events"
            ).fetchone()[0]
        self.assertEqual(count, 0)
        self.assertEqual(self.registry.status("alpha")["version"]["lifecycle"], "IDEA")

    def test_new_idea_version_is_append_only_without_replacing_active(self) -> None:
        first = self.register_alpha()
        second_source = self.candidates / "alpha_v2.py"
        second_source.write_text("SIGNAL = 'alpha-v2'\n", encoding="utf-8")
        second = self.registry.register("ALPHA", second_source)
        self.assertEqual(first["version"], 1)
        self.assertEqual(second["version"], 2)
        self.assertEqual(second["parent_version_id"], first["version_id"])
        versions = self.registry.list_versions("alpha")
        self.assertEqual([item["active"] for item in versions], [True, False])
        self.assertEqual(self.registry.status("alpha")["version"]["version"], 1)
        self.assertEqual(self.registry.status("alpha", version=2)["version"]["version"], 2)


class EvaluationTrialAndGateTests(RegistryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.register_alpha()

    def test_evaluation_captures_all_required_metrics(self) -> None:
        evaluation = self.registry.evaluate(
            "alpha",
            symbol="btcusdt",
            timeframe="1H",
            sample_type="out-of-sample",
            net_profit=12.5,
            profit_factor=1.4,
            max_drawdown=9.5,
            win_rate=57.5,
            trade_count=42,
            avg_trade=0.3,
        )
        self.assertEqual(evaluation["symbol"], "BTCUSDT")
        self.assertEqual(evaluation["timeframe"], "1h")
        self.assertEqual(evaluation["sample_type"], "OUT_OF_SAMPLE")
        for field in (
            "net_profit",
            "profit_factor",
            "max_drawdown",
            "win_rate",
            "trade_count",
            "avg_trade",
            "max_daily_loss_abs",
            "evidence_id",
            "evidence_fingerprint",
            "provenance",
        ):
            self.assertIn(field, evaluation)

    def test_invalid_evaluation_metrics_fail_closed(self) -> None:
        base = {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "sample_type": "BACKTEST",
            "net_profit": 1,
            "profit_factor": 1.3,
            "max_drawdown": 5,
            "win_rate": 50,
            "trade_count": 10,
            "avg_trade": 0.1,
        }
        for field, value in (
            ("profit_factor", -1),
            ("profit_factor", float("nan")),
            ("max_drawdown", 101),
            ("win_rate", -1),
            ("trade_count", True),
            ("sample_type", "mystery"),
            ("max_daily_loss_abs", -1),
        ):
            values = dict(base)
            values[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                self.registry.evaluate("alpha", **values)

    def test_evaluations_reject_exact_duplicate_and_duplicate_evidence_id(self) -> None:
        values = {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "sample_type": "BACKTEST",
            "net_profit": 1,
            "profit_factor": 1.3,
            "max_drawdown": 5,
            "win_rate": 50,
            "trade_count": 10,
            "avg_trade": 0.1,
            "evidence_id": "dataset-window-1",
            "dataset_sha256": "d" * 64,
            "provenance": {"source": "fixture", "window": "2025Q1"},
        }
        first = self.registry.evaluate("alpha", **values)
        self.assertEqual(first["dataset_sha256"], "d" * 64)
        with self.assertRaisesRegex(ValidationError, "exact duplicate"):
            self.registry.evaluate("alpha", **values)
        changed_metrics = dict(values, net_profit=2)
        with self.assertRaisesRegex(ValidationError, "evidence_id"):
            self.registry.evaluate("alpha", **changed_metrics)
        changed_id = dict(values, evidence_id="dataset-window-2")
        with self.assertRaisesRegex(ValidationError, "exact duplicate"):
            self.registry.evaluate("alpha", **changed_id)

    def test_trial_ledger_and_evaluation_link(self) -> None:
        trial = self.registry.record_trial(
            "alpha",
            trial_type="walk_forward",
            status="passed",
            hypothesis="trend persists",
            parameters={"window": 20},
            result={"robust": True},
        )
        evaluation = self.registry.evaluate(
            "alpha",
            trial_id=trial["trial_id"],
            symbol="BTCUSDT",
            timeframe="1h",
            sample_type="WALK_FORWARD",
            net_profit=3,
            profit_factor=1.4,
            max_drawdown=8,
            win_rate=55,
            trade_count=25,
            avg_trade=0.12,
        )
        self.assertEqual(evaluation["trial_id"], trial["trial_id"])
        status = self.registry.status("alpha")
        self.assertEqual(status["trials"][0]["parameters"], {"window": 20})

    def test_gate_rejects_insufficient_evidence_and_illegal_skips(self) -> None:
        decision = self.registry.assess_promotion("alpha", Lifecycle.VALIDATED)
        self.assertFalse(decision.eligible)
        self.assertTrue(any("not allowed" in failure for failure in decision.failures))
        with self.assertRaises(GateRejectedError):
            self.registry.promote("alpha", Lifecycle.VALIDATED)
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        decision = self.registry.assess_promotion("alpha", Lifecycle.VALIDATED)
        self.assertFalse(decision.eligible)
        self.assertTrue(any("trade_count" in failure for failure in decision.failures))

    def test_each_stage_requires_new_stage_specific_evidence(self) -> None:
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        self.add_passing_research_matrix()
        self.registry.promote("alpha", Lifecycle.VALIDATED)
        holdout = self.registry.assess_promotion(
            "alpha", Lifecycle.HOLDOUT_PASSED
        )
        self.assertFalse(holdout.eligible)
        self.assertEqual(
            holdout.evidence["required_sample_types"], ["HOLDOUT"]
        )
        self.add_stage_evidence("HOLDOUT")
        self.registry.promote("alpha", Lifecycle.HOLDOUT_PASSED)
        with self.assertRaisesRegex(ValidationError, "only be recorded while"):
            self.add_stage_evidence("SHADOW")
        shadow = self.registry.assess_promotion("alpha", Lifecycle.SHADOW)
        self.assertTrue(shadow.eligible)
        self.assertEqual(shadow.evidence["required_sample_types"], ["HOLDOUT"])
        self.registry.promote("alpha", Lifecycle.SHADOW)
        paper = self.registry.assess_promotion("alpha", Lifecycle.PAPER)
        self.assertFalse(paper.eligible)
        self.assertEqual(paper.evidence["required_sample_types"], ["SHADOW"])
        self.add_stage_evidence("SHADOW")
        self.assertTrue(
            self.registry.assess_promotion("alpha", Lifecycle.PAPER).eligible
        )
        self.registry.promote("alpha", Lifecycle.PAPER)
        canary = self.registry.assess_promotion("alpha", Lifecycle.CANARY)
        self.assertFalse(canary.eligible)
        self.assertEqual(canary.evidence["required_sample_types"], ["PAPER"])
        self.add_stage_evidence("PAPER")

    def test_minimum_slice_pf_positive_profit_and_daily_loss_are_gated(self) -> None:
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        self.registry.evaluate(
            "alpha",
            symbol="BTCUSDT",
            timeframe="1h",
            sample_type="BACKTEST",
            net_profit=10,
            profit_factor=1.3,
            max_drawdown=5,
            win_rate=55,
            trade_count=99,
            avg_trade=0.1,
            evidence_id="dominant-good-slice",
        )
        self.registry.evaluate(
            "alpha",
            symbol="ETHUSDT",
            timeframe="4h",
            sample_type="VALIDATION",
            net_profit=1,
            profit_factor=0.1,
            max_drawdown=5,
            win_rate=55,
            trade_count=1,
            avg_trade=1,
            max_daily_loss_abs=11,
            evidence_id="tiny-bad-slice",
        )
        decision = self.registry.assess_promotion("alpha", Lifecycle.VALIDATED)
        self.assertFalse(decision.eligible)
        self.assertTrue(any("minimum slice profit_factor" in item for item in decision.failures))
        self.assertTrue(any("must report max_daily_loss_abs" in item for item in decision.failures))
        self.assertTrue(any("max_daily_loss_abs" in item for item in decision.failures))
        self.assertNotIn("profit_factor", decision.evidence["stage_summary"])

    def test_validated_requires_every_research_evidence_type(self) -> None:
        for missing in ("BACKTEST", "VALIDATION", "OUT_OF_SAMPLE"):
            with self.subTest(missing=missing):
                strategy = f"missing-{missing.lower()}"
                source = self.candidates / f"{strategy}.py"
                source.write_text("RULE = 1\n", encoding="utf-8")
                self.registry.register(strategy, source)
                self.registry.promote(strategy, Lifecycle.RESEARCH)
                slices = (
                    ("BACKTEST", "BTCUSDT", "1h"),
                    ("VALIDATION", "ETHUSDT", "4h"),
                    ("OUT_OF_SAMPLE", "BTCUSDT", "4h"),
                )
                for index, (sample_type, symbol, timeframe) in enumerate(slices):
                    if sample_type == missing:
                        continue
                    self.registry.evaluate(
                        strategy,
                        symbol=symbol,
                        timeframe=timeframe,
                        sample_type=sample_type,
                        net_profit=10,
                        profit_factor=1.3,
                        max_drawdown=5,
                        win_rate=55,
                        trade_count=100,
                        avg_trade=0.1,
                        max_daily_loss_abs=1,
                        evidence_id=f"{strategy}-{index}",
                    )
                decision = self.registry.assess_promotion(
                    strategy, Lifecycle.VALIDATED
                )
                self.assertFalse(decision.eligible)
                self.assertTrue(
                    any(
                        f"missing: {missing}" in failure
                        for failure in decision.failures
                    )
                )

    def test_holdout_rejects_zero_trades_and_each_negative_slice(self) -> None:
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        self.add_passing_research_matrix()
        self.registry.promote("alpha", Lifecycle.VALIDATED)
        self.registry.evaluate(
            "alpha",
            symbol="BTCUSDT",
            timeframe="1h",
            sample_type="HOLDOUT",
            net_profit=1,
            profit_factor=1.3,
            max_drawdown=5,
            win_rate=50,
            trade_count=0,
            avg_trade=0,
            evidence_id="empty-holdout",
        )
        decision = self.registry.assess_promotion(
            "alpha", Lifecycle.HOLDOUT_PASSED
        )
        self.assertFalse(decision.eligible)
        self.assertTrue(any("contain trades" in item for item in decision.failures))

    def test_stage_rejects_ten_trade_single_symbol_sample(self) -> None:
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        self.add_passing_research_matrix()
        self.registry.promote("alpha", Lifecycle.VALIDATED)
        self.registry.evaluate(
            "alpha",
            symbol="BTCUSDT",
            timeframe="1h",
            sample_type="HOLDOUT",
            net_profit=2,
            profit_factor=1.3,
            max_drawdown=5,
            win_rate=55,
            trade_count=10,
            avg_trade=0.2,
            max_daily_loss_abs=1,
            evidence_id="tiny-holdout",
        )
        decision = self.registry.assess_promotion(
            "alpha", Lifecycle.HOLDOUT_PASSED
        )
        self.assertFalse(decision.eligible)
        self.assertTrue(any("trade_count 10" in item for item in decision.failures))
        self.assertTrue(any("symbol_count 1" in item for item in decision.failures))

    def test_live_stage_requires_promoted_manifest(self) -> None:
        # Candidate artifacts can complete research but are never live-authorizable.
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        self.add_passing_research_matrix()
        self.registry.promote("alpha", Lifecycle.VALIDATED)
        self.add_stage_evidence("HOLDOUT")
        self.registry.promote("alpha", Lifecycle.HOLDOUT_PASSED)
        self.registry.promote("alpha", Lifecycle.SHADOW)
        self.add_stage_evidence("SHADOW")
        self.registry.promote("alpha", Lifecycle.PAPER)
        self.add_stage_evidence("PAPER")
        decision = self.registry.assess_promotion("alpha", Lifecycle.CANARY)
        self.assertFalse(decision.eligible)
        self.assertTrue(any("source_root" in item for item in decision.failures))
        self.assertTrue(any("deployment_manifest" in item for item in decision.failures))

    def test_authorization_is_read_only_and_rejects_wrong_lifecycle(self) -> None:
        candidate_source = self.candidates / "auth.py"
        candidate_source.write_text("x = 1\n", encoding="utf-8")
        candidate = self.registry.register("auth", candidate_source)
        source = self.promoted / "auth.py"
        source.write_bytes(candidate_source.read_bytes())
        version = self.registry.register(
            "auth",
            source,
            parent_version=int(candidate["version"]),
            metadata=self.deployment_manifest(),
        )
        with self.assertRaisesRegex(
            DeploymentAuthorizationError, "lifecycle is IDEA"
        ):
            self.registry.deployment_authorization(
                "auth", int(version["version"]), Lifecycle.CANARY
            )
        self.assertEqual(
            self.registry.status("auth", version=int(version["version"]))["version"][
                "lifecycle"
            ],
            "IDEA",
        )

    def test_full_promotion_path_and_manual_live_approvals(self) -> None:
        candidate_source = self.candidates / "live.py"
        candidate_source.write_text("SIGNAL = 'live'\n", encoding="utf-8")
        candidate = self.registry.register("live", candidate_source)
        source = self.promoted / "live.py"
        source.write_bytes(candidate_source.read_bytes())
        version = self.registry.register(
            "live",
            source,
            parent_version=int(candidate["version"]),
            metadata=self.deployment_manifest(),
        )
        version_number = int(version["version"])
        self.registry.promote("live", Lifecycle.RESEARCH, version=version_number)
        self.add_passing_research_matrix("live", version=version_number)
        self.registry.promote("live", Lifecycle.VALIDATED, version=version_number)
        self.add_stage_evidence(
            "HOLDOUT", strategy="live", version=version_number
        )
        self.registry.promote(
            "live", Lifecycle.HOLDOUT_PASSED, version=version_number
        )
        self.registry.promote("live", Lifecycle.SHADOW, version=version_number)
        self.add_stage_evidence("SHADOW", strategy="live", version=version_number)
        self.registry.promote("live", Lifecycle.PAPER, version=version_number)
        self.add_stage_evidence("PAPER", strategy="live", version=version_number)

        with self.assertRaises(ManualApprovalRequired):
            self.registry.promote(
                "live", Lifecycle.CANARY, version=version_number
            )
        canary_approval = self.write_approval(
            "live",
            version_number,
            "CANARY",
            str(version["artifact_sha256"]),
            "Alice Risk",
        )
        unsafe_approval = self.promoted / "human-approval.json"
        unsafe_approval.write_bytes(canary_approval.read_bytes())
        with self.assertRaisesRegex(ApprovalArtifactError, "outside"):
            self.registry.promote(
                "live",
                Lifecycle.CANARY,
                version=version_number,
                manual_approval=True,
                approved_by="Alice Risk",
                approval_file=unsafe_approval,
                interactive=True,
            )
        with self.assertRaises(ManualApprovalRequired):
            self.registry.promote(
                "live",
                Lifecycle.CANARY,
                version=version_number,
                manual_approval=True,
                approved_by="Alice Risk",
                approval_file=canary_approval,
                interactive=False,
            )
        canary = self.registry.promote(
            "live",
            Lifecycle.CANARY,
            version=version_number,
            manual_approval=True,
            approved_by="Alice Risk",
            approval_file=canary_approval,
            interactive=True,
            reason="signed change ticket",
        )
        self.assertTrue(canary["manual_approval"])
        self.assertFalse(canary_approval.exists())
        self.assertTrue(Path(canary["approval_file_path"]).is_file())
        with self.assertRaisesRegex(
            ValidationError, "MCP cannot record evidence for a version in CANARY"
        ):
            self.registry.evaluate(
                "live",
                version=version_number,
                symbol="BTCUSDT",
                timeframe="1h",
                sample_type="BACKTEST",
                net_profit=1,
                profit_factor=1.3,
                max_drawdown=3,
                win_rate=55,
                trade_count=1,
                avg_trade=1,
                max_daily_loss_abs=1,
                research_only=True,
            )
        sibling = source.with_suffix(".json")
        sibling.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(
            DeploymentAuthorizationError, "sibling parameter"
        ):
            self.registry.deployment_authorization(
                "live", version_number, "CANARY"
            )
        sibling.unlink()
        authorization = self.registry.deployment_authorization(
            "live", version_number, "CANARY"
        )
        self.assertEqual(authorization["source_path"], str(source.resolve()))
        self.assertEqual(
            authorization["deployment_manifest"]["freqtrade_version"], "2026.7"
        )

        self.add_stage_evidence(
            "CANARY",
            strategy="live",
            version=version_number,
            net_profit=3,
            suffix="forward",
        )
        with self.assertRaises(ManualApprovalRequired):
            self.registry.promote(
                "live", Lifecycle.PRODUCTION, version=version_number
            )
        production_approval = self.write_approval(
            "live",
            version_number,
            "PRODUCTION",
            str(version["artifact_sha256"]),
            "Bob Ops",
        )
        production = self.registry.promote(
            "live",
            Lifecycle.PRODUCTION,
            version=version_number,
            manual_approval=True,
            approved_by="Bob Ops",
            approval_file=production_approval,
            interactive=True,
        )
        self.assertEqual(production["to_state"], "PRODUCTION")
        with self.assertRaisesRegex(
            ValidationError, "MCP cannot record evidence for a version in PRODUCTION"
        ):
            self.registry.evaluate(
                "live",
                version=version_number,
                symbol="BTCUSDT",
                timeframe="1h",
                sample_type="BACKTEST",
                net_profit=1,
                profit_factor=1.3,
                max_drawdown=3,
                win_rate=55,
                trade_count=1,
                avg_trade=1,
                max_daily_loss_abs=1,
                research_only=True,
            )
        status = self.registry.status("live")
        self.assertEqual(status["version"]["lifecycle"], "PRODUCTION")
        self.assertEqual(len(status["promotion_events"]), 7)
        authorized = self.registry.deployment_authorization(
            "live", version_number, "PRODUCTION"
        )
        self.assertEqual(authorized["artifact_sha256"], version["artifact_sha256"])
        self.assertEqual(authorized["risk_policy"]["max_capital"], 250.0)
        Path(production["approval_file_path"]).write_text(
            '{"tampered":true}\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(
            DeploymentAuthorizationError, "SHA-256"
        ):
            self.registry.deployment_authorization(
                "live", version_number, "PRODUCTION"
            )

    def test_negative_holdout_blocks_all_post_validation_stages(self) -> None:
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        self.add_passing_research_matrix()
        self.registry.promote("alpha", Lifecycle.VALIDATED)
        self.add_stage_evidence("HOLDOUT", net_profit=-1.0)
        decision = self.registry.assess_promotion("alpha", Lifecycle.HOLDOUT_PASSED)
        self.assertFalse(decision.eligible)
        self.assertTrue(any("net_profit" in failure for failure in decision.failures))

    def test_drawdown_and_cross_market_requirements_are_enforced(self) -> None:
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        for timeframe in ("1h", "4h"):
            self.registry.evaluate(
                "alpha",
                symbol="BTCUSDT",
                timeframe=timeframe,
                sample_type="BACKTEST",
                net_profit=10,
                profit_factor=1.5,
                max_drawdown=16,
                win_rate=60,
                trade_count=60,
                avg_trade=0.2,
            )
        decision = self.registry.assess_promotion("alpha", Lifecycle.VALIDATED)
        self.assertFalse(decision.eligible)
        self.assertTrue(any("max_drawdown" in failure for failure in decision.failures))
        self.assertTrue(any("symbol_count" in failure for failure in decision.failures))

    def test_safety_transitions_and_research_recovery(self) -> None:
        self.registry.promote("alpha", Lifecycle.RESEARCH)
        self.add_passing_research_matrix()
        self.registry.promote("alpha", Lifecycle.VALIDATED)
        self.add_stage_evidence("HOLDOUT")
        self.registry.promote("alpha", Lifecycle.HOLDOUT_PASSED)
        self.registry.promote("alpha", Lifecycle.SHADOW)
        self.registry.promote("alpha", Lifecycle.DEGRADED, reason="drift")
        recovered = self.registry.promote("alpha", Lifecycle.RESEARCH)
        self.assertEqual(recovered["to_state"], "RESEARCH")


class ConfigurableGateTests(unittest.TestCase):
    def test_gate_thresholds_can_only_be_tightened(self) -> None:
        tightened = GateCriteria(
            min_trade_count=200,
            min_profit_factor=1.5,
            max_drawdown_pct=10,
            min_symbols=3,
            min_timeframes=3,
        )
        self.assertEqual(tightened.min_trade_count, 200)
        insecure = (
            {"min_trade_count": 99},
            {"min_profit_factor": 1.19},
            {"max_drawdown_pct": 15.01},
            {"min_symbols": 1},
            {"min_timeframes": 1},
            {"require_positive_holdout": False},
        )
        for values in insecure:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                GateCriteria(**values)


if __name__ == "__main__":
    unittest.main()
