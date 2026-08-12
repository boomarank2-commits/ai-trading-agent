from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from local_trader.cli import main  # noqa: E402


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "registry.sqlite3"
        self.candidate = self.root / "candidate"
        self.promoted = self.root / "promoted"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def call(self, arguments: list[str]) -> tuple[int, dict, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = main(arguments, stdout=stdout, stderr=stderr)
        raw = stdout.getvalue() or stderr.getvalue()
        return code, json.loads(raw), stdout.getvalue(), stderr.getvalue()

    def initialize(self, *, database_first: bool = False) -> dict:
        core = [
            "init",
            "--candidate-root",
            str(self.candidate),
            "--promoted-root",
            str(self.promoted),
        ]
        arguments = (
            ["--db", str(self.database), *core]
            if database_first
            else [*core, "--db", str(self.database)]
        )
        code, payload, _, _ = self.call(arguments)
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        return payload

    def test_init_accepts_global_or_command_database_and_emits_sorted_json(self) -> None:
        _, _, stdout, _ = self.call(
            [
                "--db",
                str(self.database),
                "init",
                "--candidate-root",
                str(self.candidate),
                "--promoted-root",
                str(self.promoted),
            ]
        )
        self.assertTrue(stdout.startswith('{"command":"init","ok":true'))

    def test_register_evaluate_list_status_and_verify(self) -> None:
        self.initialize()
        source = self.candidate / "cli.py"
        source.write_text("RULE = 1\n", encoding="utf-8")
        code, registered, _, _ = self.call(
            [
                "register",
                "--db",
                str(self.database),
                "--name",
                "cli-alpha",
                "--source",
                str(source),
                "--metadata-json",
                '{"family":"trend"}',
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(registered["version"]["metadata"], {"family": "trend"})
        code, evaluation, _, _ = self.call(
            [
                "evaluate",
                "--db",
                str(self.database),
                "--strategy",
                "cli-alpha",
                "--symbol",
                "BTCUSDT",
                "--timeframe",
                "1h",
                "--sample-type",
                "BACKTEST",
                "--net-profit",
                "5",
                "--profit-factor",
                "1.3",
                "--max-drawdown",
                "10",
                "--win-rate",
                "55",
                "--trade-count",
                "100",
                "--avg-trade",
                "0.05",
                "--max-daily-loss-abs",
                "1.25",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(evaluation["evaluation"]["trade_count"], 100)
        for command, key in (("list", "strategies"), ("verify", "artifacts")):
            code, payload, _, _ = self.call(
                [command, "--db", str(self.database)]
            )
            self.assertEqual(code, 0)
            self.assertIn(key, payload)
        code, status, _, _ = self.call(
            [
                "status",
                "--db",
                str(self.database),
                "--strategy",
                "cli-alpha",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(status["status"]["version"]["strategy"], "cli-alpha")

    def test_cli_candidate_to_promoted_handoff(self) -> None:
        self.initialize()
        candidate = self.candidate / "handoff.py"
        candidate.write_text("RULE = 1\n", encoding="utf-8")
        code, first, _, _ = self.call(
            [
                "register",
                "--db",
                str(self.database),
                "--name",
                "handoff",
                "--source",
                str(candidate),
            ]
        )
        self.assertEqual(code, 0)
        promoted = self.promoted / "handoff.py"
        promoted.write_bytes(candidate.read_bytes())
        manifest = {
            "deployment_manifest": {
                "config_sha256": "a" * 64,
                "lock_sha256": "b" * 64,
                "imports_sha256": "c" * 64,
                "freqtrade_version": "2026.7",
            }
        }
        code, second, _, _ = self.call(
            [
                "register",
                "--db",
                str(self.database),
                "--name",
                "handoff",
                "--source",
                str(promoted),
                "--parent-version",
                "1",
                "--metadata-json",
                json.dumps(manifest),
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(second["version"]["lifecycle"], "IDEA")
        self.assertEqual(second["version"]["source_root"], "promoted")
        self.assertEqual(
            second["version"]["artifact_sha256"],
            first["version"]["artifact_sha256"],
        )
        self.assertFalse(second["version"]["active"])

    def test_errors_are_json_and_missing_db_is_rejected(self) -> None:
        code, payload, stdout, stderr = self.call(["list"])
        self.assertEqual(code, 2)
        self.assertFalse(payload["ok"])
        self.assertEqual(stdout, "")
        self.assertNotEqual(stderr, "")

    def test_tampered_verify_returns_code_three_with_json(self) -> None:
        self.initialize()
        source = self.candidate / "cli.py"
        source.write_text("RULE = 1\n", encoding="utf-8")
        self.call(
            [
                "register",
                "--db",
                str(self.database),
                "--name",
                "cli-alpha",
                "--source",
                str(source),
            ]
        )
        source.write_text("RULE = 2\n", encoding="utf-8")
        code, payload, _, _ = self.call(["verify", "--db", str(self.database)])
        self.assertEqual(code, 3)
        self.assertFalse(payload["valid"])
        self.assertFalse(payload["artifacts"][0]["valid"])

        code, payload, _, _ = self.call(
            [
                "verify",
                "--db",
                str(self.database),
                "--strategy",
                "cli-alpha",
            ]
        )
        self.assertEqual(code, 3)
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["artifacts"][0]["strategy"], "cli-alpha")

    def test_cli_promote_outputs_gate_rejection_as_json(self) -> None:
        self.initialize()
        source = self.candidate / "cli.py"
        source.write_text("RULE = 1\n", encoding="utf-8")
        self.call(
            [
                "register",
                "--db",
                str(self.database),
                "--name",
                "cli-alpha",
                "--source",
                str(source),
            ]
        )
        code, payload, _, stderr = self.call(
            [
                "promote",
                "--db",
                str(self.database),
                "--strategy",
                "cli-alpha",
                "--to",
                "PRODUCTION",
            ]
        )
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"]["type"], "ValidationError")
        self.assertIn("explicit --version", payload["error"]["message"])
        self.assertNotEqual(stderr, "")

        code, payload, _, _ = self.call(
            [
                "promote",
                "--db",
                str(self.database),
                "--strategy",
                "cli-alpha",
                "--version",
                "1",
                "--to",
                "CANARY",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("interactive TTY", payload["error"]["message"])

    def test_authorize_command_returns_launcher_contract(self) -> None:
        expected = {
            "strategy": "live",
            "version": 7,
            "version_id": 42,
            "target": "CANARY",
            "lifecycle": "CANARY",
            "source_path": "C:/safe/promoted/live.py",
            "source_root": "promoted",
            "artifact_sha256": "a" * 64,
            "artifact_size": 123,
            "risk_policy": {"max_capital": 250.0},
            "metadata": {"deployment_manifest": {"freqtrade_version": "2026.7"}},
            "deployment_manifest": {"freqtrade_version": "2026.7"},
        }

        class StubRegistry:
            def __init__(self, _database: str) -> None:
                pass

            def deployment_authorization(
                self, strategy: str, version: int, target: str
            ) -> dict:
                self_args = (strategy, version, target)
                if self_args != ("live", 7, "CANARY"):
                    raise AssertionError(self_args)
                return expected

        with patch("local_trader.cli.StrategyRegistry", StubRegistry):
            code, payload, stdout, stderr = self.call(
                [
                    "authorize",
                    "--db",
                    str(self.database),
                    "--strategy",
                    "live",
                    "--version",
                    "7",
                    "--target",
                    "CANARY",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload["authorization"], expected)
        self.assertEqual(stderr, "")
        self.assertTrue(stdout.startswith('{"authorization":'))


if __name__ == "__main__":
    unittest.main()
