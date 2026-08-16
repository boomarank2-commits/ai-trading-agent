from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from walk_forward import (
    WalkForwardFoldMetrics,
    WalkForwardWindow,
    build_walk_forward_windows,
    summarize_walk_forward,
    validate_walk_forward_windows,
)


def test_windows_are_causal_half_open_and_repeatable() -> None:
    first = build_walk_forward_windows(
        date(2020, 1, 1),
        date(2024, 1, 1),
        train_days=365,
        test_days=90,
        step_days=90,
    )
    second = build_walk_forward_windows(
        date(2020, 1, 1),
        date(2024, 1, 1),
        train_days=365,
        test_days=90,
        step_days=90,
    )
    assert first == second
    assert first
    validate_walk_forward_windows(first)
    for window in first:
        assert window.train_end == window.test_start
        assert window.train_start < window.train_end <= window.test_start < window.test_end


def test_window_rejects_train_test_overlap() -> None:
    with pytest.raises(ValueError, match="must not overlap"):
        WalkForwardWindow(
            index=0,
            train_start=date(2024, 1, 1),
            train_end=date(2024, 6, 1),
            test_start=date(2024, 5, 1),
            test_end=date(2024, 7, 1),
        )


def test_summary_keeps_cost_and_lag_stress_visible() -> None:
    summary = summarize_walk_forward(
        [
            WalkForwardFoldMetrics(0, 0.04, 1.4, 1.1, 0.07, True, True),
            WalkForwardFoldMetrics(1, -0.01, 0.9, 0.2, 0.09, False, True),
            WalkForwardFoldMetrics(2, 0.03, 1.3, 0.9, 0.08, True, False),
        ]
    )
    assert summary["fold_count"] == 3
    assert summary["positive_return_folds"] == 2
    assert summary["median_profit_factor"] == 1.3
    assert summary["worst_max_drawdown"] == 0.09
    assert summary["all_cost_stress_profitable"] is False
    assert summary["all_one_bar_lag_profitable"] is False


def test_empty_or_duplicate_fold_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="at least one window"):
        validate_walk_forward_windows([])
    with pytest.raises(ValueError, match="fold metrics"):
        summarize_walk_forward([])
    duplicate = WalkForwardFoldMetrics(0, 0.01, 1.1, 0.5, 0.05, True, True)
    with pytest.raises(ValueError, match="duplicate"):
        summarize_walk_forward([duplicate, duplicate])
