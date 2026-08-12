"""Export a read-only Freqtrade dry-run summary as JSON and Markdown.

This module deliberately uses only the Python standard library.  It never contacts an
exchange and never estimates unrealized profit for open positions.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
RECENT_TRADE_LIMIT = 20
REQUIRED_TRADE_COLUMNS = frozenset(
    {
        "id",
        "pair",
        "is_open",
        "stake_amount",
        "open_date",
        "close_date",
        "close_profit_abs",
    }
)
OPTIONAL_TRADE_COLUMNS = (
    "realized_profit",
    "open_rate",
    "close_rate",
    "exit_reason",
    "strategy",
)
UNREALIZED_NOTICE = (
    "Offene Positionen werden nicht zum aktuellen Marktpreis bewertet. Nicht realisierte "
    "Gewinne oder Verluste sind in allen Gewinn- und Kapitalwerten ausgeschlossen."
)
OPEN_REALIZED_SESSION_NOTICE = (
    "Bereits realisierte Gewinne oder Verluste offener Trades werden im Gesamtergebnis "
    "beruecksichtigt. Weil die Trade-Tabelle keinen Zeitstempel des partiellen Ausstiegs "
    "enthaelt, werden sie keiner Sitzung zugerechnet."
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc(value: str, *, argument: str) -> datetime:
    candidate = value.strip()
    if candidate.endswith(("Z", "z")):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"{argument} must be an ISO-8601 timestamp with a UTC offset"
        ) from error
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError(f"{argument} must include Z or a UTC offset")
    return parsed.astimezone(UTC)


def _parse_database_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.endswith(("Z", "z")):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as error:
            raise RuntimeError(f"Invalid UTC timestamp in trades database: {value!r}") from error
    else:
        raise RuntimeError(f"Unsupported timestamp value in trades database: {value!r}")

    # Freqtrade stores UTC timestamps without an offset in SQLite.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _finite_float(value: Any, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"Invalid numeric value for trades.{field}: {value!r}") from error
    if not math.isfinite(number):
        raise RuntimeError(f"Non-finite numeric value for trades.{field}: {value!r}")
    return number


def _money(value: float) -> float:
    rounded = round(value, 8)
    return 0.0 if rounded == 0 else rounded


def _in_inclusive_window(
    value: datetime | None, start: datetime | None, end: datetime | None
) -> bool:
    if value is None:
        return False
    return (start is None or value >= start) and (end is None or value <= end)


def _safe_session_component(session_id: str) -> str:
    component = re.sub(r"[^A-Za-z0-9._-]+", "_", session_id.strip()).strip("._-")
    if not component:
        raise ValueError("session-id must contain at least one letter or digit")
    return component[:80]


def _open_database_read_only(database: Path) -> sqlite3.Connection:
    uri = f"{database.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _read_trades(database: Path) -> list[dict[str, Any]]:
    if not database.is_file():
        raise RuntimeError(f"Dry-run database path is not a regular file: {database}")

    # sqlite3.Connection's own context manager does not close the handle on exit.
    # closing() matters on Windows, where an open read handle prevents cleanup/rotation.
    with closing(_open_database_read_only(database)) as connection:
        connection.execute("BEGIN")
        columns = {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(trades)").fetchall()
        }
        missing = sorted(REQUIRED_TRADE_COLUMNS - columns)
        if missing:
            raise RuntimeError(
                "Dry-run database has no compatible trades table; missing columns: "
                + ", ".join(missing)
            )
        selected = list(sorted(REQUIRED_TRADE_COLUMNS))
        selected.extend(column for column in OPTIONAL_TRADE_COLUMNS if column in columns)
        sql = "SELECT " + ", ".join(f'\"{column}\"' for column in selected) + " FROM trades"
        rows = connection.execute(sql).fetchall()

    trades: list[dict[str, Any]] = []
    for row in rows:
        available = set(row.keys())
        is_open = bool(row["is_open"])
        close_profit = row["close_profit_abs"]
        if not is_open and close_profit is None:
            raise RuntimeError(
                "Incompatible trades database: closed trade "
                f"{row['id']} has NULL close_profit_abs"
            )
        open_realized_profit = 0.0
        if is_open and "realized_profit" in available and row["realized_profit"] is not None:
            open_realized_profit = _finite_float(
                row["realized_profit"], field="realized_profit"
            )
        trade = {
            "trade_id": int(row["id"]),
            "pair": str(row["pair"]),
            "is_open": is_open,
            "stake_usdt": _finite_float(row["stake_amount"], field="stake_amount"),
            "open_date": _parse_database_datetime(row["open_date"]),
            "close_date": _parse_database_datetime(row["close_date"]),
            "closed_realized_profit_usdt": (
                None
                if is_open
                else _finite_float(close_profit, field="close_profit_abs")
            ),
            "open_trade_realized_profit_usdt": open_realized_profit,
            "open_rate": (
                _finite_float(row["open_rate"], field="open_rate")
                if "open_rate" in available and row["open_rate"] is not None
                else None
            ),
            "close_rate": (
                _finite_float(row["close_rate"], field="close_rate")
                if "close_rate" in available and row["close_rate"] is not None
                else None
            ),
            "exit_reason": (
                str(row["exit_reason"])
                if "exit_reason" in available and row["exit_reason"] is not None
                else None
            ),
            "strategy": (
                str(row["strategy"])
                if "strategy" in available and row["strategy"] is not None
                else None
            ),
        }
        trades.append(trade)
    return trades


def _closed_statistics(trades: Sequence[dict[str, Any]]) -> dict[str, int | float]:
    profits = [float(trade["closed_realized_profit_usdt"]) for trade in trades]
    closed_realized_profit = _money(sum(profits))
    return {
        "closed_trade_count": len(profits),
        "wins": sum(profit > 0 for profit in profits),
        "losses": sum(profit < 0 for profit in profits),
        "breakeven": sum(profit == 0 for profit in profits),
        # Keep realized_profit_usdt as the established closed-trade field.
        "realized_profit_usdt": closed_realized_profit,
        "closed_realized_profit_usdt": closed_realized_profit,
    }


def _public_trade(trade: dict[str, Any]) -> dict[str, Any]:
    return {
        "trade_id": trade["trade_id"],
        "pair": trade["pair"],
        "is_open": trade["is_open"],
        "stake_usdt": _money(float(trade["stake_usdt"])),
        "open_date_utc": _iso_utc(trade["open_date"]),
        "close_date_utc": _iso_utc(trade["close_date"]),
        "closed_realized_profit_usdt": (
            None
            if trade["closed_realized_profit_usdt"] is None
            else _money(float(trade["closed_realized_profit_usdt"]))
        ),
        "open_trade_realized_profit_usdt": _money(
            float(trade["open_trade_realized_profit_usdt"])
        ),
        "total_realized_profit_usdt": _money(
            float(trade["closed_realized_profit_usdt"] or 0.0)
            + float(trade["open_trade_realized_profit_usdt"])
        ),
        "realized_profit_usdt": _money(
            float(trade["closed_realized_profit_usdt"] or 0.0)
            + float(trade["open_trade_realized_profit_usdt"])
        ),
        "open_rate": trade["open_rate"],
        "close_rate": trade["close_rate"],
        "exit_reason": trade["exit_reason"],
        "strategy": trade["strategy"],
    }


def build_report(
    *,
    database: Path,
    starting_wallet: float,
    session_id: str,
    session_start_utc: datetime | None = None,
    session_end_utc: datetime | None = None,
    generated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build a report without writing to the database or contacting the network."""
    if not math.isfinite(starting_wallet) or starting_wallet <= 0:
        raise ValueError("starting-wallet must be a positive finite number")
    if not session_id.strip():
        raise ValueError("session-id must not be empty")
    if session_start_utc is not None:
        session_start_utc = session_start_utc.astimezone(UTC)
    if session_end_utc is not None:
        session_end_utc = session_end_utc.astimezone(UTC)
    if (
        session_start_utc is not None
        and session_end_utc is not None
        and session_start_utc > session_end_utc
    ):
        raise ValueError("session-start-utc must not be later than session-end-utc")

    database = database.resolve()
    database_exists = database.exists()
    trades = _read_trades(database) if database_exists else []
    closed = [trade for trade in trades if not trade["is_open"]]
    open_trades = [trade for trade in trades if trade["is_open"]]
    cumulative = _closed_statistics(closed)
    open_trade_realized_profit = _money(
        sum(float(trade["open_trade_realized_profit_usdt"]) for trade in open_trades)
    )
    total_realized_profit = _money(
        float(cumulative["closed_realized_profit_usdt"]) + open_trade_realized_profit
    )
    cumulative.update(
        {
            "total_trade_count": len(trades),
            "open_trade_count": len(open_trades),
            "open_stake_usdt": _money(
                sum(float(trade["stake_usdt"]) for trade in open_trades)
            ),
            "starting_wallet_usdt": _money(starting_wallet),
            "open_trade_realized_profit_usdt": open_trade_realized_profit,
            "total_realized_profit_usdt": total_realized_profit,
            "capital_after_realized_pnl_usdt": _money(
                starting_wallet + total_realized_profit
            ),
            "realized_return_percent_of_starting_wallet": _money(
                100.0 * total_realized_profit / starting_wallet
            ),
        }
    )

    session_closed = [
        trade
        for trade in closed
        if _in_inclusive_window(
            trade["close_date"], session_start_utc, session_end_utc
        )
    ]
    session = _closed_statistics(session_closed)
    session["realized_return_percent_of_starting_wallet"] = _money(
        100.0 * float(session["realized_profit_usdt"]) / starting_wallet
    )
    session["opened_trade_count"] = sum(
        _in_inclusive_window(trade["open_date"], session_start_utc, session_end_utc)
        for trade in trades
    )
    session["open_trade_realized_profit_usdt_included"] = 0.0
    session["open_trade_realized_profit_included"] = False
    session["open_trade_realized_profit_attribution"] = "excluded_no_order_timestamp"
    session["open_trade_realized_profit_attribution_notice"] = (
        OPEN_REALIZED_SESSION_NOTICE
    )

    def recent_key(trade: dict[str, Any]) -> tuple[datetime, int]:
        timestamp = trade["close_date"] or trade["open_date"] or datetime.min.replace(tzinfo=UTC)
        return timestamp, int(trade["trade_id"])

    recent = sorted(trades, key=recent_key, reverse=True)[:RECENT_TRADE_LIMIT]
    generated = generated_at_utc or _utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _iso_utc(generated),
        "session_id": session_id,
        "source": {
            "database": str(database),
            "database_exists": database_exists,
            "status": "ok" if database_exists else "missing",
        },
        "accounting_notice": UNREALIZED_NOTICE,
        "open_trade_realized_profit_session_notice": OPEN_REALIZED_SESSION_NOTICE,
        "cumulative": cumulative,
        "session": {
            "start_utc": _iso_utc(session_start_utc),
            "end_utc": _iso_utc(session_end_utc),
            "window_inclusive": True,
            **session,
        },
        "recent_trades": [_public_trade(trade) for trade in recent],
    }


