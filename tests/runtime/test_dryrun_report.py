from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from runtime.export_dryrun_report import build_report, main, render_markdown, write_reports


def _create_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                pair TEXT NOT NULL,
                is_open INTEGER NOT NULL,
                stake_amount REAL NOT NULL,
                open_date TEXT NOT NULL,
                close_date TEXT,
                close_profit_abs REAL,
                realized_profit REAL,
                open_rate REAL,
                close_rate REAL,
                exit_reason TEXT,
                strategy TEXT
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO trades (
                id, pair, is_open, stake_amount, open_date, close_date,
                close_profit_abs, realized_profit, open_rate, close_rate, exit_reason, strategy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    1,
                    "BTC/USDT",
                    0,
                    80.0,
                    "2026-08-11 23:00:00",
                    "2026-08-12 00:00:00",
                    5.5,
                    0.0,
                    100.0,
                    107.0,
                    "roi",
                    "TestStrategy",
                ),
                (
                    2,
                    "ETH/USDT",
                    0,
                    80.0,
                    "2026-08-12T12:00:00+00:00",
                    "2026-08-13T00:00:00Z",
                    -2.25,
                    0.0,
                    50.0,
                    48.0,
                    "stop_loss",
                    "TestStrategy",
                ),
                (
                    3,
                    "SOL/USDT",
                    1,
                    75.0,
                    "2026-08-13 00:00:00",
                    None,
                    9999.0,
                    0.0,
                    20.0,
                    None,
                    None,
                    "TestStrategy",
                ),
                (
                    4,
                    "BTC/USDT",
                    0,
                    40.0,
                    "2026-08-13 00:00:01",
                    "2026-08-13 00:00:01",
                    0.0,
                    0.0,
                    107.0,
                    107.0,
                    "force_exit",
                    "TestStrategy",
                ),
            ],
        )
        connection.commit()


