"""Local-only backtest API used by the Testbot FreqUI extension.

This module deliberately does not contain a second trading strategy. Every run
hashes and loads the exact strategy file used by STARTBOT, downloads public
Binance candles, and launches Freqtrade backtesting with the same config plus
1-minute detail candles for more realistic intrabar fills.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import Response

ALLOWED_PAIRS = ("BTC/USDT", "ETH/USDT", "SOL/USDT")
ALLOWED_YEARS = (1, 2, 3)
STRATEGY_NAME = "CompressionBreakout250"

_RUNTIME_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _RUNTIME_ROOT.parent
_USERDIR = _RUNTIME_ROOT / "user_data"
_CONFIG = _USERDIR / "config.json"
_PUBLIC_CONFIG = _USERDIR / "config-public.json"
_STRATEGY = _USERDIR / "strategies" / f"{STRATEGY_NAME}.py"
_BACKTEST_RUNNER = _RUNTIME_ROOT / "locked_backtest_freqtrade.py"
_UI_SCRIPT = _RUNTIME_ROOT / "ui" / "testbot-backtest.js"
_RESULTS_ROOT = _USERDIR / "backtest_results" / "ui"

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


def _clean_subprocess_environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("FREQTRADE__")
        and key != "AI_TRADING_KILL_SWITCH_FILE"
    }
    env["PYTHONUTF8"] = "1"
    return env


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
    candidates = [
        path
        for path in run_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".zip", ".json"}
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
        # Some historical result formats store an absolute drawdown in this field.
        drawdown_pct = (_number(strategy.get("max_drawdown_account")) * 100.0)
    else:
        drawdown_pct = drawdown_value * 100.0

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
        "result_file": str(result_file),
    }


def _execute_backtest(run_id: str, pair: str, years: int) -> None:
    run_dir = _RESULTS_ROOT / run_id
    log_path = run_dir / "backtest.log"
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
        for required in (_CONFIG, _PUBLIC_CONFIG, _STRATEGY, _BACKTEST_RUNNER):
            if not required.is_file():
                raise RuntimeError(f"Erforderliche Datei fehlt: {required}")

        strategy_hash = _sha256(_STRATEGY)
        now = datetime.now(timezone.utc)
        requested_start = now - timedelta(days=365 * years)
        # Download a small warmup before the visible test window. The strategy
        # currently needs 400 x 15m startup candles (~4.2 days).
        download_start = requested_start - timedelta(days=7)
        requested_timerange = requested_start.strftime("%Y%m%d") + "-"
        download_timerange = download_start.strftime("%Y%m%d") + "-"

        _set_state(stage="Binance-Daten werden geladen", progress=10)
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
            "15m",
            "1m",
            "--pairs",
            pair,
            "--trading-mode",
            "spot",
            "--timerange",
            download_timerange,
        ]
        _run_checked(download_args, log_path)

        _set_state(stage="Historische Daten geladen - Backtest startet", progress=45)
        backtest_args = [
            sys.executable,
            str(_BACKTEST_RUNNER),
            "--strategy-source",
            str(_STRATEGY),
            "--strategy-sha256",
            strategy_hash,
            "--strategy-class",
            STRATEGY_NAME,
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
            pair,
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
        _set_state(stage="Aktueller Bot wird historisch simuliert", progress=60)
        _run_checked(backtest_args, log_path)

        _set_state(stage="Ergebnis wird ausgewertet", progress=92)
        result_file = _find_result_file(run_dir)
        result = _extract_result(result_file, pair, years, strategy_hash)
        _set_state(
            status="completed",
            stage="Fertig",
            progress=100,
            finished_at=datetime.now(timezone.utc).isoformat(),
            result=result,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 - background job must report all failures
        _set_state(
            status="failed",
            stage="Fehler",
            progress=100,
            finished_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
            result=None,
        )


def start_backtest(request: BacktestRequest) -> dict[str, Any]:
    if request.pair not in ALLOWED_PAIRS:
        raise HTTPException(status_code=400, detail="Dieses Handelspaar ist nicht freigegeben.")
    if request.years not in ALLOWED_YEARS:
        raise HTTPException(status_code=400, detail="Zeitraum muss 1, 2 oder 3 Jahre sein.")

    current = get_state()
    if current["status"] == "running":
        raise HTTPException(status_code=409, detail="Es laeuft bereits ein Backtest.")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    _set_state(
        status="running",
        stage="Backtest wird vorbereitet",
        progress=2,
        run_id=run_id,
        pair=request.pair,
        years=request.years,
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        result=None,
        error=None,
    )
    thread = threading.Thread(
        target=_execute_backtest,
        args=(run_id, request.pair, request.years),
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
