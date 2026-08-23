"""Ten-pair adapter for the existing locked Testbot backtest API.

The active paper bot and the backtester now share the exact same V12.17
CompressionBreakout250 source and the same ten-pair config.  The UI exposes only
single-pair tests: each requested pair gets its own independent 250-USDT wallet.
The internal PORTFOLIO target remains available for a later explicit 3x80
whole-system test, but it is intentionally not part of the normal UI batch.
"""

from __future__ import annotations

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


base.registered_experiment = _active_registered_experiment


def get_state() -> dict[str, Any]:
    return base.get_state()


def start_backtest(request: Any) -> dict[str, Any]:
    return base.start_backtest(request)


def build_router() -> Any:
    return base.build_router()
