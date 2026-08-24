"""Aggregate every preserved Testbot UI backtest without deleting raw evidence.

The UI intentionally stores one immutable directory per attempt.  This module
reads all completed Freqtrade ZIP exports, records incomplete attempts, and
writes a JSON plus a human-readable Markdown report.  Overlapping one- and
three-year windows are never presented as one compounded capital curve.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

try:
    from runtime.backtest_experiment import (
        DETAILED_EXPERIMENT_FIELDS,
        build_test_identity,
        config_contract,
        strategy_hashes,
    )
except ModuleNotFoundError:  # Direct execution from runtime/.
    from backtest_experiment import (
        DETAILED_EXPERIMENT_FIELDS,
        build_test_identity,
        config_contract,
        strategy_hashes,
    )

STRATEGY_NAME = "CompressionBreakout250"
_RUNTIME_ROOT = Path(__file__).resolve().parent
_DEFAULT_RESULTS_ROOT = _RUNTIME_ROOT / "user_data" / "backtest_results" / "ui"
_DEFAULT_STRATEGY = _RUNTIME_ROOT / "user_data" / "strategies" / f"{STRATEGY_NAME}.py"
_DEFAULT_LEDGER = _RUNTIME_ROOT.parent / "research" / "trial_ledger.csv"
_VERSION_PATTERN = re.compile(r"\bV(?:ersion\s*)?(\d+(?:\.\d+)*)\b", re.IGNORECASE)
_COMPARISON_METRICS = (
    "profit_usdt",
    "profit_pct",
    "trades",
    "winrate_pct",
    "profit_factor",
    "max_drawdown_pct",
    "capital_time_utilization_pct",
    "no_position_time_pct",
)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _rounded(value: Any, digits: int = 4) -> float:
    return round(_number(value), digits)


def _median(values: list[float], digits: int = 4) -> float:
    return round(statistics.median(values), digits) if values else 0.0


def _strategy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    strategies = payload.get("strategy")
    if not isinstance(strategies, dict):
        raise ValueError("Backtest JSON contains no strategy map")
    strategy = strategies.get(STRATEGY_NAME)
    if isinstance(strategy, dict):
        return strategy
    candidates = [value for value in strategies.values() if isinstance(value, dict)]
    if len(candidates) != 1:
        raise ValueError(f"Backtest JSON contains no unambiguous {STRATEGY_NAME} result")
    return candidates[0]


def _entry_name(names: list[str], suffix: str, *, excluded: tuple[str, ...] = ()) -> str:
    candidates = [
        name
        for name in names
        if name.lower().endswith(suffix.lower())
        and not any(name.lower().endswith(item.lower()) for item in excluded)
    ]
    if not candidates:
        raise ValueError(f"Archive entry *{suffix} is missing")
    return sorted(candidates)[0]


def _strategy_version(source: bytes, digest: str) -> str:
    text = source.decode("utf-8", errors="replace")
    match = _VERSION_PATTERN.search(text[:12000])
    if match:
        return f"V{match.group(1)}"
    description = text[:2000].lower()
    if "volatility-compression breakout baseline" in description:
        return "Baseline"
    if "multi-timeframe volatility breakout" in description:
        return "MTF-Baseline"
    return f"Hash {digest[:8]}"


def _period_years(backtest_days: int) -> int | None:
    if backtest_days <= 0:
        return None
    years = max(1, round(backtest_days / 365))
    return years if abs(backtest_days - years * 365) <= 7 else None


def _pair(strategy: dict[str, Any]) -> str:
    pairlist = strategy.get("pairlist")
    if isinstance(pairlist, list) and len(pairlist) == 1:
        return str(pairlist[0])
    if isinstance(pairlist, list) and len(pairlist) > 1:
        return "PORTFOLIO"
    rows = strategy.get("results_per_pair")
    if isinstance(rows, list):
        names = [
            str(row.get("key"))
            for row in rows
            if isinstance(row, dict) and row.get("key") not in {None, "TOTAL"}
        ]
        if len(names) == 1:
            return names[0]
    return "unbekannt"


def _parse_utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def capital_utilization_metrics(
    trades: list[dict[str, Any]],
    backtest_start: Any,
    backtest_end: Any,
    *,
    available_capital: float = 250.0,
) -> dict[str, float | int]:
    """Measure position time and the time of each actually filled entry chunk.

    Older implementations applied a trade's final aggregated ``stake_amount``
    from its original open time.  That overstates capital use when a second or
    third entry was filled days later.  Freqtrade exports every filled entry
    order, so position-adjusted runs can be measured at their real fill times.
    """

    start = _parse_utc(backtest_start)
    end = _parse_utc(backtest_end)
    total_hours = (end - start).total_seconds() / 3600.0
    if total_hours <= 0 or available_capital <= 0:
        return {
            "capital_time_utilization_pct": 0.0,
            "no_position_time_pct": 100.0,
            "average_open_positions": 0.0,
            "max_simultaneous_positions": 0,
            "total_entry_chunks": 0,
            "additional_entry_chunks": 0,
            "trades_with_multiple_entries": 0,
            "max_entries_per_trade": 0,
            "max_active_entry_chunks": 0,
            "max_deployed_capital_usdt": 0.0,
        }

    events: list[tuple[datetime, int, float, int]] = []
    total_entry_chunks = 0
    trades_with_multiple_entries = 0
    max_entries_per_trade = 0
    measured_trades = 0
    for trade in trades:
        try:
            opened = _parse_utc(trade.get("open_date"))
            closed = _parse_utc(trade.get("close_date"))
        except (TypeError, ValueError):
            continue

        entry_fills: list[tuple[datetime, float]] = []
        orders = trade.get("orders")
        entry_fee = max(0.0, _number(trade.get("fee_open")))
        if isinstance(orders, list):
            for order in orders:
                if not isinstance(order, dict) or order.get("ft_is_entry") is not True:
                    continue
                timestamp = _number(order.get("order_filled_timestamp"), -1.0)
                gross_cost = max(0.0, _number(order.get("cost")))
                stake_cost = gross_cost / (1.0 + entry_fee)
                if timestamp <= 0.0 or stake_cost <= 0.0:
                    continue
                # Freqtrade exports milliseconds; accepting seconds keeps the
                # history reader compatible with older preserved fixtures.
                seconds = timestamp / 1000.0 if timestamp >= 100_000_000_000 else timestamp
                try:
                    filled_at = datetime.fromtimestamp(seconds, tz=UTC)
                except (OSError, OverflowError, ValueError):
                    continue
                entry_fills.append((filled_at, stake_cost))

        if not entry_fills:
            fallback_stake = max(0.0, _number(trade.get("stake_amount")))
            if fallback_stake > 0.0:
                entry_fills = [(opened, fallback_stake)]

        entry_count = len(entry_fills)
        measured_trades += 1
        total_entry_chunks += entry_count
        trades_with_multiple_entries += int(entry_count > 1)
        max_entries_per_trade = max(max_entries_per_trade, entry_count)
        deployed_for_trade = sum(cost for _filled_at, cost in entry_fills)

        events.append((opened, 1, 0.0, 0))
        for filled_at, cost in entry_fills:
            events.append((filled_at, 0, cost, 1))
        events.append((closed, -1, -deployed_for_trade, -entry_count))

    last = start
    open_positions = 0
    deployed_capital = 0.0
    capital_hours = 0.0
    position_hours = 0.0
    no_position_hours = 0.0
    max_positions = 0
    active_entry_chunks = 0
    max_active_entry_chunks = 0
    max_deployed_capital = 0.0
    for event_time, position_delta, capital_delta, chunk_delta in sorted(events):
        if event_time <= start:
            open_positions += position_delta
            deployed_capital += capital_delta
            active_entry_chunks += chunk_delta
            max_positions = max(max_positions, open_positions)
            max_active_entry_chunks = max(max_active_entry_chunks, active_entry_chunks)
            max_deployed_capital = max(max_deployed_capital, deployed_capital)
            continue
        if event_time >= end:
            break
        elapsed_hours = (event_time - last).total_seconds() / 3600.0
        capital_hours += max(0.0, deployed_capital) * elapsed_hours
        position_hours += max(0, open_positions) * elapsed_hours
        if open_positions == 0:
            no_position_hours += elapsed_hours
        open_positions += position_delta
        deployed_capital += capital_delta
        active_entry_chunks += chunk_delta
        max_positions = max(max_positions, open_positions)
        max_active_entry_chunks = max(max_active_entry_chunks, active_entry_chunks)
        max_deployed_capital = max(max_deployed_capital, deployed_capital)
        last = event_time

    elapsed_hours = (end - last).total_seconds() / 3600.0
    capital_hours += max(0.0, deployed_capital) * elapsed_hours
    position_hours += max(0, open_positions) * elapsed_hours
    if open_positions == 0:
        no_position_hours += elapsed_hours

    return {
        "capital_time_utilization_pct": round(
            100.0 * capital_hours / (available_capital * total_hours), 2
        ),
        "no_position_time_pct": round(100.0 * no_position_hours / total_hours, 2),
        "average_open_positions": round(position_hours / total_hours, 3),
        "max_simultaneous_positions": max_positions,
        "total_entry_chunks": total_entry_chunks,
        "additional_entry_chunks": max(0, total_entry_chunks - measured_trades),
        "trades_with_multiple_entries": trades_with_multiple_entries,
        "max_entries_per_trade": max_entries_per_trade,
        "max_active_entry_chunks": max_active_entry_chunks,
        "max_deployed_capital_usdt": round(max_deployed_capital, 4),
    }


def _breakdown(trades: list[dict[str, Any]], field: str, fallback: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for trade in trades:
        label = str(trade.get(field) or fallback)
        row = grouped.setdefault(
            label,
            {"label": label, "trades": 0, "wins": 0, "profit_usdt": 0.0},
        )
        profit = _number(trade.get("profit_abs"))
        row["trades"] += 1
        row["wins"] += int(profit > 0)
        row["profit_usdt"] += profit
    return sorted(
        (
            {
                "label": row["label"],
                "trades": row["trades"],
                "wins": row["wins"],
                "profit_usdt": round(row["profit_usdt"], 4),
            }
            for row in grouped.values()
        ),
        key=lambda row: (-row["trades"], row["label"]),
    )


def _read_archive(archive_path: Path, run_id: str) -> dict[str, Any]:
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        result_name = _entry_name(
            [name for name in names if not name.startswith("audit/")],
            ".json",
            excluded=("_config.json", ".meta.json", ".last_result.json"),
        )
        source_name = _entry_name(names, f"_{STRATEGY_NAME}.py")
        payload = json.loads(archive.read(result_name).decode("utf-8"))
        source = archive.read(source_name)
        config_names = [name for name in names if name.lower().endswith("_config.json")]
        config = (
            json.loads(archive.read(sorted(config_names)[0]).decode("utf-8"))
            if config_names
            else {}
        )

    strategy = _strategy_payload(payload)
    trades = [item for item in (strategy.get("trades") or []) if isinstance(item, dict)]
    hashes = strategy_hashes(source)
    digest = hashes["strategy_sha256"]
    days = _integer(strategy.get("backtest_days"))
    pair = _pair(strategy)
    years = _period_years(days)
    identity = build_test_identity(
        strategy_source=source,
        pair=pair,
        years=years or 0,
        config=config_contract(config),
    )
    total_trades = _integer(
        strategy.get("total_trades"),
        _integer(strategy.get("trade_count"), len(trades)),
    )
    wins = _integer(
        strategy.get("wins"),
        sum(1 for trade in trades if _number(trade.get("profit_abs")) > 0),
    )
    losses = _integer(
        strategy.get("losses"),
        sum(1 for trade in trades if _number(trade.get("profit_abs")) < 0),
    )
    starting_balance = _number(strategy.get("starting_balance"), 250.0)
    profit_usdt = _number(strategy.get("profit_total_abs"))
    final_balance = _number(strategy.get("final_balance"), starting_balance + profit_usdt)
    if profit_usdt == 0.0 and final_balance != starting_balance:
        profit_usdt = final_balance - starting_balance
    profit_ratio = strategy.get("profit_total")
    if profit_ratio is None:
        profit_ratio = profit_usdt / starting_balance if starting_balance else 0.0
    drawdown = _number(strategy.get("max_drawdown_account"), strategy.get("max_drawdown", 0.0))
    if drawdown > 1.0:
        drawdown = _number(strategy.get("max_drawdown_account"))
    winrate = strategy.get("winrate")
    if winrate is None:
        winrate = wins / total_trades if total_trades else 0.0
    utilization = capital_utilization_metrics(
        trades,
        strategy.get("backtest_start"),
        strategy.get("backtest_end"),
        available_capital=starting_balance,
    )

    return {
        "status": "completed",
        "run_id": run_id,
        "archive": archive_path.name,
        "strategy": str(strategy.get("strategy_name") or STRATEGY_NAME),
        "strategy_version": _strategy_version(source, digest),
        "strategy_sha256": digest,
        "strategy_logic_sha256": hashes["strategy_logic_sha256"],
        "test_fingerprint": identity["test_fingerprint"],
        "test_protocol_version": identity["material"]["protocol_version"],
        "pair": pair,
        "period_years": years,
        "backtest_days": days,
        "backtest_start": str(strategy.get("backtest_start") or ""),
        "backtest_end": str(strategy.get("backtest_end") or ""),
        "starting_balance_usdt": round(starting_balance, 4),
        "final_balance_usdt": round(final_balance, 4),
        "profit_usdt": round(profit_usdt, 4),
        "profit_pct": round(_number(profit_ratio) * 100.0, 4),
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "draws": _integer(strategy.get("draws")),
        "winrate_pct": round(_number(winrate) * 100.0, 2),
        "profit_factor": _rounded(strategy.get("profit_factor")),
        "max_drawdown_pct": round(drawdown * 100.0, 2),
        "expectancy_usdt": _rounded(strategy.get("expectancy")),
        "sharpe": _rounded(strategy.get("sharpe")),
        "sortino": _rounded(strategy.get("sortino")),
        "calmar": _rounded(strategy.get("calmar")),
        **utilization,
        "entry_tag_breakdown": _breakdown(trades, "enter_tag", "ohne_entry_tag"),
        "exit_reason_breakdown": _breakdown(trades, "exit_reason", "ohne_exit_reason"),
    }


def _incomplete_run(run_dir: Path, reason: str) -> dict[str, Any]:
    log_path = run_dir / "backtest.log"
    return {
        "status": "incomplete",
        "run_id": run_dir.name,
        "reason": reason,
        "log_present": log_path.is_file(),
    }


def _group_summaries(completed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, int | None], list[dict[str, Any]]] = defaultdict(list)
    for run in completed:
        grouped[
            (
                run["strategy_sha256"],
                run["strategy_version"],
                run["pair"],
                run["period_years"],
            )
        ].append(run)

    summaries = []
    for (digest, version, pair, years), runs in grouped.items():
        latest = max(runs, key=lambda row: (row["backtest_end"], row["run_id"]))
        summaries.append(
            {
                "strategy_version": version,
                "strategy_sha256": digest,
                "pair": pair,
                "period_years": years,
                "runs": len(runs),
                "positive_runs": sum(run["profit_usdt"] > 0 for run in runs),
                "median_profit_usdt": _median([run["profit_usdt"] for run in runs]),
                "minimum_profit_usdt": round(min(run["profit_usdt"] for run in runs), 4),
                "maximum_profit_usdt": round(max(run["profit_usdt"] for run in runs), 4),
                "median_trades": _median([float(run["trades"]) for run in runs], 1),
                "median_winrate_pct": _median([run["winrate_pct"] for run in runs], 2),
                "latest_run_id": latest["run_id"],
                "latest_profit_usdt": latest["profit_usdt"],
            }
        )
    return sorted(
        summaries,
        key=lambda row: (
            row["strategy_version"],
            row["strategy_sha256"],
            row["pair"],
            row["period_years"] or 0,
        ),
    )


def _matrix_summaries(completed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    legacy_pairs = ("BTC/USDT", "ETH/USDT", "SOL/USDT")
    v12_12_pairs = (*legacy_pairs, "XRP/USDT", "BNB/USDT", "DOGE/USDT")
    v12_16_pairs = (*v12_12_pairs, "ADA/USDT")
    v12_17_pairs = (*v12_12_pairs, "LINK/USDT", "TRX/USDT", "LTC/USDT", "BCH/USDT")
    by_hash: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in completed:
        by_hash[(run["strategy_sha256"], run["strategy_version"])].append(run)

    matrices = []
    for (digest, version), runs in by_hash.items():
        matrix_runs = [run for run in runs if run["pair"] != "PORTFOLIO"]
        latest_by_cell: dict[tuple[str, int | None], dict[str, Any]] = {}
        for run in matrix_runs:
            cell = (run["pair"], run["period_years"])
            previous = latest_by_cell.get(cell)
            if previous is None or (run["backtest_end"], run["run_id"]) > (
                previous["backtest_end"],
                previous["run_id"],
            ):
                latest_by_cell[cell] = run
        selected = list(latest_by_cell.values())
        periods = sorted(
            {run["period_years"] for run in selected if run["period_years"] is not None}
        )
        if version == "V12.16":
            matrix_pairs = v12_16_pairs
        elif version in {"V12.17", "V12.18", "V12.19", "V12.20", "V12.21"}:
            matrix_pairs = v12_17_pairs
        elif version in {"V12.12", "V12.13", "V12.14", "V12.15"}:
            matrix_pairs = v12_12_pairs
        else:
            matrix_pairs = legacy_pairs
        expected = {(pair, years) for pair in matrix_pairs for years in periods}
        complete = bool(periods) and expected == set(latest_by_cell)
        matrices.append(
            {
                "strategy_version": version,
                "strategy_sha256": digest,
                "all_runs": len(runs),
                "portfolio_runs": sum(run["pair"] == "PORTFOLIO" for run in runs),
                "latest_cells": len(selected),
                "expected_cells": len(expected),
                "period_years": periods,
                "matrix_complete": complete,
                "matrix_pairs": list(matrix_pairs),
                "current_six_run_matrix": (
                    complete and matrix_pairs == legacy_pairs and periods == [1, 3]
                ),
                "current_twelve_cell_matrix": (
                    complete and matrix_pairs == v12_12_pairs and periods == [1, 3]
                ),
                "current_ten_pair_matrix": (
                    complete and matrix_pairs == v12_17_pairs
                ),
                "positive_cells": sum(run["profit_usdt"] > 0 for run in selected),
                "independent_profit_sum_usdt": round(
                    sum(run["profit_usdt"] for run in selected), 4
                ),
                "median_profit_pct": _median([run["profit_pct"] for run in selected]),
                "total_trades_across_overlapping_cells": sum(run["trades"] for run in selected),
                "worst_max_drawdown_pct": round(
                    max((run["max_drawdown_pct"] for run in selected), default=0.0), 2
                ),
                "latest_backtest_end": max((run["backtest_end"] for run in selected), default=""),
            }
        )
    return sorted(
        matrices,
        key=lambda row: (row["latest_backtest_end"], row["strategy_version"]),
        reverse=True,
    )


def _load_experiments(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return [
            {field: str(row.get(field) or "").strip() for field in DETAILED_EXPERIMENT_FIELDS}
            for row in reader
        ]


def _annotate_experiments(
    completed: list[dict[str, Any]], experiments: list[dict[str, str]]
) -> None:
    by_hash = {row["strategy_hash"]: row for row in experiments if row.get("strategy_hash")}
    for run in completed:
        experiment = by_hash.get(run["strategy_sha256"], {})
        run["experiment_id"] = experiment.get("experiment_id", "historisch-nicht-registriert")
        for field in (
            "parent_experiment_id",
            "hypothesis",
            "change_summary",
            "acceptance_criteria",
            "result_summary",
            "decision",
            "lessons",
            "next_experiment",
        ):
            run[field] = experiment.get(field, "")


def _duplicate_groups(completed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in completed:
        grouped[run["test_fingerprint"]].append(run)

    duplicates: list[dict[str, Any]] = []
    for fingerprint, runs in grouped.items():
        ordered = sorted(runs, key=lambda row: (row["backtest_end"], row["run_id"]))
        canonical = ordered[0]
        for duplicate in ordered[1:]:
            duplicate["duplicate_of"] = canonical["run_id"]
        if len(ordered) > 1:
            duplicates.append(
                {
                    "test_fingerprint": fingerprint,
                    "strategy_version": canonical["strategy_version"],
                    "strategy_logic_sha256": canonical["strategy_logic_sha256"],
                    "pair": canonical["pair"],
                    "period_years": canonical["period_years"],
                    "canonical_run_id": canonical["run_id"],
                    "duplicate_run_ids": [row["run_id"] for row in ordered[1:]],
                }
            )
    return sorted(duplicates, key=lambda row: row["canonical_run_id"])


def _history_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "run_id",
        "experiment_id",
        "parent_experiment_id",
        "strategy_version",
        "strategy_sha256",
        "strategy_logic_sha256",
        "test_fingerprint",
        "pair",
        "period_years",
        "backtest_start",
        "backtest_end",
        "profit_usdt",
        "profit_pct",
        "trades",
        "wins",
        "losses",
        "winrate_pct",
        "profit_factor",
        "max_drawdown_pct",
        "capital_time_utilization_pct",
        "no_position_time_pct",
        "total_entry_chunks",
        "additional_entry_chunks",
        "max_active_entry_chunks",
        "max_deployed_capital_usdt",
        "hypothesis",
        "change_summary",
        "acceptance_criteria",
        "result_summary",
        "decision",
        "lessons",
        "next_experiment",
    )
    return {field: run.get(field) for field in fields}


def build_pair_history_context(
    report: dict[str, Any],
    *,
    pair: str,
    years: int,
    current_run_id: str | None = None,
) -> dict[str, Any]:
    """Return the immutable same-pair/same-period learning history for one run."""

    candidates = [
        run
        for run in report.get("runs", [])
        if run.get("pair") == pair and run.get("period_years") == years
    ]
    candidates.sort(key=lambda row: (row.get("backtest_end", ""), row.get("run_id", "")))
    current = next(
        (run for run in candidates if run.get("run_id") == current_run_id),
        candidates[-1] if candidates else None,
    )
    previous = None
    if current is not None:
        for candidate in reversed(candidates):
            if candidate.get("run_id") == current.get("run_id"):
                continue
            if candidate.get("test_fingerprint") == current.get("test_fingerprint"):
                continue
            previous = candidate
            break

    deltas = None
    if current is not None and previous is not None:
        deltas = {
            metric: round(_number(current.get(metric)) - _number(previous.get(metric)), 4)
            for metric in _COMPARISON_METRICS
        }

    if current is None:
        assessment = "Für diese Paar-/Zeitraumzelle liegt noch kein vollständiger Lauf vor."
    elif previous is None:
        assessment = "Erster erhaltener Vergleichslauf für diese Paar-/Zeitraumzelle."
    else:
        profit_delta = _number(deltas.get("profit_usdt") if deltas else 0.0)
        drawdown_delta = _number(deltas.get("max_drawdown_pct") if deltas else 0.0)
        profit_assessment = (
            "verbessert"
            if profit_delta > 0
            else "verschlechtert"
            if profit_delta < 0
            else "unverändert"
        )
        drawdown_assessment = (
            "gesunken"
            if drawdown_delta < 0
            else "gestiegen"
            if drawdown_delta > 0
            else "unverändert"
        )
        assessment = (
            f"Gewinn {profit_assessment} "
            f"um {profit_delta:+.2f} USDT; Drawdown "
            f"{drawdown_assessment} "
            f"um {abs(drawdown_delta):.2f} Prozentpunkte."
        )

    return {
        "schema_version": 1,
        "pair": pair,
        "years": years,
        "comparison_scope": "same_pair_same_period_previous_material_strategy",
        "current": _history_run_summary(current) if current is not None else None,
        "previous": _history_run_summary(previous) if previous is not None else None,
        "delta_vs_previous": deltas,
        "assessment_de": assessment,
        "all_preserved_runs": [_history_run_summary(run) for run in reversed(candidates)],
        "duplicate_execution_allowed": False,
    }


def _pair_histories(completed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    shell = {"runs": completed}
    cells = sorted(
        {
            (str(run["pair"]), int(run["period_years"]))
            for run in completed
            if run.get("pair") != "PORTFOLIO" and run.get("period_years") is not None
        }
    )
    return [
        build_pair_history_context(shell, pair=pair, years=years)
        for pair, years in cells
    ]


def analyze_backtest_history(
    results_root: Path,
    *,
    current_strategy_path: Path | None = None,
    trial_ledger_path: Path | None = _DEFAULT_LEDGER,
) -> dict[str, Any]:
    results_root = results_root.resolve()
    records: list[dict[str, Any]] = []
    if results_root.is_dir():
        for run_dir in sorted(
            path
            for path in results_root.iterdir()
            if path.is_dir() and not path.name.startswith("_")
        ):
            archives = sorted(run_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime_ns)
            if not archives:
                records.append(_incomplete_run(run_dir, "Kein Backtest-ZIP vorhanden"))
                continue
            archive = archives[-1]
            try:
                record = _read_archive(archive, run_dir.name)
                plan_path = run_dir / "experiment-plan.json"
                result_path = run_dir / "experiment-result.json"
                if plan_path.is_file():
                    record["experiment_plan"] = json.loads(plan_path.read_text(encoding="utf-8"))
                if result_path.is_file():
                    record["experiment_result"] = json.loads(
                        result_path.read_text(encoding="utf-8")
                    )
                    if record["experiment_result"].get("outcome") == "failed":
                        record["status"] = "incomplete"
                        record["reason"] = (
                            "Simulation erzeugte ein ZIP, aber der Laufvertrag schlug fehl: "
                            + str(record["experiment_result"].get("error") or "unbekannt")
                        )
                records.append(record)
            except (BadZipFile, json.JSONDecodeError, KeyError, OSError, ValueError) as exc:
                records.append(_incomplete_run(run_dir, f"Nicht lesbar: {exc}"))

    completed = [row for row in records if row["status"] == "completed"]
    incomplete = [row for row in records if row["status"] != "completed"]
    experiments = _load_experiments(trial_ledger_path)
    _annotate_experiments(completed, experiments)
    duplicate_groups = _duplicate_groups(completed)
    duplicate_runs = sum(len(row["duplicate_run_ids"]) for row in duplicate_groups)
    current_hash = None
    current_logic_hash = None
    if current_strategy_path and current_strategy_path.is_file():
        current_hashes = strategy_hashes(current_strategy_path.read_bytes())
        current_hash = current_hashes["strategy_sha256"]
        current_logic_hash = current_hashes["strategy_logic_sha256"]

    supplementary_archives = []
    if results_root.is_dir():
        supplementary_archives = sorted(
            path.name
            for path in results_root.iterdir()
            if path.is_file() and path.suffix.lower() in {".rar", ".7z", ".tar"}
        )

    return {
        "schema_version": 2,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "results_root": str(results_root),
        "current_strategy_sha256": current_hash,
        "current_strategy_logic_sha256": current_logic_hash,
        "summary": {
            "attempts": len(records),
            "completed": len(completed),
            "incomplete": len(incomplete),
            "strategy_snapshots": len({run["strategy_sha256"] for run in completed}),
            "unique_material_tests": len(completed) - duplicate_runs,
            "duplicate_runs": duplicate_runs,
            "duplicate_groups": len(duplicate_groups),
            "supplementary_archives": supplementary_archives,
        },
        "experiment_ledger": experiments,
        "duplicate_test_groups": duplicate_groups,
        "strategy_matrices": _matrix_summaries(completed),
        "repeat_groups": _group_summaries(completed),
        "pair_histories": _pair_histories(completed),
        "runs": sorted(
            completed,
            key=lambda row: (row["backtest_end"], row["run_id"]),
            reverse=True,
        ),
        "incomplete_runs": incomplete,
        "interpretation_contract": {
            "overlapping_windows_compounded": False,
            "profit_sums_are_independent_scenario_sums": True,
            "backtests_guarantee_future_profit": False,
            "identical_material_fingerprints_allowed_for_new_runs": False,
            "metadata_only_changes_create_new_test": False,
        },
    }


def _fmt(value: Any, digits: int = 2) -> str:
    return f"{_number(value):.{digits}f}"


def _cell(value: Any, limit: int = 120) -> str:
    text = str(value or "-").replace("|", "/").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Gesamtauswertung aller Testbot-Backtests",
        "",
        f"Erzeugt: `{report['generated_at_utc']}`",
        "",
        f"- Versuche: **{summary['attempts']}**",
        f"- Erfolgreich auswertbar: **{summary['completed']}**",
        f"- Unvollständig/abgebrochen: **{summary['incomplete']}**",
        f"- Unterschiedliche Strategie-Snapshots: **{summary['strategy_snapshots']}**",
        f"- Einzigartige inhaltliche Tests: **{summary['unique_material_tests']}**",
        f"- Historisch erkannte 1:1-Doppelläufe: **{summary['duplicate_runs']}**",
        "",
        "> Ein- und Dreijahresfenster überschneiden sich. Summen sind deshalb nur",
        "> Vergleiche unabhängiger Tests und keine gemeinsam handelbare Kapitalkurve.",
        "",
        "## Lückenlose Experimentkette",
        "",
        "| Experiment | Vorgänger | Version | Genau geändert | "
        "Ergebnis/Entscheidung | Nächster Schritt |",
        "|---|---|---|---|---|---|",
    ]
    for experiment in report["experiment_ledger"]:
        lines.append(
            "| {experiment} | {parent} | {version} | {change} | {decision} | {next} |".format(
                experiment=_cell(experiment["experiment_id"], 35),
                parent=_cell(experiment["parent_experiment_id"], 35),
                version=_cell(experiment["strategy_version"], 15),
                change=_cell(experiment["change_summary"]),
                decision=_cell(f"{experiment['result_summary']} — {experiment['decision']}"),
                next=_cell(experiment["next_experiment"]),
            )
        )
    lines.extend(
        [
            "",
            "## Letzter vollständiger Stand je Strategie-Snapshot",
            "",
            "| Version | Hash | Jahre | Zellen | Positiv | Unabhängige P/L-Summe | "
            "Median P/L | Trades* | Schlimmster DD |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for matrix in report["strategy_matrices"]:
        cells = f"{matrix['latest_cells']}/{matrix['expected_cells']}" + (
            "" if matrix["matrix_complete"] else " (unvollständig)"
        )
        lines.append(
            "| {version} | `{digest}` | {periods} | {cells} | {positive} | "
            "{profit} USDT | "
            "{median}% | {trades} | {drawdown}% |".format(
                version=matrix["strategy_version"],
                digest=matrix["strategy_sha256"][:8],
                periods=", ".join(str(year) for year in matrix["period_years"]),
                cells=cells,
                positive=matrix["positive_cells"],
                profit=_fmt(matrix["independent_profit_sum_usdt"]),
                median=_fmt(matrix["median_profit_pct"]),
                trades=matrix["total_trades_across_overlapping_cells"],
                drawdown=_fmt(matrix["worst_max_drawdown_pct"]),
            )
        )
    lines.extend(
        [
            "",
            "\\* Trades aus überlappenden Zeitfenstern dürfen nicht additiv als echte "
            "Handelsserie gelesen werden.",
            "",
            "## Wiederholungen nach Version, Paar und Zeitraum",
            "",
            "| Version | Paar | Jahre | Läufe | Positiv | Median P/L | Min | Max | Letzter P/L |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for group in report["repeat_groups"]:
        lines.append(
            "| {version} | {pair} | {years} | {runs} | {positive} | {median} USDT | "
            "{minimum} | {maximum} | {latest} |".format(
                version=group["strategy_version"],
                pair=group["pair"],
                years=group["period_years"] or "?",
                runs=group["runs"],
                positive=group["positive_runs"],
                median=_fmt(group["median_profit_usdt"]),
                minimum=_fmt(group["minimum_profit_usdt"]),
                maximum=_fmt(group["maximum_profit_usdt"]),
                latest=_fmt(group["latest_profit_usdt"]),
            )
        )
    lines.extend(
        [
            "",
            "## Erkannte 1:1-Doppeltests",
            "",
            "Gleiche Strategie-Logik, Pair, Laufzeit, Konfiguration und dasselbe "
            "Backtest-Protokoll ergeben denselben Fingerabdruck. Diese historischen "
            "Rohdaten bleiben erhalten; neue identische Läufe werden vor dem Start blockiert.",
            "",
        ]
    )
    if report["duplicate_test_groups"]:
        lines.extend(
            [
                "| Version | Pair | Jahre | Original | Doppelläufe | Fingerabdruck |",
                "|---|---|---:|---|---|---|",
            ]
        )
        for group in report["duplicate_test_groups"]:
            lines.append(
                (
                    "| {version} | {pair} | {years} | `{original}` | "
                    "{duplicates} | `{fingerprint}` |"
                ).format(
                    version=group["strategy_version"],
                    pair=group["pair"],
                    years=group["period_years"] or "?",
                    original=group["canonical_run_id"],
                    duplicates=", ".join(f"`{run_id}`" for run_id in group["duplicate_run_ids"]),
                    fingerprint=group["test_fingerprint"][:12],
                )
            )
    else:
        lines.append("Keine 1:1-Doppeltests erkannt.")
    lines.extend(
        [
            "",
            "## Alle erfolgreichen Läufe",
            "",
            "| Lauf | Experiment | Version | Paar | Jahre | Zeitraum | P/L | P/L % | Trades | "
            "Treffer | PF | Max DD | Kapitalzeit | Ohne Position |",
            "|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for run in report["runs"]:
        period = f"{run['backtest_start'][:10]} - {run['backtest_end'][:10]}"
        lines.append(
            "| `{run}` | {experiment} | {version} | {pair} | {years} | {period} | {profit} | "
            "{profit_pct}% | {trades} | {winrate}% | {pf} | {drawdown}% | "
            "{capital_time}% | {no_position}% |".format(
                run=run["run_id"],
                experiment=run["experiment_id"]
                + (f" (Duplikat von {run['duplicate_of']})" if run.get("duplicate_of") else ""),
                version=run["strategy_version"],
                pair=run["pair"],
                years=run["period_years"] or "?",
                period=period,
                profit=_fmt(run["profit_usdt"]),
                profit_pct=_fmt(run["profit_pct"]),
                trades=run["trades"],
                winrate=_fmt(run["winrate_pct"]),
                pf=_fmt(run["profit_factor"]),
                drawdown=_fmt(run["max_drawdown_pct"]),
                capital_time=_fmt(run["capital_time_utilization_pct"]),
                no_position=_fmt(run["no_position_time_pct"]),
            )
        )
    if report["incomplete_runs"]:
        lines.extend(["", "## Unvollständige Versuche", ""])
        for run in report["incomplete_runs"]:
            lines.append(f"- `{run['run_id']}`: {run['reason']}")
    if summary["supplementary_archives"]:
        names = ", ".join(f"`{name}`" for name in summary["supplementary_archives"])
        lines.extend(
            [
                "",
                "## Zusätzlich erhaltene Archive",
                "",
                f"Nicht doppelt gezählt: {names}.",
            ]
        )
    lines.extend(
        [
            "",
            "## Bewertungsgrenze",
            "",
            "Die Auswertung bewahrt jeden Roh-Lauf und vergleicht Ergebnisse, sie beweist "
            "aber keine",
            "zukünftige Rendite. Überlappende Zeiträume, wiederholte Tests und unterschiedliche",
            "Strategie-Hashes werden bewusst nicht zu einer einzigen Gewinnkurve vermischt.",
            "",
        ]
    )
    return "\n".join(lines)


def render_pair_history_markdown(history: dict[str, Any]) -> str:
    pair = str(history["pair"])
    years = int(history["years"])
    lines = [
        f"# Backtest-Historie {pair} · {years} Jahr{'e' if years != 1 else ''}",
        "",
        "Diese Akte vergleicht ausschließlich dasselbe Pair und dieselbe Laufzeit. ",
        "Unterschiedliche Strategie-Hashes bleiben getrennte Versuche; identische ",
        "Fingerabdrücke dürfen nicht erneut ausgeführt werden.",
        "",
        f"Aktuelle Bewertung: **{history['assessment_de']}**",
        "",
        "| Lauf | Experiment | Version | Zeitraum | P/L | Trades | PF | Max DD | Kapitalzeit |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for run in history["all_preserved_runs"]:
        start = str(run.get("backtest_start") or "")[:10]
        end = str(run.get("backtest_end") or "")[:10]
        period = f"{start} bis {end}"
        lines.append(
            "| `{run}` | {experiment} | {version} | {period} | {profit:+.2f} USDT | "
            "{trades} | {pf:.2f} | {dd:.2f}% | {capital:.2f}% |".format(
                run=run.get("run_id") or "?",
                experiment=run.get("experiment_id") or "historisch-nicht-registriert",
                version=run.get("strategy_version") or "?",
                period=period,
                profit=_number(run.get("profit_usdt")),
                trades=_integer(run.get("trades")),
                pf=_number(run.get("profit_factor")),
                dd=_number(run.get("max_drawdown_pct")),
                capital=_number(run.get("capital_time_utilization_pct")),
            )
        )
    current = history.get("current") or {}
    previous = history.get("previous") or {}
    delta = history.get("delta_vs_previous") or {}
    lines.extend(["", "## Letzte Änderung gegenüber dem Vorgänger", ""])
    if previous:
        lines.extend(
            [
                f"- Vorgänger: `{previous.get('run_id')}` / {previous.get('strategy_version')}",
                f"- Aktuell: `{current.get('run_id')}` / {current.get('strategy_version')}",
                f"- Gewinnänderung: {_number(delta.get('profit_usdt')):+.2f} USDT",
                f"- Tradeänderung: {_integer(delta.get('trades')):+d}",
                f"- Profit-Faktor-Änderung: {_number(delta.get('profit_factor')):+.2f}",
                f"- Drawdown-Änderung: {_number(delta.get('max_drawdown_pct')):+.2f} Prozentpunkte",
                f"- Vorgänger-Änderung: {previous.get('change_summary') or 'nicht dokumentiert'}",
                f"- Vorgänger-Ergebnis: {previous.get('result_summary') or 'nicht dokumentiert'}",
                f"- Aktuelle Hypothese: {current.get('hypothesis') or 'nicht dokumentiert'}",
                f"- Aktuelle Änderung: {current.get('change_summary') or 'nicht dokumentiert'}",
                f"- Erfolgskriterium: {current.get('acceptance_criteria') or 'nicht dokumentiert'}",
                f"- Ergebnis: {current.get('result_summary') or 'noch nicht im Ledger bewertet'}",
                f"- Entscheidung: {current.get('decision') or 'noch offen'}",
                f"- Erkenntnis: {current.get('lessons') or 'noch offen'}",
                f"- Nächster Versuch: {current.get('next_experiment') or 'noch offen'}",
            ]
        )
    else:
        lines.append("Kein älterer materiell unterschiedlicher Vergleichslauf vorhanden.")
    lines.extend(
        [
            "",
            "## Forschungsregel",
            "",
            "Ein weiterer Lauf dieser Zelle benötigt eine echte, vorab dokumentierte Änderung ",
            "der Bot-/Strategielogik oder des fest definierten Testprotokolls. Der Backtest ",
            "selbst optimiert keine Parameter.",
            "",
        ]
    )
    return "\n".join(lines)


def write_history_reports(
    results_root: Path,
    *,
    current_strategy_path: Path | None = None,
    trial_ledger_path: Path | None = _DEFAULT_LEDGER,
    output_json: Path | None = None,
    output_markdown: Path | None = None,
) -> dict[str, Any]:
    report = analyze_backtest_history(
        results_root,
        current_strategy_path=current_strategy_path,
        trial_ledger_path=trial_ledger_path,
    )
    output_json = output_json or results_root / "gesamt-auswertung.json"
    output_markdown = output_markdown or results_root / "GESAMTAUSWERTUNG.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_markdown.write_text(render_markdown(report), encoding="utf-8")
    pair_report_root = results_root / "_PAIR_HISTORIEN"
    pair_report_root.mkdir(parents=True, exist_ok=True)
    for history in report["pair_histories"]:
        stem = f"{str(history['pair']).replace('/', '_')}-{history['years']}J"
        (pair_report_root / f"{stem}.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (pair_report_root / f"{stem}.md").write_text(
            render_pair_history_markdown(history),
            encoding="utf-8",
        )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=_DEFAULT_RESULTS_ROOT)
    parser.add_argument("--current-strategy", type=Path, default=_DEFAULT_STRATEGY)
    parser.add_argument("--trial-ledger", type=Path, default=_DEFAULT_LEDGER)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-markdown", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = write_history_reports(
        args.results_root,
        current_strategy_path=args.current_strategy,
        trial_ledger_path=args.trial_ledger,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
    )
    summary = report["summary"]
    print(
        "Backtest-Gesamtauswertung: "
        f"{summary['completed']} erfolgreich, {summary['incomplete']} unvollständig, "
        f"{summary['strategy_snapshots']} Strategie-Snapshots, "
        f"{summary['duplicate_runs']} historische Doppelläufe."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
