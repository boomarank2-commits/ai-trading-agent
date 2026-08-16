"""Deterministic walk-forward window and fold-summary primitives.

This module defines causal train/test windows and comparable fold summaries. It
does not optimize a strategy and does not select a winner from a holdout. The
actual strategy runner must consume these windows without looking ahead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median
from typing import Iterable


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    index: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("index must be non-negative")
        if not self.train_start < self.train_end:
            raise ValueError("train window must be non-empty")
        if not self.test_start < self.test_end:
            raise ValueError("test window must be non-empty")
        if self.train_end > self.test_start:
            raise ValueError("train/test windows must not overlap")

    @property
    def train_days(self) -> int:
        return (self.train_end - self.train_start).days

    @property
    def test_days(self) -> int:
        return (self.test_end - self.test_start).days


@dataclass(frozen=True, slots=True)
class WalkForwardFoldMetrics:
    window_index: int
    net_return: float
    profit_factor: float
    sharpe: float
    max_drawdown: float
    profitable_at_cost_stress: bool
    profitable_with_one_bar_lag: bool


def build_walk_forward_windows(
    start: date,
    end_exclusive: date,
    *,
    train_days: int,
    test_days: int,
    step_days: int | None = None,
) -> list[WalkForwardWindow]:
    """Build half-open `[start, end)` causal walk-forward windows."""

    if not start < end_exclusive:
        raise ValueError("start must precede end_exclusive")
    if train_days <= 0 or test_days <= 0:
        raise ValueError("train_days and test_days must be positive")
    step = test_days if step_days is None else step_days
    if step <= 0:
        raise ValueError("step_days must be positive")

    windows: list[WalkForwardWindow] = []
    cursor = start
    index = 0
    while True:
        train_start = cursor
        train_end = train_start + timedelta(days=train_days)
        test_start = train_end
        test_end = test_start + timedelta(days=test_days)
        if test_end > end_exclusive:
            break
        windows.append(
            WalkForwardWindow(
                index=index,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
        index += 1
        cursor += timedelta(days=step)
    return windows


def validate_walk_forward_windows(windows: Iterable[WalkForwardWindow]) -> None:
    items = list(windows)
    if not items:
        raise ValueError("walk-forward requires at least one window")
    expected_indices = list(range(len(items)))
    if [window.index for window in items] != expected_indices:
        raise ValueError("walk-forward indices must be contiguous from zero")
    for previous, current in zip(items, items[1:], strict=False):
        if current.train_start <= previous.train_start:
            raise ValueError("walk-forward train starts must be strictly increasing")
        if current.test_end <= previous.test_end:
            raise ValueError("walk-forward test ends must be strictly increasing")


def summarize_walk_forward(
    metrics: Iterable[WalkForwardFoldMetrics],
) -> dict[str, float | int | bool]:
    items = list(metrics)
    if not items:
        raise ValueError("walk-forward summary requires fold metrics")
    indices = [item.window_index for item in items]
    if len(set(indices)) != len(indices):
        raise ValueError("duplicate walk-forward fold metric")
    return {
        "fold_count": len(items),
        "positive_return_folds": sum(item.net_return > 0 for item in items),
        "median_net_return": median(item.net_return for item in items),
        "median_profit_factor": median(item.profit_factor for item in items),
        "median_sharpe": median(item.sharpe for item in items),
        "worst_max_drawdown": max(item.max_drawdown for item in items),
        "all_cost_stress_profitable": all(
            item.profitable_at_cost_stress for item in items
        ),
        "all_one_bar_lag_profitable": all(
            item.profitable_with_one_bar_lag for item in items
        ),
    }
