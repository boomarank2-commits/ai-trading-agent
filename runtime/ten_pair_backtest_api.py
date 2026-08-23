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
    from runtime import backtest_history_analysis as history
    from runtime import testbot_backtest_api as base
except ModuleNotFoundError:  # Direct runtime/ execution.
    import backtest_history_analysis as history
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
# mutable globals to isolated research artifacts before any request runs.
base.ALLOWED_PAIRS = TEN_PAIR_UNIVERSE
base.ALLOWED_TARGETS = (*TEN_PAIR_UNIVERSE, base.PORTFOLIO_TARGET)
base.STRATEGY_NAME = RESEARCH_STRATEGY_NAME
base._CONFIG = base._USERDIR / "config-ten-pair-research.json"
base._STRATEGY = base._USERDIR / "strategies" / f"{RESEARCH_STRATEGY_NAME}.py"
base._UI_SCRIPT = base._RUNTIME_ROOT / "ui" / "testbot-backtest-ten-pair.js"
base._RESULTS_ROOT = base._USERDIR / "backtest_results" / "ten_pair_research"

# The existing history reader is generic except for the archived strategy
# filename and the expected pair matrix. Keep research evidence in its own root
# and teach that reader the V12.17 class/universe without touching old evidence.
history.STRATEGY_NAME = RESEARCH_STRATEGY_NAME
_original_matrix_summaries = history._matrix_summaries


def _ten_pair_matrix_summaries(
    completed: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = _original_matrix_summaries(completed)
    for row in rows:
        if row.get("strategy_version") != "V12.17":
            continue
        digest = str(row.get("strategy_sha256") or "")
        relevant = [
            run
            for run in completed
            if run.get("strategy_sha256") == digest
            and run.get("pair") != "PORTFOLIO"
        ]
        latest_by_cell: dict[tuple[str, int | None], dict[str, Any]] = {}
        for run in relevant:
            cell = (str(run.get("pair")), run.get("period_years"))
            previous = latest_by_cell.get(cell)
            if previous is None or (
                str(run.get("backtest_end")),
                str(run.get("run_id")),
            ) > (
                str(previous.get("backtest_end")),
                str(previous.get("run_id")),
            ):
                latest_by_cell[cell] = run
        selected = list(latest_by_cell.values())
        periods = sorted(
            {
                int(run["period_years"])
                for run in selected
                if run.get("period_years") is not None
            }
        )
        expected = {
            (pair, years) for pair in TEN_PAIR_UNIVERSE for years in periods
        }
        row["matrix_pairs"] = list(TEN_PAIR_UNIVERSE)
        row["period_years"] = periods
        row["latest_cells"] = len(selected)
        row["expected_cells"] = len(expected)
        row["matrix_complete"] = bool(periods) and expected == set(latest_by_cell)
        row["current_six_run_matrix"] = False
        row["current_twelve_cell_matrix"] = False
        row["current_twenty_cell_matrix"] = (
            row["matrix_complete"] and periods == [1, 3]
        )
        row["positive_cells"] = sum(
            float(run.get("profit_usdt") or 0.0) > 0 for run in selected
        )
        row["independent_profit_sum_usdt"] = round(
            sum(float(run.get("profit_usdt") or 0.0) for run in selected), 4
        )
        profits = [float(run.get("profit_pct") or 0.0) for run in selected]
        row["median_profit_pct"] = history._median(profits) if profits else 0.0
        row["total_trades_across_overlapping_cells"] = sum(
            int(run.get("trades") or 0) for run in selected
        )
        row["worst_max_drawdown_pct"] = round(
            max(
                (
                    float(run.get("max_drawdown_pct") or 0.0)
                    for run in selected
                ),
                default=0.0,
            ),
            2,
        )
        row["latest_backtest_end"] = max(
            (str(run.get("backtest_end") or "") for run in selected),
            default="",
        )
    return rows


history._matrix_summaries = _ten_pair_matrix_summaries


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
            "exit, stop, protection, fee, stake or slot rule is intentionally "
            "changed."
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
