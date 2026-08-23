"""Ten-pair adapter for the existing locked Testbot backtest API.

The active paper bot and the backtester share the exact same V12.18
CompressionBreakout250 source and the same ten-pair config. The UI exposes both
single-pair tests with an independent 250-USDT wallet and the real ten-pair
portfolio in which all pairs compete for one shared 250-USDT / 3x80 budget.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

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
ACTIVE_EXPERIMENT_ID = "V12.18-TEN-PAIR-PROFIT-PYRAMID-REPAIR"

base.ALLOWED_PAIRS = TEN_PAIR_UNIVERSE
base.ALLOWED_TARGETS = (*TEN_PAIR_UNIVERSE, base.PORTFOLIO_TARGET)
base.STRATEGY_VERSION = "V12.18"
base._UI_SCRIPT = base._RUNTIME_ROOT / "ui" / "testbot-backtest.js"

_original_validate_candle_data = base._validate_candle_data
_original_is_within = base._is_within
_python_dependency_prefix = Path(sys.prefix).resolve()


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
    return base.build_router()
