"""Hixton V5 pair-route adapter for the locked Testbot backtest API.

This branch is intentionally isolated from V12.33 strategy research. A new
clone starts without local market data/results, downloads and validates the
required Binance candles, runs ten independent 250-USDT diagnostics, and then
runs the real chronological shared-wallet portfolio with at most 3 x 80 USDT.
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

try:
    from runtime import testbot_backtest_api as base
except ModuleNotFoundError:
    import testbot_backtest_api as base

TEN_PAIR_UNIVERSE = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "DOGE/USDT",
    "LINK/USDT",
    "TRX/USDT",
    "LTC/USDT",
    "BCH/USDT",
)
ACTIVE_EXPERIMENT_ID = "HIXTON-V5-PAIR-ROUTES"

# Re-point the generic locked engine to the isolated Hixton research records.
base.ALLOWED_PAIRS = TEN_PAIR_UNIVERSE
base.ALLOWED_TARGETS = (*TEN_PAIR_UNIVERSE, base.PORTFOLIO_TARGET)
base.STRATEGY_VERSION = "HIXTON-V5"
base._TRIAL_LEDGER = base._REPO_ROOT / "research" / "hixton_trial_ledger.csv"
base._EXECUTED_TEST_LEDGER = base._REPO_ROOT / "research" / "hixton_executed_test_fingerprints.csv"
base._RESULTS_ROOT = base._USERDIR / "backtest_results" / "hixton"
base._UI_SCRIPT = base._RUNTIME_ROOT / "ui" / "testbot-backtest.js"

_original_validate_candle_data = base._validate_candle_data
_original_is_within = base._is_within
_python_dependency_prefix = Path(sys.prefix).resolve()
_BATCH_ROOT = base._RESULTS_ROOT / "_BATCHES"
_BATCH_POINTER = _BATCH_ROOT / "latest.json"
_batch_lock = threading.Lock()
_batch_worker_context = threading.local()


class BatchRequest(BaseModel):
    years: int = Field(ge=1, le=3)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "run_id",
        "pair",
        "years",
        "strategy",
        "strategy_sha256",
        "starting_balance_usdt",
        "final_balance_usdt",
        "profit_usdt",
        "profit_pct",
        "trades",
        "wins",
        "winrate_pct",
        "profit_factor",
        "max_drawdown_pct",
        "capital_time_utilization_pct",
        "no_position_time_pct",
        "average_open_positions",
        "max_simultaneous_positions",
        "max_deployed_capital_usdt",
        "total_entry_capital_usdt",
        "deployed_capital_usdt_days",
        "profit_per_trade_usdt",
        "profit_per_calendar_day_usdt",
        "trades_per_year",
        "profit_per_100_entry_capital_usdt",
        "profit_per_100_deployed_capital_day_usdt",
        "backtest_start",
        "backtest_end",
        "backtest_days",
        "coverage_validated",
        "data_integrity_validated",
        "reused_existing_result",
        "pair_breakdown",
        "entry_tag_breakdown",
        "exit_reason_breakdown",
        "timing",
    )
    return {field: result.get(field) for field in fields}


def _identity(pair: str, years: int) -> dict[str, Any]:
    return base.build_test_identity(
        strategy_source=base._STRATEGY.read_bytes(),
        pair=pair,
        years=years,
        config=base.load_config_contract(base._CONFIG),
    )


def _batch_fingerprint(years: int) -> tuple[str, list[dict[str, Any]], str]:
    cases: list[dict[str, Any]] = []
    for pair in TEN_PAIR_UNIVERSE:
        identity = _identity(pair, years)
        cases.append(
            {
                "pair": pair,
                "years": years,
                "test_fingerprint": identity["test_fingerprint"],
                "status": "pending",
                "result": None,
                "error": None,
            }
        )
    portfolio_identity = _identity(base.PORTFOLIO_TARGET, years)
    material = {
        "schema_version": 2,
        "experiment_id": ACTIVE_EXPERIMENT_ID,
        "strategy_sha256": base._sha256(base._STRATEGY),
        "years": years,
        "cases": [case["test_fingerprint"] for case in cases],
        "portfolio_test_fingerprint": portfolio_identity["test_fingerprint"],
    }
    fingerprint = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return fingerprint, cases, str(portfolio_identity["test_fingerprint"])


def _batch_dir(batch_id: str) -> Path:
    return _BATCH_ROOT / batch_id


def _persist_batch(state: dict[str, Any]) -> None:
    directory = _batch_dir(str(state["batch_id"]))
    directory.mkdir(parents=True, exist_ok=True)
    base._write_json(directory / "batch-plan.json", state["plan"])
    base._write_json(directory / "batch-result.json", state)
    base._write_json(
        _BATCH_POINTER,
        {
            "schema_version": 2,
            "batch_id": state["batch_id"],
            "batch_fingerprint": state["batch_fingerprint"],
            "result_path": str((directory / "batch-result.json").resolve()),
        },
    )


def _load_latest_batch() -> dict[str, Any] | None:
    try:
        pointer = json.loads(_BATCH_POINTER.read_text(encoding="utf-8"))
        path = _batch_dir(str(pointer["batch_id"])) / "batch-result.json"
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if state.get("status") == "running":
        state["status"] = "interrupted"
        state["stage"] = "Bot wurde neu gestartet; Hixton-Batch kann fortgesetzt werden"
        state["updated_at_utc"] = _utc_now()
        _persist_batch(state)
    return state


_batch_state: dict[str, Any] | None = _load_latest_batch()


def get_batch_state() -> dict[str, Any]:
    with _batch_lock:
        if _batch_state is None:
            return {
                "status": "idle",
                "stage": "Kein Hixton-Gesamttest gestartet",
                "progress": 0,
                "cases": [],
                "portfolio_status": "pending",
                "portfolio_result": None,
            }
        return json.loads(json.dumps(_batch_state))


def _set_batch_state(**values: Any) -> dict[str, Any]:
    global _batch_state
    with _batch_lock:
        if _batch_state is None:
            raise RuntimeError("batch state is not initialized")
        _batch_state.update(values)
        _batch_state["updated_at_utc"] = _utc_now()
        _persist_batch(_batch_state)
        return json.loads(json.dumps(_batch_state))


def _new_batch(
    years: int,
    fingerprint: str,
    cases: list[dict[str, Any]],
    portfolio_fingerprint: str,
) -> dict[str, Any]:
    run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    batch_id = f"{run_stamp}-{uuid.uuid4().hex[:8]}"
    plan = {
        "schema_version": 2,
        "batch_id": batch_id,
        "batch_fingerprint": fingerprint,
        "created_at_utc": _utc_now(),
        "experiment_id": ACTIVE_EXPERIMENT_ID,
        "strategy_version": base.STRATEGY_VERSION,
        "strategy_sha256": base._sha256(base._STRATEGY),
        "source_commit": base.current_git_commit(base._REPO_ROOT),
        "years": years,
        "wallet_contract": (
            "10 independent diagnostics: own 250-USDT wallet, fixed 80-USDT trade; "
            "then one chronological shared 250-USDT portfolio with max 3x80 USDT"
        ),
        "required_timeframes": list(base.REQUIRED_TIMEFRAMES),
        "cases": [
            {
                "pair": case["pair"],
                "years": years,
                "test_fingerprint": case["test_fingerprint"],
            }
            for case in cases
        ],
        "portfolio": {
            "pair": base.PORTFOLIO_TARGET,
            "years": years,
            "test_fingerprint": portfolio_fingerprint,
        },
    }
    return {
        "schema_version": 2,
        "batch_id": batch_id,
        "batch_fingerprint": fingerprint,
        "status": "running",
        "stage": "Hixton V5 wird vorbereitet",
        "progress": 0,
        "years": years,
        "started_at_utc": _utc_now(),
        "updated_at_utc": _utc_now(),
        "finished_at_utc": None,
        "current_pair": None,
        "completed_cases": 0,
        "failed_cases": 0,
        "batch_error": None,
        "cases": cases,
        "portfolio_status": "pending",
        "portfolio_result": None,
        "portfolio_error": None,
        "plan": plan,
    }


def _wait_for_result(request: base.BacktestRequest) -> dict[str, Any]:
    started = start_backtest(request)
    state = started
    while state.get("status") == "running":
        time.sleep(1)
        state = base.get_state()
    if state.get("status") != "completed" or not isinstance(state.get("result"), dict):
        raise RuntimeError(str(state.get("error") or "Backtest fehlgeschlagen"))
    return dict(state["result"])


def _run_individual_cases() -> None:
    state = get_batch_state()
    total = len(state.get("cases", []))
    for index in range(total):
        state = get_batch_state()
        case = state["cases"][index]
        if case.get("status") in {"completed", "reused"}:
            continue
        pair = str(case["pair"])
        years = int(case["years"])
        case["status"] = "running"
        state["cases"][index] = case
        _set_batch_state(
            cases=state["cases"],
            current_pair=pair,
            stage=f"Hixton: {pair} Einzeltest ({index + 1}/{total})",
            progress=round(85 * index / max(1, total), 2),
        )
        try:
            planned_hash = str(state.get("plan", {}).get("strategy_sha256") or "")
            if base._sha256(base._STRATEGY) != planned_hash:
                raise RuntimeError("Strategiedatei wurde während des Batches verändert.")
            result = _wait_for_result(base.BacktestRequest(pair=pair, years=years))
            identity = result.get("test_identity")
            actual_fingerprint = identity.get("test_fingerprint") if isinstance(identity, dict) else None
            if actual_fingerprint != case["test_fingerprint"]:
                raise RuntimeError(f"{pair}: Ergebnis-Fingerprint passt nicht zum Batchplan.")
            case["status"] = "reused" if result.get("reused_existing_result") else "completed"
            case["result"] = _compact_result(result)
            case["error"] = None
        except Exception as exc:
            case["status"] = "failed"
            case["error"] = str(getattr(exc, "detail", None) or exc)

        state = get_batch_state()
        state["cases"][index] = case
        completed = sum(item.get("status") in {"completed", "reused"} for item in state["cases"])
        failed = sum(item.get("status") == "failed" for item in state["cases"])
        _set_batch_state(
            cases=state["cases"],
            completed_cases=completed,
            failed_cases=failed,
            progress=round(85 * (index + 1) / max(1, total), 2),
        )


def _run_shared_portfolio() -> None:
    state = get_batch_state()
    if int(state.get("failed_cases") or 0):
        _set_batch_state(
            status="completed_with_errors",
            stage="Einzeltests enthalten Fehler; 3x80-Portfolio wurde nicht gestartet",
            progress=100,
            current_pair=None,
            portfolio_status="blocked",
            finished_at_utc=_utc_now(),
        )
        return

    if state.get("portfolio_status") in {"completed", "reused"}:
        return

    years = int(state["years"])
    expected_fingerprint = str(state["plan"]["portfolio"]["test_fingerprint"])
    _set_batch_state(
        current_pair=base.PORTFOLIO_TARGET,
        stage="Alle 10 Einzeltests fertig - gemeinsames 3x80-Portfolio wird gerechnet",
        progress=90,
        portfolio_status="running",
        portfolio_error=None,
    )
    try:
        result = _wait_for_result(base.BacktestRequest(pair=base.PORTFOLIO_TARGET, years=years))
        identity = result.get("test_identity")
        actual = identity.get("test_fingerprint") if isinstance(identity, dict) else None
        if actual != expected_fingerprint:
            raise RuntimeError("Portfolio-Ergebnis-Fingerprint passt nicht zum Batchplan.")
        portfolio_status = "reused" if result.get("reused_existing_result") else "completed"
        _set_batch_state(
            portfolio_status=portfolio_status,
            portfolio_result=_compact_result(result),
            portfolio_error=None,
            progress=100,
        )
    except Exception as exc:
        _set_batch_state(
            status="completed_with_errors",
            stage="Zehn Einzeltests fertig, aber der gemeinsame 3x80-Lauf ist fehlgeschlagen",
            progress=100,
            current_pair=None,
            portfolio_status="failed",
            portfolio_error=str(getattr(exc, "detail", None) or exc),
            finished_at_utc=_utc_now(),
        )
        return

    _set_batch_state(
        status="completed",
        stage="Hixton-Gesamttest fertig: 10 Einzeltests + gemeinsames 3x80-Portfolio",
        progress=100,
        current_pair=None,
        finished_at_utc=_utc_now(),
    )


def _run_batch() -> None:
    _batch_worker_context.active = True
    try:
        _run_individual_cases()
        _run_shared_portfolio()
    except Exception as exc:
        with suppress(Exception):
            _set_batch_state(
                status="failed",
                stage="Hixton-Gesamttest ist technisch fehlgeschlagen",
                progress=100,
                current_pair=None,
                batch_error=str(exc),
                finished_at_utc=_utc_now(),
            )
    finally:
        _batch_worker_context.active = False


def _reject_manual_start_during_batch() -> None:
    if bool(getattr(_batch_worker_context, "active", False)):
        return
    if get_batch_state().get("status") == "running":
        raise HTTPException(status_code=409, detail="Der Hixton-Gesamttest läuft bereits.")


def start_batch(request: BatchRequest) -> dict[str, Any]:
    global _batch_state
    if request.years not in base.ALLOWED_YEARS:
        raise HTTPException(status_code=400, detail="Zeitraum muss 1, 2 oder 3 Jahre sein.")
    if base.get_state().get("status") == "running":
        raise HTTPException(status_code=409, detail="Es läuft bereits ein einzelner Backtest.")

    fingerprint, cases, portfolio_fingerprint = _batch_fingerprint(request.years)
    with _batch_lock:
        current = _batch_state
        if current and current.get("status") == "running":
            return json.loads(json.dumps(current))
        if current and current.get("batch_fingerprint") == fingerprint:
            if current.get("status") == "completed":
                return json.loads(json.dumps(current))
            _batch_state = current
            _batch_state["status"] = "running"
            _batch_state["stage"] = "Unvollständiger Hixton-Gesamttest wird fortgesetzt"
            _batch_state["batch_error"] = None
            _batch_state["updated_at_utc"] = _utc_now()
            _persist_batch(_batch_state)
        else:
            _batch_state = _new_batch(request.years, fingerprint, cases, portfolio_fingerprint)
            _persist_batch(_batch_state)
        response = json.loads(json.dumps(_batch_state))
    threading.Thread(target=_run_batch, name="hixton-ten-plus-portfolio", daemon=True).start()
    return response


def _audit_boundary_is_within(path: Path, root: Path) -> bool:
    resolved_root = root.resolve()
    if resolved_root == base._REPO_ROOT.resolve() and _original_is_within(path, _python_dependency_prefix):
        return False
    return _original_is_within(path, root)


def _validate_or_repair_candle_data(
    pair: str,
    download_start: Any,
    required_end: Any,
) -> list[dict[str, Any]]:
    """Validate all 1m/15m/1h/4h files; rebuild only this pair if invalid."""
    try:
        return _original_validate_candle_data(pair, download_start, required_end)
    except RuntimeError as first_error:
        base._set_state(
            stage=f"{pair}: lokale Marktdaten werden vollständig neu aufgebaut",
            progress=35,
        )
        for timeframe in base.REQUIRED_TIMEFRAMES:
            base._candle_path(pair, timeframe).unlink(missing_ok=True)

        repair_log = base._RESULTS_ROOT / "data-repair.log"
        repair_args = [
            sys.executable,
            "-m",
            "freqtrade",
            "download-data",
            "--config",
            str(base._CONFIG),
            "--config",
            str(base._PUBLIC_CONFIG),
            "--userdir",
            str(base._USERDIR),
            "--timeframes",
            *base.REQUIRED_TIMEFRAMES,
            "--pairs",
            pair,
            "--trading-mode",
            "spot",
            "--timerange",
            base._closed_timerange(download_start, required_end),
        ]
        try:
            base._run_checked(repair_args, repair_log)
            repaired = _original_validate_candle_data(pair, download_start, required_end)
        except Exception as repair_error:
            raise RuntimeError(
                f"Marktdatenprüfung für {pair} fehlgeschlagen. Erster Fehler: {first_error}. "
                f"Vollständiger Neuaufbau ebenfalls fehlgeschlagen: {repair_error}"
            ) from repair_error
        base._set_state(stage=f"{pair}: Daten frisch aufgebaut und geprüft", progress=38)
        return repaired


def _existing_completed_result(request: Any) -> dict[str, Any] | None:
    identity = _identity(request.pair, request.years)
    history = base.analyze_backtest_history(
        base._RESULTS_ROOT,
        current_strategy_path=base._STRATEGY,
        trial_ledger_path=base._TRIAL_LEDGER,
    )
    existing = next(
        (
            dict(row)
            for row in history["runs"]
            if row.get("test_fingerprint") == identity["test_fingerprint"]
        ),
        None,
    )
    if existing is None:
        return None
    experiment, lineage = base.registered_experiment(base._TRIAL_LEDGER, identity["strategy_sha256"])
    existing.update(
        {
            "pair": request.pair,
            "years": request.years,
            "strategy": existing.get("strategy") or base.STRATEGY_NAME,
            "strategy_sha256": identity["strategy_sha256"],
            "reused_existing_result": True,
            "experiment": experiment,
            "experiment_lineage": lineage,
            "test_identity": identity,
        }
    )
    return existing


base._validate_candle_data = _validate_or_repair_candle_data
base._is_within = _audit_boundary_is_within
base._START_GUARD = _reject_manual_start_during_batch


def get_state() -> dict[str, Any]:
    return base.get_state()


def start_backtest(request: Any) -> dict[str, Any]:
    try:
        return base.start_backtest(request)
    except HTTPException as exc:
        detail = str(exc.detail or "")
        if exc.status_code == 409 and detail.startswith("Doppeltest blockiert:"):
            existing = _existing_completed_result(request)
            if existing is not None:
                now = _utc_now()
                base._set_state(
                    status="completed",
                    stage="Vorhandenes identisches Hixton-Ergebnis geladen - kein Doppeltest",
                    progress=100,
                    run_id=existing.get("run_id"),
                    pair=request.pair,
                    years=request.years,
                    started_at=now,
                    finished_at=now,
                    result=existing,
                    error=None,
                )
                return base.get_state()
        raise


def build_router() -> Any:
    router = base.build_router()

    @router.get("/api/v1/testbot/backtest/batch/status")
    async def batch_status() -> dict[str, Any]:
        return get_batch_state()

    @router.post("/api/v1/testbot/backtest/batch/start")
    async def batch_start(request: BatchRequest) -> dict[str, Any]:
        return start_batch(request)

    return router