def _markdown_cell(value: Any) -> str:
    if value is None:
        return "-"
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    cumulative = report["cumulative"]
    session = report["session"]
    source = report["source"]
    lines = [
        "# Testbot-Auswertung (Dry-run)",
        "",
        f"- Sitzung: `{_markdown_cell(report['session_id'])}`",
        f"- Erstellt (UTC): `{report['generated_at_utc']}`",
        f"- Datenbank: `{_markdown_cell(source['database'])}`",
        f"- Datenbankstatus: **{source['status']}**",
        "",
    ]
    if source["status"] == "missing":
        lines.extend(
            [
                "> Beim Erstellen dieses Berichts gab es noch keine Dry-run-Datenbank. "
                "Deshalb sind alle Werte null.",
                "",
            ]
        )
    lines.extend(
        [
            f"> {report['accounting_notice']}",
            "",
            "## Gesamter Testzeitraum",
            "",
            "| Kennzahl | Wert |",
            "| --- | ---: |",
            f"| Virtuelles Startkapital (USDT) | {cumulative['starting_wallet_usdt']:.8f} |",
            f"| Realisierter Gewinn/Verlust geschlossener Trades (USDT) | "
            f"{cumulative['closed_realized_profit_usdt']:.8f} |",
            f"| Bereits realisierter Gewinn/Verlust offener Trades (USDT) | "
            f"{cumulative['open_trade_realized_profit_usdt']:.8f} |",
            f"| Realisierter Gewinn/Verlust insgesamt (USDT) | "
            f"{cumulative['total_realized_profit_usdt']:.8f} |",
            f"| Rendite auf Startkapital, nur realisiert (%) | "
            f"{cumulative['realized_return_percent_of_starting_wallet']:.8f} |",
            f"| Startkapital plus realisiertes Ergebnis (USDT) | "
            f"{cumulative['capital_after_realized_pnl_usdt']:.8f} |",
            f"| Trades insgesamt | {cumulative['total_trade_count']} |",
            f"| Geschlossene Trades | {cumulative['closed_trade_count']} |",
            f"| Offene Trades | {cumulative['open_trade_count']} |",
            f"| Einsatz in offenen Trades (USDT) | {cumulative['open_stake_usdt']:.8f} |",
            f"| Gewinne / Verluste / unveraendert | {cumulative['wins']} / "
            f"{cumulative['losses']} / {cumulative['breakeven']} |",
            "",
            "## Diese Sitzung",
            "",
            f"Inklusives UTC-Zeitfenster: `{session['start_utc'] or '-unendlich'}` bis "
            f"`{session['end_utc'] or '+unendlich'}`.",
            "",
            f"> {session['open_trade_realized_profit_attribution_notice']}",
            "",
            "| Kennzahl | Wert |",
            "| --- | ---: |",
            f"| In diesem Zeitraum eroeffnet | {session['opened_trade_count']} |",
            f"| In diesem Zeitraum geschlossen | {session['closed_trade_count']} |",
            f"| Dabei realisierter Gewinn/Verlust (USDT) | "
            f"{session['realized_profit_usdt']:.8f} |",
            f"| Dabei realisierte Rendite auf Startkapital (%) | "
            f"{session['realized_return_percent_of_starting_wallet']:.8f} |",
            f"| Gewinne / Verluste / unveraendert | {session['wins']} / {session['losses']} / "
            f"{session['breakeven']} |",
            "",
            "## Letzte Trades",
            "",
            "| ID | Paar | Status | Eroeffnet UTC | Geschlossen UTC | Einsatz USDT | "
            "Realisiertes Ergebnis USDT | Exit-Grund |",
            "| ---: | --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for trade in report["recent_trades"]:
        state = "offen" if trade["is_open"] else "geschlossen"
        realized = f"{trade['total_realized_profit_usdt']:.8f}"
        lines.append(
            f"| {trade['trade_id']} | {_markdown_cell(trade['pair'])} | {state} | "
            f"{_markdown_cell(trade['open_date_utc'])} | "
            f"{_markdown_cell(trade['close_date_utc'])} | {trade['stake_usdt']:.8f} | "
            f"{realized} | {_markdown_cell(trade['exit_reason'])} |"
        )
    if not report["recent_trades"]:
        lines.append("| - | Noch keine Trades | - | - | - | 0.00000000 | - | - |")
    lines.append("")
    return "\n".join(lines)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_reports(
    report: dict[str, Any], *, output_dir: Path, session_id: str
) -> tuple[Path, Path]:
    output_dir = output_dir.resolve()
    component = _safe_session_component(session_id)
    json_path = output_dir / f"dryrun-report-{component}.json"
    markdown_path = output_dir / f"dryrun-report-{component}.md"
    json_text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    _atomic_write_text(json_path, json_text)
    _atomic_write_text(markdown_path, render_markdown(report))
    return json_path, markdown_path


def _positive_wallet(value: str) -> float:
    try:
        wallet = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("starting-wallet must be a number") from error
    if not math.isfinite(wallet) or wallet <= 0:
        raise argparse.ArgumentTypeError("starting-wallet must be a positive finite number")
    return wallet


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path, help="Freqtrade SQLite database")
    parser.add_argument("--output-dir", required=True, type=Path, help="Report directory")
    parser.add_argument("--starting-wallet", required=True, type=_positive_wallet)
    parser.add_argument("--session-id", required=True)
    parser.add_argument(
        "--session-start-utc",
        type=lambda value: _parse_utc(value, argument="session-start-utc"),
        default=None,
    )
    parser.add_argument(
        "--session-end-utc",
        type=lambda value: _parse_utc(value, argument="session-end-utc"),
        default=None,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        report = build_report(
            database=arguments.database,
            starting_wallet=arguments.starting_wallet,
            session_id=arguments.session_id,
            session_start_utc=arguments.session_start_utc,
            session_end_utc=arguments.session_end_utc,
        )
        json_path, markdown_path = write_reports(
            report, output_dir=arguments.output_dir, session_id=arguments.session_id
        )
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(
        json.dumps(
            {
                "json_report": str(json_path),
                "markdown_report": str(markdown_path),
                "database_status": report["source"]["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
