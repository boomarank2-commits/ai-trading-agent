"""Local-only backtest API used by the Testbot FreqUI extension.

Every run hashes and loads the exact strategy file used by STARTBOT. V12.12 can
test one selected pair or the real six-pair 250 USDT portfolio. All pairs remain
independent pair-local engines; portfolio mode changes only the execution/account
simulation and injects no cross-pair market-regime signal.

The result also exposes entry-tag and exit-reason attribution so new challengers
can be judged independently instead of hiding behind aggregate P/L.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import Response

try:
    from runtime.backtest_experiment import (
        build_run_plan,
        build_test_identity,
        current_git_commit,
        find_archived_strategy_source,
        load_config_contract,
        registered_experiment,
        strategy_change_diff,
        strategy_hashes,
    )
    from runtime.backtest_history_analysis import (
        analyze_backtest_history,
        capital_utilization_metrics,
        write_history_reports,
    )
except ModuleNotFoundError:  # Direct locked_freqtrade.py execution from runtime/.
    from backtest_experiment import (
        build_run_plan,
        build_test_identity,
        current_git_commit,
        find_archived_strategy_source,
        load_config_contract,
        registered_experiment,
        strategy_change_diff,
        strategy_hashes,
    )
    from backtest_history_analysis import (
        analyze_backtest_history,
        capital_utilization_metrics,
        write_history_reports,
    )

ALLOWED_PAIRS = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "DOGE/USDT",
)
PORTFOLIO_TARGET = "PORTFOLIO"
ALLOWED_TARGETS = (*ALLOWED_PAIRS, PORTFOLIO_TARGET)
ALLOWED_YEARS = (1, 2, 3)
STRATEGY_NAME = "CompressionBreakout250"
REQUIRED_TIMEFRAMES = ("15m", "1m", "1h", "4h")
BACKTEST_WARMUP_DAYS = 75

_RUNTIME_ROOT = Path(__file__).resolve().parent
_USERDIR = _RUNTIME_ROOT / "user_data"
_CONFIG = _USERDIR / "config.json"
_PUBLIC_CONFIG = _USERDIR / "config-public.json"
_STRATEGY = _USERDIR / "strategies" / f"{STRATEGY_NAME}.py"
_BACKTEST_RUNNER = _RUNTIME_ROOT / "locked_backtest_freqtrade.py"
_UI_SCRIPT = _RUNTIME_ROOT / "ui" / "testbot-backtest.js"
_RESULTS_ROOT = _USERDIR / "backtest_results" / "ui"
_DATA_ROOT = _USERDIR / "data" / "binance"
_REPO_ROOT = _RUNTIME_ROOT.parent
_TRIAL_LEDGER = _REPO_ROOT / "research" / "trial_ledger.csv"
_EXECUTED_TEST_LEDGER = _REPO_ROOT / "research" / "executed_test_fingerprints.csv"

_state_lock = threading.Lock()
_state: dict[str, Any] = {
    "status": "idle",
    "stage": "Bereit",
    "progress": 0,
    "run_id": None,
    "pair": None,
    "years": None,
    "started_at": None,
    "finished_at": None,
    "result": None,
    "error": None,
}


class BacktestRequest(BaseModel):
    pair: str
    years: int = Field(ge=1, le=3)


def _set_state(**values: Any) -> None:
    with _state_lock:
        _state.update(values)


def get_state() -> dict[str, Any]:
    with _state_lock:
        return dict(_state)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _registered_test_attempt(fingerprint: str) -> dict[str, str] | None:
    if not _EXECUTED_TEST_LEDGER.is_file():
        return None
    with _EXECUTED_TEST_LEDGER.open("r", encoding="utf-8", newline="") as stream:
        return next(
            (
                {str(key): str(value or "") for key, value in row.items()}
                for row in csv.DictReader(stream)
                if row.get("test_fingerprint") == fingerprint
            ),
            None,
        )


def _clean_subprocess_environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("FREQTRADE__") and key != "AI_TRADING_KILL_SWITCH_FILE"
    }
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _btc_context_pair(pair: str) -> None:
    """Compatibility hook: pair-local V12.12 never requests another pair as context."""

    if pair not in ALLOWED_PAIRS:
        raise ValueError(f"unsupported pair: {pair}")
    return None


def _pairs_for_target(target: str) -> tuple[str, ...]:
    if target == PORTFOLIO_TARGET:
        return ALLOWED_PAIRS
    if target in ALLOWED_PAIRS:
        return (target,)
    raise ValueError(f"unsupported backtest target: {target}")


def _closed_timerange(start: datetime, end: datetime) -> str:
    return f"{start:%Y%m%d}-{end:%Y%m%d}"


def _parse_backtest_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _validate_result_coverage(
    result: dict[str, Any],
    requested_start: datetime,
    requested_end: datetime,
    years: int,
) -> None:
    actual_start = _parse_backtest_time(result.get("backtest_start"))
    actual_end = _parse_backtest_time(result.get("backtest_end"))
    expected_start = requested_start.replace(hour=0, minute=0, second=0, microsecond=0)
    expected_days = 365 * years
    actual_days = int(result.get("backtest_days") or 0)

    if (
        actual_start > expected_start + timedelta(days=1)
        or actual_end < requested_end - timedelta(days=1)
        or actual_days < expected_days - 2
    ):
        raise RuntimeError(
            "Backtest-Zeitraum unvollstaendig: angefordert "
            f"{years} Jahr(e) ab {expected_start:%Y-%m-%d}, tatsaechlich "
            f"{actual_start:%Y-%m-%d} bis {actual_end:%Y-%m-%d} "
            f"({actual_days} Tage). Ergebnis wird nicht als gueltig angezeigt."
        )


def _timeframe_delta(timeframe: str) -> timedelta:
    seconds = {"1m": 60, "15m": 15 * 60, "1h": 60 * 60, "4h": 4 * 60 * 60}
    try:
        return timedelta(seconds=seconds[timeframe])
    except KeyError as exc:
        raise RuntimeError(f"Unbekannter Backtest-Timeframe: {timeframe}") from exc


def _timeframe_floor(value: datetime, delta: timedelta) -> datetime:
    current = value.astimezone(UTC)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    delta_seconds = int(delta.total_seconds())
    elapsed_seconds = int((current - epoch).total_seconds())
    return epoch + timedelta(seconds=(elapsed_seconds // delta_seconds) * delta_seconds)


def _candle_path(pair: str, timeframe: str) -> Path:
    return _DATA_ROOT / f"{pair.replace('/', '_')}-{timeframe}.feather"


def _inspect_candle_file(
    path: Path,
    timeframe: str,
    required_start: datetime,
    required_end: datetime,
) -> dict[str, Any]:
    import pandas as pd

    if not path.is_file():
        raise RuntimeError(f"Marktdaten-Datei fehlt: {path}")
    frame = pd.read_feather(path, columns=["date"])
    if frame.empty:
        raise RuntimeError(f"Marktdaten-Datei ist leer: {path}")

    dates = pd.to_datetime(frame["date"], utc=True, errors="raise")
    delta = _timeframe_delta(timeframe)
    window_start = required_start.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    in_window = dates[(dates >= window_start) & (dates <= required_end + delta)]
    if in_window.empty:
        raise RuntimeError(f"Keine {timeframe}-Kerzen im benoetigten Zeitraum in {path.name}.")

    duplicates = int(in_window.duplicated().sum())
    diffs = in_window.diff().dropna()
    non_increasing = int((diffs <= timedelta(0)).sum())
    gaps = int((diffs > delta).sum())
    first = in_window.iloc[0].to_pydatetime()
    last = in_window.iloc[-1].to_pydatetime()

    if duplicates or non_increasing or gaps:
        raise RuntimeError(
            "Marktdaten-Integritaet fehlgeschlagen fuer "
            f"{path.name}: Duplikate={duplicates}, unsortiert={non_increasing}, "
            f"Luecken={gaps}. Backtest wird nicht gestartet."
        )
    if first > window_start + delta:
        raise RuntimeError(
            f"Marktdaten beginnen zu spaet fuer {path.name}: {first.isoformat()} "
            f"statt spaetestens {(window_start + delta).isoformat()}."
        )

    freshness_floor = _timeframe_floor(required_end, delta) - (2 * delta)
    if last < freshness_floor:
        raise RuntimeError(
            f"Marktdaten enden zu frueh fuer {path.name}: {last.isoformat()} "
            f"(Mindeststand {freshness_floor.isoformat()}, Pruefzeit "
            f"{required_end.isoformat()})."
        )

    return {
        "file": path.name,
        "timeframe": timeframe,
        "rows_in_required_window": len(in_window),
        "first": first.isoformat(),
        "last": last.isoformat(),
        "duplicates": duplicates,
        "gaps": gaps,
    }


def _validate_candle_data(
    pair: str, download_start: datetime, required_end: datetime
) -> list[dict[str, Any]]:
    return [
        _inspect_candle_file(_candle_path(pair, timeframe), timeframe, download_start, required_end)
        for timeframe in REQUIRED_TIMEFRAMES
    ]


def _run_checked(args: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write("\n$ " + subprocess.list2cmdline(args) + "\n")
        log.flush()
        process = subprocess.run(
            args,
            cwd=str(_RUNTIME_ROOT),
            env=_clean_subprocess_environment(),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if process.returncode != 0:
        raise RuntimeError(
            f"Befehl fehlgeschlagen (Code {process.returncode}). Details: {log_path}"
        )


def _find_result_file(run_dir: Path) -> Path:
    zip_candidates = [path for path in run_dir.glob("*.zip") if path.is_file()]
    if zip_candidates:
        return max(zip_candidates, key=lambda path: path.stat().st_mtime_ns)
    candidates = [
        path
        for path in run_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".json"
        and path.name.startswith("backtest-result-")
        and not path.name.endswith("_config.json")
        and not path.name.endswith(".meta.json")
    ]
    if not candidates:
        raise RuntimeError("Freqtrade hat keine Backtest-Ergebnisdatei erzeugt.")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _trade_breakdown(trades: list[dict[str, Any]], key: str, fallback: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for trade in trades:
        label = str(trade.get(key) or fallback)
        item = grouped.setdefault(
            label,
            {"label": label, "trades": 0, "wins": 0, "profit_usdt": 0.0},
        )
        profit = _number(trade.get("profit_abs"))
        item["trades"] += 1
        item["wins"] += int(profit > 0)
        item["profit_usdt"] += profit

    rows = []
    for item in grouped.values():
        rows.append(
            {
                "label": item["label"],
                "trades": int(item["trades"]),
                "wins": int(item["wins"]),
                "profit_usdt": round(float(item["profit_usdt"]), 4),
            }
        )
    return sorted(rows, key=lambda row: (-row["trades"], row["label"]))


def _extract_result(result_file: Path, pair: str, years: int, strategy_hash: str) -> dict[str, Any]:
    from freqtrade.data.btanalysis import load_backtest_stats

    stats = load_backtest_stats(result_file)
    strategy_map = stats.get("strategy", {})
    strategy = strategy_map.get(STRATEGY_NAME)
    if not isinstance(strategy, dict):
        raise RuntimeError(f"Backtest-Ergebnis fuer {STRATEGY_NAME} fehlt.")

    trades = strategy.get("trades") or []
    trade_count = int(strategy.get("total_trades") or strategy.get("trade_count") or len(trades))
    wins = strategy.get("wins")
    if wins is None:
        wins = sum(1 for trade in trades if _number(trade.get("profit_abs")) > 0)
    wins = int(wins)

    starting_balance = _number(strategy.get("starting_balance"), 250.0)
    profit_abs = _number(strategy.get("profit_total_abs"))
    final_balance = _number(strategy.get("final_balance"), starting_balance + profit_abs)
    if profit_abs == 0.0 and final_balance != starting_balance:
        profit_abs = final_balance - starting_balance

    profit_ratio = strategy.get("profit_total")
    if profit_ratio is None:
        profit_ratio = (profit_abs / starting_balance) if starting_balance else 0.0
    profit_pct = _number(profit_ratio) * 100.0

    winrate = strategy.get("winrate")
    if winrate is None:
        winrate = (wins / trade_count) if trade_count else 0.0
    winrate_pct = _number(winrate) * 100.0

    drawdown_ratio = strategy.get("max_drawdown_account")
    if drawdown_ratio is None:
        drawdown_ratio = strategy.get("max_drawdown")
    drawdown_value = _number(drawdown_ratio)
    if drawdown_value > 1.0:
        drawdown_pct = _number(strategy.get("max_drawdown_account")) * 100.0
    else:
        drawdown_pct = drawdown_value * 100.0
    utilization = capital_utilization_metrics(
        trades,
        strategy.get("backtest_start"),
        strategy.get("backtest_end"),
        available_capital=starting_balance,
    )

    return {
        "pair": pair,
        "years": years,
        "strategy": STRATEGY_NAME,
        "strategy_sha256": strategy_hash,
        "timeframe": "15m",
        "timeframe_detail": "1m",
        "starting_balance_usdt": round(starting_balance, 4),
        "final_balance_usdt": round(final_balance, 4),
        "profit_usdt": round(profit_abs, 4),
        "profit_pct": round(profit_pct, 4),
        "trades": trade_count,
        "wins": wins,
        "winrate_pct": round(winrate_pct, 2),
        "profit_factor": round(_number(strategy.get("profit_factor")), 4),
        "max_drawdown_pct": round(drawdown_pct, 2),
        "backtest_start": str(strategy.get("backtest_start") or ""),
        "backtest_end": str(strategy.get("backtest_end") or ""),
        "backtest_days": int(strategy.get("backtest_days") or 0),
        "coverage_validated": True,
        "result_file": str(result_file),
        "adaptive_router": False,
        "cross_pair_context": False,
        **utilization,
        "entry_tag_breakdown": _trade_breakdown(trades, key="enter_tag", fallback="ohne_entry_tag"),
        "exit_reason_breakdown": _trade_breakdown(
            trades, key="exit_reason", fallback="ohne_exit_reason"
        ),
    }


def _prepare_run_contract(run_id: str, pair: str, years: int) -> tuple[dict[str, Any], str]:
    for required in (_CONFIG, _STRATEGY, _TRIAL_LEDGER, _EXECUTED_TEST_LEDGER):
        if not required.is_file():
            raise HTTPException(
                status_code=409,
                detail=f"Backtest gesperrt: notwendige Forschungsakte fehlt: {required}",
            )

    source = _STRATEGY.read_bytes()
    identity = build_test_identity(
        strategy_source=source,
        pair=pair,
        years=years,
        config=load_config_contract(_CONFIG),
    )
    try:
        experiment, lineage = registered_experiment(_TRIAL_LEDGER, identity["strategy_sha256"])
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "Backtest gesperrt: Die aktuelle Strategie ist nicht eindeutig und "
                f"vollständig im Versuchsregister dokumentiert. {exc}"
            ),
        ) from exc

    recorded_attempt = _registered_test_attempt(identity["test_fingerprint"])
    if recorded_attempt:
        raise HTTPException(
            status_code=409,
            detail=(
                "Doppeltest blockiert: Der inhaltliche Fingerabdruck ist bereits "
                f"im versionierten Laufregister als {recorded_attempt.get('run_id') or '?'} "
                f"mit Ausgang {recorded_attempt.get('outcome') or '?'} erfasst. Auch ein "
                "technisch fehlgeschlagener Lauf darf nicht identisch wiederholt werden."
            ),
        )

    history = analyze_backtest_history(
        _RESULTS_ROOT,
        current_strategy_path=_STRATEGY,
        trial_ledger_path=_TRIAL_LEDGER,
    )
    duplicate = next(
        (
            row
            for row in (*history["runs"], *history["incomplete_runs"])
            if row.get("test_fingerprint") == identity["test_fingerprint"]
        ),
        None,
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=(
                "Doppeltest blockiert: Derselbe inhaltliche Test existiert bereits als "
                f"{duplicate['run_id']} ({pair}, {years} Jahr(e), "
                f"{duplicate['strategy_version']}). Reine Versions-, Kommentar- oder "
                "Beschreibungsänderungen zählen nicht. Für einen neuen Lauf muss eine "
                "echte Logik-/Parameteränderung als neues Experiment registriert sein."
            ),
        )

    parent = lineage[-2] if len(lineage) > 1 else None
    parent_source = find_archived_strategy_source(
        _RESULTS_ROOT, parent.get("strategy_hash", "") if parent else ""
    )
    if parent and parent_source is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Backtest gesperrt: Die exakte Strategy-Quelle des Vorgängers ist "
                "nicht im erhaltenen Archiv auffindbar; die Änderung kann nicht "
                "zuverlässig geprüft werden."
            ),
        )
    if parent_source and (
        strategy_hashes(parent_source)["strategy_logic_sha256"] == identity["strategy_logic_sha256"]
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Doppeltest blockiert: Gegenüber dem registrierten Vorgänger wurde "
                "keine Strategy-Logik geändert. Versionen, Kommentare und "
                "Beschreibungen erzeugen kein neues Experiment."
            ),
        )
    diff = strategy_change_diff(parent_source, source)
    plan = build_run_plan(
        run_id=run_id,
        pair=pair,
        years=years,
        identity=identity,
        experiment=experiment,
        lineage=lineage,
        source_commit=current_git_commit(_REPO_ROOT),
        strategy_diff=diff,
    )
    plan["execution_contract"] = {
        "locked_runner": str(_BACKTEST_RUNNER.resolve()),
        "strategy_source": str(_STRATEGY.resolve()),
        "config_chain": [str(_CONFIG.resolve()), str(_PUBLIC_CONFIG.resolve())],
        "targets": list(_pairs_for_target(pair)),
        "required_timeframes": list(REQUIRED_TIMEFRAMES),
        "allowed_data_root": str((_USERDIR / "data").resolve()),
        "allowed_output_root": str((_RESULTS_ROOT / run_id).resolve()),
        "file_access_audit_required": True,
        "child_processes_allowed_inside_locked_backtest": False,
        "python_executable": str(Path(sys.executable).resolve()),
        "python_dependency_prefix": str(Path(sys.prefix).resolve()),
    }
    return plan, diff


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _validate_file_access_audit(
    audit_path: Path,
    run_dir: Path,
    pairs: tuple[str, ...],
    strategy_hash: str,
) -> dict[str, Any]:
    if not audit_path.is_file():
        raise RuntimeError("Backtest-Dateizugriffsprotokoll fehlt.")
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    context = payload.get("context")
    opened_rows = payload.get("opened_files")
    candle_rows = payload.get("candle_loads")
    spawned = payload.get("spawned_processes")
    if (
        not isinstance(context, dict)
        or not isinstance(opened_rows, list)
        or not isinstance(candle_rows, list)
    ):
        raise RuntimeError("Backtest-Dateizugriffsprotokoll ist unvollstaendig.")
    if context.get("strategy_sha256") != strategy_hash:
        raise RuntimeError("Dateiaudit meldet einen unerwarteten Strategie-Hash.")
    if Path(str(context.get("strategy_source", ""))).resolve() != _STRATEGY.resolve():
        raise RuntimeError("Dateiaudit meldet eine unerwartete Strategiequelle.")
    if spawned:
        raise RuntimeError("Der gesperrte Backtest hat einen unerwarteten Kindprozess gestartet.")

    opened = {
        Path(str(row.get("path"))).resolve()
        for row in opened_rows
        if isinstance(row, dict) and row.get("path")
    }
    required_files = {_STRATEGY.resolve(), _CONFIG.resolve(), _PUBLIC_CONFIG.resolve()}
    missing_required = sorted(str(path) for path in required_files - opened)

    data_root = (_USERDIR / "data").resolve()
    data_files = sorted(
        {
            Path(str(row.get("path"))).resolve()
            for row in candle_rows
            if isinstance(row, dict) and row.get("path")
        }
    )
    expected_candle_files: dict[Path, str] = {}
    for pair in pairs:
        for timeframe in REQUIRED_TIMEFRAMES:
            expected_candle_files[_candle_path(pair, timeframe).resolve()] = (
                f"{pair} {timeframe}"
            )
    loaded_candle_files = set(data_files)
    missing_candles = sorted(
        label
        for path, label in expected_candle_files.items()
        if path not in loaded_candle_files
    )
    unexpected_candles = sorted(
        str(path) for path in loaded_candle_files if path not in expected_candle_files
    )
    changed_candles = []
    for row in candle_rows:
        if not isinstance(row, dict) or not row.get("path"):
            continue
        path = Path(str(row["path"])).resolve()
        if not path.is_file() or _sha256(path) != row.get("sha256_at_load"):
            changed_candles.append(str(path))

    allowed_files = required_files | {
        _BACKTEST_RUNNER.resolve(),
        (_RUNTIME_ROOT / "locked_freqtrade.py").resolve(),
    }
    unexpected_repo_reads = sorted(
        str(path)
        for path in opened
        if _is_within(path, _REPO_ROOT)
        and path.exists()
        and path not in allowed_files
        and not _is_within(path, data_root)
        and not _is_within(path, run_dir)
    )
    validation = {
        "strategy_source_exact": (
            not missing_required and context.get("strategy_sha256") == strategy_hash
        ),
        "required_files_observed": sorted(str(path) for path in required_files),
        "missing_required_files": missing_required,
        "expected_candle_sets": len(pairs) * len(REQUIRED_TIMEFRAMES),
        "observed_candle_files": [str(path) for path in data_files],
        "missing_candle_sets": missing_candles,
        "unexpected_candle_files": unexpected_candles,
        "changed_candle_files_after_load": sorted(changed_candles),
        "unexpected_repo_reads": unexpected_repo_reads,
        "spawned_processes": spawned or [],
        "passed": not (
            missing_required
            or missing_candles
            or unexpected_candles
            or changed_candles
            or unexpected_repo_reads
        ),
    }
    payload["validation"] = validation
    _write_json(audit_path, payload)
    if not validation["passed"]:
        raise RuntimeError(
            "Backtest-Dateiaudit fehlgeschlagen: "
            + json.dumps(validation, ensure_ascii=False, sort_keys=True)
        )
    return validation


def _attach_audit_files(result_file: Path, run_dir: Path) -> None:
    if result_file.suffix.lower() != ".zip":
        return
    with ZipFile(result_file, "a") as archive:
        for name in (
            "experiment-plan.json",
            "strategy-change.diff",
            "experiment-result.json",
            "file-access-audit.json",
        ):
            archive.write(run_dir / name, f"audit/{name}")


def _execute_backtest(
    run_id: str,
    pair: str,
    years: int,
    run_plan: dict[str, Any],
    strategy_diff: str,
) -> None:
    run_dir = _RESULTS_ROOT / run_id
    log_path = run_dir / "backtest.log"
    file_audit_path = run_dir / "file-access-audit.json"
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
        _write_json(run_dir / "experiment-plan.json", run_plan)
        (run_dir / "strategy-change.diff").write_text(strategy_diff, encoding="utf-8")
        for required in (_CONFIG, _PUBLIC_CONFIG, _STRATEGY, _BACKTEST_RUNNER):
            if not required.is_file():
                raise RuntimeError(f"Erforderliche Datei fehlt: {required}")

        strategy_hash = _sha256(_STRATEGY)
        if strategy_hash != run_plan["test_identity"]["strategy_sha256"]:
            raise RuntimeError(
                "Strategiedatei wurde nach der Duplikatprüfung verändert; Lauf abgebrochen."
            )
        now = datetime.now(UTC)
        requested_start = now - timedelta(days=365 * years)
        download_start = requested_start - timedelta(days=BACKTEST_WARMUP_DAYS)
        requested_timerange = requested_start.strftime("%Y%m%d") + "-"
        download_timerange = download_start.strftime("%Y%m%d") + "-"
        pairs = _pairs_for_target(pair)

        _set_state(stage="Binance-Daten werden bis heute aktualisiert", progress=10)
        download_args = [
            sys.executable,
            "-m",
            "freqtrade",
            "download-data",
            "--config",
            str(_CONFIG),
            "--config",
            str(_PUBLIC_CONFIG),
            "--userdir",
            str(_USERDIR),
            "--timeframes",
            *REQUIRED_TIMEFRAMES,
            "--pairs",
            *pairs,
            "--trading-mode",
            "spot",
            "--timerange",
            download_timerange,
        ]
        _run_checked(download_args, log_path)

        _set_state(stage="Aeltere Binance-Daten werden vervollstaendigt", progress=24)
        prepend_args = [
            *download_args[:-2],
            "--timerange",
            _closed_timerange(download_start, now),
            "--prepend",
        ]
        _run_checked(prepend_args, log_path)

        _set_state(stage="Kerzendaten werden auf Luecken und Duplikate geprueft", progress=38)
        data_integrity = {
            current_pair: _validate_candle_data(current_pair, download_start, now)
            for current_pair in pairs
        }

        _set_state(stage="Historische Daten geladen - V12.12 Backtest startet", progress=45)
        backtest_args = [
            sys.executable,
            str(_BACKTEST_RUNNER),
            "--strategy-source",
            str(_STRATEGY),
            "--strategy-sha256",
            strategy_hash,
            "--strategy-class",
            STRATEGY_NAME,
            "--file-audit-output",
            str(file_audit_path),
            "--",
            "backtesting",
            "--config",
            str(_CONFIG),
            "--config",
            str(_PUBLIC_CONFIG),
            "--userdir",
            str(_USERDIR),
            "--strategy",
            STRATEGY_NAME,
            "--pairs",
            *pairs,
            "--timerange",
            requested_timerange,
            "--timeframe-detail",
            "1m",
            "--fee",
            "0.002",
            "--enable-protections",
            "--dry-run-wallet",
            "250",
            "--cache",
            "none",
            "--export",
            "trades",
            "--backtest-directory",
            str(run_dir),
            "--breakdown",
            "month",
        ]
        _set_state(stage="V12.12 wird historisch simuliert", progress=60)
        _run_checked(backtest_args, log_path)

        _set_state(stage="Ergebnis und Strategie-Familien werden ausgewertet", progress=92)
        execution_file_audit = _validate_file_access_audit(
            file_audit_path,
            run_dir,
            pairs,
            strategy_hash,
        )
        result_file = _find_result_file(run_dir)
        result = _extract_result(result_file, pair, years, strategy_hash)
        _validate_result_coverage(result, requested_start, now, years)
        result["data_integrity_validated"] = True
        result["data_integrity"] = data_integrity
        result["execution_file_audit"] = execution_file_audit
        result["experiment"] = run_plan["experiment"]
        result["experiment_lineage"] = run_plan["lineage"]
        result["test_identity"] = run_plan["test_identity"]
        experiment_result = {
            **run_plan,
            "finished_at_utc": datetime.now(UTC).isoformat(),
            "outcome": "completed",
            "outcome_metrics": {
                field: result[field]
                for field in (
                    "profit_usdt",
                    "profit_pct",
                    "trades",
                    "winrate_pct",
                    "profit_factor",
                    "max_drawdown_pct",
                    "capital_time_utilization_pct",
                    "no_position_time_pct",
                    "average_open_positions",
                    "max_simultaneous_positions",
                    "backtest_start",
                    "backtest_end",
                    "backtest_days",
                )
            },
        }
        experiment_result["outcome_metrics"]["file_access_audit_passed"] = (
            execution_file_audit["passed"]
        )
        _write_json(run_dir / "experiment-result.json", experiment_result)
        _attach_audit_files(result_file, run_dir)
        try:
            history = write_history_reports(
                _RESULTS_ROOT,
                current_strategy_path=_STRATEGY,
                trial_ledger_path=_TRIAL_LEDGER,
            )
            result["history_analysis"] = {
                "completed": history["summary"]["completed"],
                "incomplete": history["summary"]["incomplete"],
                "markdown": str(_RESULTS_ROOT / "GESAMTAUSWERTUNG.md"),
                "json": str(_RESULTS_ROOT / "gesamt-auswertung.json"),
            }
        except Exception as exc:
            # A successful raw backtest remains valid evidence even if the
            # secondary historical summary cannot be refreshed.
            result["history_analysis_error"] = str(exc)
        _set_state(
            status="completed",
            stage="Fertig",
            progress=100,
            finished_at=datetime.now(UTC).isoformat(),
            result=result,
            error=None,
        )
    except Exception as exc:
        if run_dir.is_dir():
            failed_result = {
                **run_plan,
                "finished_at_utc": datetime.now(UTC).isoformat(),
                "outcome": "failed",
                "error": str(exc),
            }
            _write_json(run_dir / "experiment-result.json", failed_result)
        _set_state(
            status="failed",
            stage="Fehler",
            progress=100,
            finished_at=datetime.now(UTC).isoformat(),
            error=str(exc),
            result=None,
        )


def start_backtest(request: BacktestRequest) -> dict[str, Any]:
    if request.pair not in ALLOWED_TARGETS:
        raise HTTPException(status_code=400, detail="Dieses Backtest-Ziel ist nicht freigegeben.")
    if request.years not in ALLOWED_YEARS:
        raise HTTPException(status_code=400, detail="Zeitraum muss 1, 2 oder 3 Jahre sein.")

    current = get_state()
    if current["status"] == "running":
        raise HTTPException(status_code=409, detail="Es laeuft bereits ein Backtest.")

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_plan, strategy_diff = _prepare_run_contract(run_id, request.pair, request.years)
    _set_state(
        status="running",
        stage="Backtest wird vorbereitet",
        progress=2,
        run_id=run_id,
        pair=request.pair,
        years=request.years,
        started_at=datetime.now(UTC).isoformat(),
        finished_at=None,
        result=None,
        error=None,
    )
    thread = threading.Thread(
        target=_execute_backtest,
        args=(run_id, request.pair, request.years, run_plan, strategy_diff),
        name=f"testbot-backtest-{run_id}",
        daemon=True,
    )
    thread.start()
    return get_state()


def build_router() -> APIRouter:
    router = APIRouter(include_in_schema=False)

    @router.get("/testbot-backtest.js")
    async def backtest_script() -> Response:
        return Response(
            _UI_SCRIPT.read_text(encoding="utf-8"),
            media_type="application/javascript",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    @router.get("/api/v1/testbot/backtest/status")
    async def backtest_status() -> dict[str, Any]:
        return get_state()

    @router.post("/api/v1/testbot/backtest/start")
    async def backtest_start(request: BacktestRequest) -> dict[str, Any]:
        return start_backtest(request)

    return router