class DryRunReportTests(unittest.TestCase):
    def test_cumulative_and_inclusive_session_statistics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "trades.sqlite"
            _create_database(database)

            report = build_report(
                database=database,
                starting_wallet=250.0,
                session_id="three-day-test",
                session_start_utc=datetime(2026, 8, 12, tzinfo=UTC),
                session_end_utc=datetime(2026, 8, 13, tzinfo=UTC),
                generated_at_utc=datetime(2026, 8, 14, tzinfo=UTC),
            )

            self.assertEqual(report["source"]["status"], "ok")
            self.assertEqual(report["cumulative"]["total_trade_count"], 4)
            self.assertEqual(report["cumulative"]["closed_trade_count"], 3)
            self.assertEqual(report["cumulative"]["open_trade_count"], 1)
            self.assertEqual(report["cumulative"]["open_stake_usdt"], 75.0)
            self.assertEqual(report["cumulative"]["wins"], 1)
            self.assertEqual(report["cumulative"]["losses"], 1)
            self.assertEqual(report["cumulative"]["breakeven"], 1)
            self.assertEqual(report["cumulative"]["realized_profit_usdt"], 3.25)
            self.assertEqual(
                report["cumulative"]["capital_after_realized_pnl_usdt"], 253.25
            )
            self.assertEqual(
                report["cumulative"]["realized_return_percent_of_starting_wallet"], 1.3
            )

            # Both exact boundary timestamps are included. Trade 4 is one second after.
            self.assertEqual(report["session"]["closed_trade_count"], 2)
            self.assertEqual(report["session"]["opened_trade_count"], 2)
            self.assertEqual(report["session"]["realized_profit_usdt"], 3.25)
            self.assertEqual(report["session"]["wins"], 1)
            self.assertEqual(report["session"]["losses"], 1)
            self.assertEqual(report["recent_trades"][0]["trade_id"], 4)
            open_trade = next(
                trade for trade in report["recent_trades"] if trade["trade_id"] == 3
            )
            self.assertIsNone(open_trade["closed_realized_profit_usdt"])
            self.assertEqual(open_trade["realized_profit_usdt"], 0.0)
            self.assertIn("Nicht realisierte", report["accounting_notice"])

    def test_partial_exit_of_open_trade_counts_only_in_cumulative_total(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "trades.sqlite"
            _create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE trades SET realized_profit = ? WHERE id = ?", (1.75, 3)
                )
                connection.commit()

            report = build_report(
                database=database,
                starting_wallet=250.0,
                session_id="partial-exit",
                session_start_utc=datetime(2026, 8, 12, tzinfo=UTC),
                session_end_utc=datetime(2026, 8, 13, tzinfo=UTC),
            )

            cumulative = report["cumulative"]
            self.assertEqual(cumulative["closed_realized_profit_usdt"], 3.25)
            self.assertEqual(cumulative["realized_profit_usdt"], 3.25)
            self.assertEqual(cumulative["open_trade_realized_profit_usdt"], 1.75)
            self.assertEqual(cumulative["total_realized_profit_usdt"], 5.0)
            self.assertEqual(cumulative["capital_after_realized_pnl_usdt"], 255.0)
            self.assertEqual(cumulative["realized_return_percent_of_starting_wallet"], 2.0)

            session = report["session"]
            self.assertEqual(session["realized_profit_usdt"], 3.25)
            self.assertEqual(session["open_trade_realized_profit_usdt_included"], 0.0)
            self.assertFalse(session["open_trade_realized_profit_included"])
            self.assertEqual(
                session["open_trade_realized_profit_attribution"],
                "excluded_no_order_timestamp",
            )
            self.assertIn(
                "keinen Zeitstempel",
                session["open_trade_realized_profit_attribution_notice"],
            )

            open_trade = next(
                trade for trade in report["recent_trades"] if trade["trade_id"] == 3
            )
            self.assertIsNone(open_trade["closed_realized_profit_usdt"])
            self.assertEqual(open_trade["open_trade_realized_profit_usdt"], 1.75)
            self.assertEqual(open_trade["total_realized_profit_usdt"], 1.75)
            markdown = render_markdown(report)
            self.assertIn("offener Trades (USDT) | 1.75000000", markdown)
            self.assertIn("keinen Zeitstempel", markdown)

    def test_closed_trade_with_null_close_profit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "trades.sqlite"
            _create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE trades SET close_profit_abs = NULL WHERE id = 1"
                )
                connection.commit()

            with self.assertRaisesRegex(
                RuntimeError, r"closed trade 1 has NULL close_profit_abs"
            ):
                build_report(
                    database=database,
                    starting_wallet=250.0,
                    session_id="invalid-null",
                )

    def test_session_filters_open_and_close_dates_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "trades.sqlite"
            _create_database(database)
            boundary = datetime(2026, 8, 13, tzinfo=UTC)

            report = build_report(
                database=database,
                starting_wallet=250.0,
                session_id="boundary",
                session_start_utc=boundary,
                session_end_utc=boundary,
            )

            self.assertEqual(report["session"]["closed_trade_count"], 1)
            self.assertEqual(report["session"]["realized_profit_usdt"], -2.25)
            self.assertEqual(report["session"]["opened_trade_count"], 1)

    def test_missing_database_produces_valid_zero_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "missing.sqlite"
            report = build_report(
                database=database,
                starting_wallet=250.0,
                session_id="no-trades",
            )

            self.assertFalse(database.exists())
            self.assertEqual(report["source"]["status"], "missing")
            self.assertEqual(report["cumulative"]["total_trade_count"], 0)
            self.assertEqual(report["cumulative"]["realized_profit_usdt"], 0.0)
            self.assertEqual(
                report["cumulative"]["capital_after_realized_pnl_usdt"], 250.0
            )
            self.assertEqual(report["session"]["opened_trade_count"], 0)
            self.assertEqual(report["recent_trades"], [])
            self.assertIn("noch keine Dry-run-Datenbank", render_markdown(report))

    def test_writes_predictable_json_and_markdown_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = build_report(
                database=root / "missing.sqlite",
                starting_wallet=250.0,
                session_id="Laptop / Test #1",
            )

            json_path, markdown_path = write_reports(
                report, output_dir=root / "reports", session_id=report["session_id"]
            )

            self.assertEqual(json_path.name, "dryrun-report-Laptop_Test_1.json")
            self.assertEqual(markdown_path.name, "dryrun-report-Laptop_Test_1.md")
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), report)
            self.assertIn(
                "# Testbot-Auswertung (Dry-run)", markdown_path.read_text(encoding="utf-8")
            )
            self.assertEqual(list((root / "reports").glob("*.tmp")), [])

    def test_cli_contract_and_missing_database_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = main(
                [
                    "--database",
                    str(root / "missing.sqlite"),
                    "--output-dir",
                    str(root / "reports"),
                    "--starting-wallet",
                    "250",
                    "--session-id",
                    "cli-test",
                    "--session-start-utc",
                    "2026-08-12T00:00:00Z",
                    "--session-end-utc",
                    "2026-08-13T00:00:00+00:00",
                ]
            )

            self.assertEqual(result, 0)
            payload = json.loads(
                (root / "reports" / "dryrun-report-cli-test.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["session"]["start_utc"], "2026-08-12T00:00:00Z")
            self.assertEqual(payload["session"]["end_utc"], "2026-08-13T00:00:00Z")

    def test_existing_database_is_never_modified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "trades.sqlite"
            _create_database(database)
            before = database.read_bytes()

            build_report(database=database, starting_wallet=250.0, session_id="readonly")

            self.assertEqual(database.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
