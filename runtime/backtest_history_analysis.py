"""Aggregate every preserved Testbot UI backtest without deleting raw evidence.

The UI intentionally stores one immutable directory per attempt.  This module
reads all completed Freqtrade ZIP exports, records incomplete attempts, and
writes a JSON plus a human-readable Markdown report.  Overlapping one- and
three-year windows are never presented as one compounded capital curve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

STRATEGY_NAME = "CompressionBreakout250"
_RUNTIME_ROOT = Path(__file__).resolve().parent
_DEFAULT_RESULTS_ROOT = _RUNTIME_ROOT / "user_data" / "backtest_results" / "ui"
_DEFAULT_STRATEGY = (
    _RUNTIME_ROOT / "user_data" / "strategies" / f"{STRATEGY_NAME}.py"
)
_VERSION_PATTERN = re.compile(r"\bV(?:ersion\s*)?(\d+(?:\.\d+)*)\b", re.IGNORECASE)


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
            names,
            ".json",
            excluded=("_config.json", ".meta.json", ".last_result.json"),
        )
        source_name = _entry_name(names, f"_{STRATEGY_NAME}.py")
        payload = json.loads(archive.read(result_name).decode("utf-8"))
        source = archive.read(source_name)

    strategy = _strategy_payload(payload)
    trades = [item for item in (strategy.get("trades") or []) if isinstance(item, dict)]
    digest = hashlib.sha256(source).hexdigest()
    days = _integer(strategy.get("backtest_days"))
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
    drawdown = _number(
        strategy.get("max_drawdown_account"), strategy.get("max_drawdown", 0.0)
    )
    if drawdown > 1.0:
        drawdown = _number(strategy.get("max_drawdown_account"))
    winrate = strategy.get("winrate")
    if winrate is None:
        winrate = wins / total_trades if total_trades else 0.0

    return {
        "status": "completed",
        "run_id": run_id,
        "archive": archive_path.name,
        "strategy": str(strategy.get("strategy_name") or STRATEGY_NAME),
        "strategy_version": _strategy_version(source, digest),
        "strategy_sha256": digest,
        "pair": _pair(strategy),
        "period_years": _period_years(days),
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
    by_hash: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in completed:
        by_hash[(run["strategy_sha256"], run["strategy_version"])].append(run)

    matrices = []
    for (digest, version), runs in by_hash.items():
        latest_by_cell: dict[tuple[str, int | None], dict[str, Any]] = {}
        for run in runs:
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
        expected = {
            (pair, years)
            for pair in ("BTC/USDT", "ETH/USDT", "SOL/USDT")
            for years in periods
        }
        complete = bool(periods) and expected == set(latest_by_cell)
        matrices.append(
            {
                "strategy_version": version,
                "strategy_sha256": digest,
                "all_runs": len(runs),
                "latest_cells": len(selected),
                "expected_cells": len(expected),
                "period_years": periods,
                "matrix_complete": complete,
                "current_six_run_matrix": complete and periods == [1, 3],
                "positive_cells": sum(run["profit_usdt"] > 0 for run in selected),
                "independent_profit_sum_usdt": round(
                    sum(run["profit_usdt"] for run in selected), 4
                ),
                "median_profit_pct": _median([run["profit_pct"] for run in selected]),
                "total_trades_across_overlapping_cells": sum(
                    run["trades"] for run in selected
                ),
                "worst_max_drawdown_pct": round(
                    max((run["max_drawdown_pct"] for run in selected), default=0.0), 2
                ),
                "latest_backtest_end": max(
                    (run["backtest_end"] for run in selected), default=""
                ),
            }
        )
    return sorted(
        matrices,
        key=lambda row: (row["latest_backtest_end"], row["strategy_version"]),
        reverse=True,
    )


def analyze_backtest_history(
    results_root: Path,
    *,
    current_strategy_path: Path | None = None,
) -> dict[str, Any]:
    results_root = results_root.resolve()
    records: list[dict[str, Any]] = []
    if results_root.is_dir():
        for run_dir in sorted(path for path in results_root.iterdir() if path.is_dir()):
            archives = sorted(run_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime_ns)
            if not archives:
                records.append(_incomplete_run(run_dir, "Kein Backtest-ZIP vorhanden"))
                continue
            archive = archives[-1]
            try:
                records.append(_read_archive(archive, run_dir.name))
            except (BadZipFile, json.JSONDecodeError, KeyError, OSError, ValueError) as exc:
                records.append(_incomplete_run(run_dir, f"Nicht lesbar: {exc}"))

    completed = [row for row in records if row["status"] == "completed"]
    incomplete = [row for row in records if row["status"] != "completed"]
    current_hash = None
    if current_strategy_path and current_strategy_path.is_file():
        current_hash = hashlib.sha256(current_strategy_path.read_bytes()).hexdigest()

    supplementary_archives = []
    if results_root.is_dir():
        supplementary_archives = sorted(
            path.name
            for path in results_root.iterdir()
            if path.is_file() and path.suffix.lower() in {".rar", ".7z", ".tar"}
        )

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "results_root": str(results_root),
        "current_strategy_sha256": current_hash,
        "summary": {
            "attempts": len(records),
            "completed": len(completed),
            "incomplete": len(incomplete),
            "strategy_snapshots": len({run["strategy_sha256"] for run in completed}),
            "supplementary_archives": supplementary_archives,
        },
        "strategy_matrices": _matrix_summaries(completed),
        "repeat_groups": _group_summaries(completed),
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
        },
    }


def _fmt(value: Any, digits: int = 2) -> str:
    return f"{_number(value):.{digits}f}"


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
        "",
        "> Ein- und Dreijahresfenster überschneiden sich. Summen sind deshalb nur",
        "> Vergleiche unabhängiger Tests und keine gemeinsam handelbare Kapitalkurve.",
        "",
        "## Letzter vollständiger Stand je Strategie-Snapshot",
        "",
        "| Version | Hash | Jahre | Zellen | Positiv | Unabhängige P/L-Summe | "
        "Median P/L | Trades* | Schlimmster DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
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
            "## Alle erfolgreichen Läufe",
            "",
            "| Lauf | Version | Paar | Jahre | Zeitraum | P/L | P/L % | Trades | "
            "Treffer | PF | Max DD |",
            "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for run in report["runs"]:
        period = f"{run['backtest_start'][:10]} - {run['backtest_end'][:10]}"
        lines.append(
            "| `{run}` | {version} | {pair} | {years} | {period} | {profit} | "
            "{profit_pct}% | {trades} | {winrate}% | {pf} | {drawdown}% |".format(
                run=run["run_id"],
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


def write_history_reports(
    results_root: Path,
    *,
    current_strategy_path: Path | None = None,
    output_json: Path | None = None,
    output_markdown: Path | None = None,
) -> dict[str, Any]:
    report = analyze_backtest_history(
        results_root,
        current_strategy_path=current_strategy_path,
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
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=_DEFAULT_RESULTS_ROOT)
    parser.add_argument("--current-strategy", type=Path, default=_DEFAULT_STRATEGY)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-markdown", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = write_history_reports(
        args.results_root,
        current_strategy_path=args.current_strategy,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
    )
    summary = report["summary"]
    print(
        "Backtest-Gesamtauswertung: "
        f"{summary['completed']} erfolgreich, {summary['incomplete']} unvollständig, "
        f"{summary['strategy_snapshots']} Strategie-Snapshots."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
