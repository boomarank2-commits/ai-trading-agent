"""Ten-pair adapter for the existing locked Testbot backtest API.

The active paper bot and the backtester now share the exact same V12.17
CompressionBreakout250 source and the same ten-pair config.  The UI exposes only
single-pair tests: each requested pair gets its own independent 250-USDT wallet.
The internal PORTFOLIO target remains available for a later explicit 3x80
whole-system test, but it is intentionally not part of the normal UI batch.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

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
V12_15_HASH = "3c5aaf823e16c1a2901c4861fcf6dbc21da4dd0f1314385d78be1f2de86c4a97"
ACTIVE_EXPERIMENT_ID = "V12.17-TEN-PAIR-THREE-CHUNK-PAPER"

base.ALLOWED_PAIRS = TEN_PAIR_UNIVERSE
base.ALLOWED_TARGETS = (*TEN_PAIR_UNIVERSE, base.PORTFOLIO_TARGET)
base._UI_SCRIPT = base._RUNTIME_ROOT / "ui" / "testbot-backtest.js"

_registered_experiment = base.registered_experiment
_original_validate_candle_data = base._validate_candle_data


def _active_registered_experiment(
    ledger_path: Path, strategy_hash: str
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Bind backtests to the active V12.17 paper change and V12.15 lineage."""

    _parent, lineage = _registered_experiment(ledger_path, V12_15_HASH)
    experiment = {
        "experiment_id": ACTIVE_EXPERIMENT_ID,
        "parent_experiment_id": "V12.15-LATE-PROFIT-RATCHET",
        "strategy_version": "V12.17",
        "strategy_hash": strategy_hash,
        "hypothesis": (
            "The accepted V12.15 signal core can be expanded to ten mature Spot "
            "markets while a strict 250-USDT wallet allocates at most three "
            "80-USDT chunks, including a second or third chunk in the same pair "
            "only when that pair produces a genuinely new entry signal."
        ),
        "change_summary": (
            "Active paper universe expanded from six to ten pairs by adding "
            "LINK/TRX/LTC/BCH. Added signal-gated position adjustment so one open "
            "pair may hold up to three independent 80-USDT entry chunks while "
            "global deployed stake remains capped at 240 USDT."
        ),
        "acceptance_criteria": (
            "Paper-only until verified. Each coin is first backtested independently "
            "with its own 250-USDT wallet over user-selected 1y/2y/3y history. "
            "The 'all ten' UI action is ten sequential independent tests, never a "
            "shared 2500-USDT portfolio. Pair-specific tuning follows only after "
            "those diagnostics. A separate shared 250-USDT 3x80 system backtest is "
            "reserved for the final portfolio stage."
        ),
        "result_summary": "Implementation built; financial ten-pair diagnostics not yet accepted.",
        "decision": "ACTIVE_PAPER_ONLY_PENDING_BACKTESTS",
        "lessons": (
            "Standalone pair diagnostics and shared-wallet portfolio behavior are "
            "different questions and must not be combined."
        ),
        "next_experiment": "V12.17-TEN-INDEPENDENT-PAIR-BACKTESTS",
    }
    return experiment, [*lineage, experiment]


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


base.registered_experiment = _active_registered_experiment
base._validate_candle_data = _validate_or_repair_candle_data


def get_state() -> dict[str, Any]:
    return base.get_state()


def start_backtest(request: Any) -> dict[str, Any]:
    return base.start_backtest(request)


def build_router() -> Any:
    return base.build_router()
