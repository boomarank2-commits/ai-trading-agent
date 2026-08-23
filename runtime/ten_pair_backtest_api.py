"""Research-only ten-pair backtest facade for the existing Testbot UI API.

The running V12.15 paper bot remains on its six approved pairs. This module
reuses the locked backtest machinery but points it at the isolated V12.17
research strategy/config and exposes the ten-pair universe only to historical
research. Exact source/config hashes still become part of each test identity and
existing fingerprints remain blocked.
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
EXISTING_APPROVED_PAIRS = TEN_PAIR_UNIVERSE[:6]
NEW_RESEARCH_PAIRS = TEN_PAIR_UNIVERSE[6:]
RESEARCH_STRATEGY_NAME = "CompressionBreakout250TenPair"
RESEARCH_EXPERIMENT_ID = "V12.17-TEN-PAIR-RESEARCH-UNIVERSE"

# Reuse the mature locked download/audit/backtest implementation but bind all
# mutable globals to the isolated research artifacts before any request runs.
base.ALLOWED_PAIRS = TEN_PAIR_UNIVERSE
base.ALLOWED_TARGETS = (*TEN_PAIR_UNIVERSE, base.PORTFOLIO_TARGET)
base.STRATEGY_NAME = RESEARCH_STRATEGY_NAME
base._CONFIG = base._USERDIR / "config-ten-pair-research.json"
base._STRATEGY = base._USERDIR / "strategies" / f"{RESEARCH_STRATEGY_NAME}.py"
base._UI_SCRIPT = base._RUNTIME_ROOT / "ui" / "testbot-backtest-ten-pair.js"


def _research_registered_experiment(
    _ledger_path: Path, strategy_hash: str
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Pre-register V12.17 without pretending it is already promoted.

    The raw strategy SHA is calculated from the exact file at request time and
    is inserted into the run plan. Promotion back into the active bot remains a
    separate manual decision after the individual and shared-wallet gates.
    """

    experiment = {
        "experiment_id": RESEARCH_EXPERIMENT_ID,
        "parent_experiment_id": "V12.15-LATE-PROFIT-RATCHET",
        "strategy_version": "V12.17",
        "strategy_hash": strategy_hash,
        "hypothesis": (
            "Adding LINK/TRX/LTC/BCH to the unchanged V12.15 broad-core signal "
            "path can add useful opportunities without degrading the shared "
            "250-USDT portfolio."
        ),
        "change_summary": (
            "Research-only universe expansion from six to ten pairs; no entry, "
            "exit, stop, protection, fee, stake or slot rule is intentionally changed."
        ),
        "acceptance_criteria": (
            "Diagnose every pair over fixed 1y/3y windows; judge promotion only "
            "with the chronological shared 250-USDT wallet, max 3x80 USDT, and "
            "reject candidates that degrade core PnL, PF, drawdown or slot quality."
        ),
        "result_summary": "Not run; research-only candidate.",
        "decision": "PLANNED_RESEARCH_ONLY",
        "lessons": (
            "ADA V12.16 showed that positive standalone PnL is insufficient when "
            "slot displacement harms the existing portfolio."
        ),
        "next_experiment": "V12.17-PAIR-DIAGNOSTICS-AND-SHARED-PORTFOLIO",
    }
    return experiment, [experiment]


# `_prepare_run_contract` resolves this name dynamically from the base module.
# Replacing it here keeps exact source/config fingerprinting while avoiding a
# false central-ledger promotion before the research candidate has run.
base.registered_experiment = _research_registered_experiment


def get_state() -> dict[str, Any]:
    return base.get_state()


def start_backtest(request: Any) -> dict[str, Any]:
    return base.start_backtest(request)


def build_router() -> Any:
    return base.build_router()
