"""Ten-pair adapter for the existing locked Testbot backtest API.

The active paper bot and the backtester share the exact same V12.33
CompressionBreakout250 source and the same ten-pair config. The UI exposes both
single-pair tests with an independent 250-USDT wallet and the real ten-pair
portfolio in which all pairs compete for one shared 250-USDT / 3x80 budget.
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
except ModuleNotFoundError:  # Direct runtime/ execution.
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
ACTIVE_EXPERIMENT_ID = "V12.33-LTC-NO-TRADE-COUNTERFACTUAL"

base.ALLOWED_PAIRS = TEN_PAIR_UNIVERSE
base.ALLOWED_TARGETS = (*TEN_PAIR_UNIVERSE, base.PORTFOLIO_TARGET)
base.STRATEGY_VERSION = "V12.33"
base._UI_SCRIPT = base._RUNTIME_ROOT / "ui" / "testbot-backtest.js"

_original_validate_candle_data = base._validate_candle_data
_original_is_within = base._is_within
_python_dependency_prefix = Path(sys.prefix).resolve()
_BATCH_ROOT = base._USERDIR / "backtest_results" / "_BATCHES"
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
        "profit_usdt",
        "profit_pct",
        "trades",
        "winrate_pct",
        "profit_factor",
        "max_drawdown_pct",
        "capital_time_utilization_pct",
        "no_position_time_pct",
        "total_entry_chunks",
        "additional_entry_chunks",
        "max_active_entry_chunks",
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
        "reused_existing_result",
        "historical_context",
        "timing",
    )
    return {field: result.get(field) for field in fields}


def _batch_fingerprint(years: int) -> tuple[str, list[dict[str, Any]]]:
    source = base._STRATEGY.read_bytes()
    config = base.load_config_contract(base._CONFIG)
    cases = []
    for pair in TEN_PAIR_UNIVERSE:
        identity = base.build_test_identity(
            strategy_source=source,
            pair=pair,
            years=years,
            config=config,
        )
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
    material = {
        "schema_version": 1,
        "strategy_sha256": base._sha256(base._STRATEGY),
        "years": years,
        "cases": [case["test_fingerprint"] for case in cases],
    }
    fingerprint = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return fingerprint, cases


def _batch_dir(batch_id: str) -> Path:
    return _BATCH_ROOT / batch_id


def _persist_batch(state: dict[str, Any]) -> None:
    batch_id = str(state["batch_id"])
    directory = _batch_dir(batch_id)
    directory.mkdir(parents=True, exist_ok=True)
    base._write_json(directory / "batch-plan.json", state["plan"])
    base._write_json(directory / "batch-result.json", state)
    base._write_json(
        _BATCH_POINTER,
        {
            "schema_version": 1,
            "batch_id": batch_id,
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
        state["stage"] = "Bot wurde neu gestartet; Batch kann fortgesetzt werden"
        state["updated_at_utc"] = _utc_now()
        _persist_batch(state)
    return state


_batch_state: dict[str, Any] | None = _load_latest_batch()


def get_batch_state() -> dict[str, Any]:
    with _batch_lock:
        if _batch_state is None:
            return {
                "status": "idle",
                "stage": "Kein Zehner-Batch gestartet",
                "progress": 0,
                "cases": [],
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


def _new_batch(years: int, fingerprint: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    batch_id = f"{run_stamp}-{uuid.uuid4().hex[:8]}"
    history = base.analyze_backtest_history(
        base._RESULTS_ROOT,
        current_strategy_path=base._STRATEGY,
        trial_ledger_path=base._TRIAL_LEDGER,
    )
    histories_before = {
        pair: base.build_pair_history_context(history, pair=pair, years=years)
        for pair in TEN_PAIR_UNIVERSE
    }
    plan = {
        "schema_version": 1,
        "batch_id": batch_id,
        "batch_fingerprint": fingerprint,
        "created_at_utc": _utc_now(),
        "experiment_id": ACTIVE_EXPERIMENT_ID,
        "strategy_version": base.STRATEGY_VERSION,
        "strategy_sha256": base._sha256(base._STRATEGY),
        "source_commit": base.current_git_commit(base._REPO_ROOT),
        "years": years,
        "wallet_contract": "ten independent 250-USDT wallets; never summed as portfolio",
        "cases": [
            {
                "pair": case["pair"],
                "years": years,
                "test_fingerprint": case["test_fingerprint"],
                "history_before": histories_before[pair],
            }
            for pair, case in zip(TEN_PAIR_UNIVERSE, cases, strict=True)
        ],
    }
    return {
        "schema_version": 1,
        "batch_id": batch_id,
        "batch_fingerprint": fingerprint,
        "status": "running",
        "stage": "Zehner-Batch wird vorbereitet",
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
        "plan": plan,
    }


def _run_batch_cases() -> None:
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
            stage=f"{pair} wird getestet ({index + 1}/{total})",
            progress=round(100 * index / max(1, total), 2),
        )
        try:
            planned_strategy_hash = str(state.get("plan", {}).get("strategy_sha256") or "")
            if base._sha256(base._STRATEGY) != planned_strategy_hash:
                raise RuntimeError(
                    "Aktive Strategie wurde während des Zehner-Batches verändert; "
                    "gemischter Batch wird verweigert."
                )
            started = start_backtest(base.BacktestRequest(pair=pair, years=years))
            result_state = started
            while result_state.get("status") == "running":
                time.sleep(1)
                result_state = base.get_state()
            if result_state.get("status") != "completed" or not isinstance(
                result_state.get("result"), dict
            ):
                raise RuntimeError(str(result_state.get("error") or "Backtest fehlgeschlagen"))
            result = dict(result_state["result"])
            result_identity = result.get("test_identity")
            actual_fingerprint = (
                result_identity.get("test_fingerprint")
                if isinstance(result_identity, dict)
                else None
            )
            if actual_fingerprint != case["test_fingerprint"]:
                raise RuntimeError(
                    f"{pair}: Ergebnis-Fingerprint passt nicht zum gespeicherten Batchplan."
                )
            case["status"] = "reused" if result.get("reused_existing_result") else "completed"
            case["result"] = _compact_result(result)
            case["error"] = None
        except Exception as exc:
            case["status"] = "failed"
            case["error"] = str(getattr(exc, "detail", None) or exc)
        state = get_batch_state()
        state["cases"][index] = case
        completed = sum(
            item.get("status") in {"completed", "reused"} for item in state["cases"]
        )
        failed = sum(item.get("status") == "failed" for item in state["cases"])
        _set_batch_state(
            cases=state["cases"],
            completed_cases=completed,
            failed_cases=failed,
            progress=round(100 * (index + 1) / max(1, total), 2),
        )

    state = get_batch_state()
    failed = int(state.get("failed_cases") or 0)
    _set_batch_state(
        status="completed_with_errors" if failed else "completed",
        stage="Zehner-Batch mit Fehlern beendet" if failed else "Alle zehn Einzeltests fertig",
        progress=100,
        current_pair=None,
        finished_at_utc=_utc_now(),
    )


def _run_batch() -> None:
    _batch_worker_context.active = True
    try:
        _run_batch_cases()
    except Exception as exc:
        with suppress(Exception):
            _set_batch_state(
                status="failed",
                stage="Zehner-Batch ist technisch fehlgeschlagen",
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
        raise HTTPException(
            status_code=409,
            detail="Der Zehner-Batch läuft bereits; kein paralleler Einzeltest erlaubt.",
        )


def start_batch(request: BatchRequest) -> dict[str, Any]:
    global _batch_state
    if request.years not in base.ALLOWED_YEARS:
        raise HTTPException(status_code=400, detail="Zeitraum muss 1, 2 oder 3 Jahre sein.")
    if base.get_state().get("status") == "running":
        raise HTTPException(status_code=409, detail="Es läuft bereits ein einzelner Backtest.")
    fingerprint, cases = _batch_fingerprint(request.years)
    with _batch_lock:
        current = _batch_state
        if current and current.get("status") == "running":
            return json.loads(json.dumps(current))
        if current and current.get("batch_fingerprint") == fingerprint:
            if current.get("status") == "completed":
                return json.loads(json.dumps(current))
            _batch_state = current
            _batch_state["status"] = "running"
            _batch_state["stage"] = "Unvollständiger Zehner-Batch wird fortgesetzt"
            _batch_state["batch_error"] = None
            _batch_state["updated_at_utc"] = _utc_now()
            _persist_batch(_batch_state)
        else:
            _batch_state = _new_batch(request.years, fingerprint, cases)
            _persist_batch(_batch_state)
        response = json.loads(json.dumps(_batch_state))
    threading.Thread(target=_run_batch, daemon=True).start()
    return response


def _audit_boundary_is_within(path: Path, root: Path) -> bool:
    """Treat the exact active Python environment as dependency space, not repo source.

    STARTBOT intentionally keeps ``.venv`` below the repository on Windows.
    Freqtrade, pandas, pyarrow and other locked dependencies are therefore
    physically below the repo root even though they are not repository-owned
    strategy/config inputs.  Excluding only the exact ``sys.prefix`` subtree from
    the repo-read check keeps the audit strict for every other repository file.
    """

    resolved_root = root.resolve()
    if resolved_root == base._REPO_ROOT.resolve() and _original_is_within(
        path, _python_dependency_prefix
    ):
        return False
    return _original_is_within(path, root)


def _validate_or_repair_candle_data(
    pair: str,
    download_start: Any,
    required_end: Any,
) -> list[dict[str, Any]]:
    """Repair stale/interrupted local candle caches once before failing a run.

    Freqtrade's normal download path appends/prepends existing files.  That does
    not necessarily repair an old hole in the middle of a Feather file.  For a
    failed integrity check we therefore rebuild only this pair's four historical
    files from Binance and validate the fresh files again.  Strategy logic and
    backtest parameters remain unchanged.
    """

    try:
        return _original_validate_candle_data(pair, download_start, required_end)
    except RuntimeError as first_error:
        base._set_state(
            stage=f"Lokale {pair}-Marktdaten werden wegen einer Datenluecke neu aufgebaut",
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
                f"Marktdatenpruefung fuer {pair} fehlgeschlagen. "
                f"Erster Fehler: {first_error}. Vollstaendiger Neuaufbau ebenfalls "
                f"fehlgeschlagen: {repair_error}"
            ) from repair_error

        base._set_state(
            stage=f"{pair}-Marktdaten frisch aufgebaut und erfolgreich geprueft",
            progress=38,
        )
        return repaired


def _existing_completed_result(request: Any) -> dict[str, Any] | None:
    """Return an already completed identical run instead of rerunning it.

    The research contract still forbids duplicate execution.  Reusing the
    preserved result lets an interrupted ten-pair batch resume later while the
    UI can still show metrics for coins which were already completed.
    """

    source = base._STRATEGY.read_bytes()
    identity = base.build_test_identity(
        strategy_source=source,
        pair=request.pair,
        years=request.years,
        config=base.load_config_contract(base._CONFIG),
    )
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

    recorded_result = existing.get("experiment_result")
    if isinstance(recorded_result, dict):
        existing["historical_context"] = recorded_result.get("historical_context")
        existing["timing"] = recorded_result.get("timing")

    experiment, lineage = base.registered_experiment(
        base._TRIAL_LEDGER, identity["strategy_sha256"]
    )
    existing.update(
        {
            "pair": request.pair,
            "years": request.years,
            "strategy": existing.get("strategy") or base.STRATEGY_NAME,
            "strategy_sha256": identity["strategy_sha256"],
            "coverage_validated": True,
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
                now = datetime.now(UTC).isoformat()
                base._set_state(
                    status="completed",
                    stage="Vorhandenes identisches Ergebnis geladen - kein Doppeltest ausgefuehrt",
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
