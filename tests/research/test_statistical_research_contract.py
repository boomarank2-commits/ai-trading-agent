from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from statistical_audit import (
    annualized_sharpe,
    deflated_sharpe_probability,
    pbo_cscv,
)


def _return_matrix() -> list[list[float]]:
    return [
        [0.01, 0.005, -0.002],
        [0.02, -0.004, 0.003],
        [-0.01, 0.006, 0.001],
        [0.015, 0.002, -0.001],
        [0.005, -0.003, 0.004],
        [-0.004, 0.004, 0.002],
        [0.012, 0.001, -0.003],
        [0.007, 0.003, 0.001],
        [-0.003, -0.001, 0.002],
        [0.009, 0.005, 0.0005],
        [0.006, -0.002, 0.003],
        [0.011, 0.002, -0.001],
        [0.004, 0.001, 0.002],
        [-0.002, 0.003, 0.001],
        [0.008, -0.001, 0.004],
        [0.003, 0.002, -0.002],
    ]


def test_pbo_is_deterministic_for_same_trial_universe() -> None:
    matrix = _return_matrix()
    first = pbo_cscv(matrix, partitions=8)
    second = pbo_cscv(matrix, partitions=8)
    assert first == second
    assert first["strategy_count"] == 3
    assert first["period_count"] == len(matrix)
    assert 0.0 <= first["pbo"] <= 1.0


def test_dsr_probability_is_bounded_and_repeatable() -> None:
    matrix = _return_matrix()
    columns = [[row[index] for row in matrix] for index in range(3)]
    sharpes = [annualized_sharpe(column) for column in columns]
    first = deflated_sharpe_probability(columns[0], all_trial_sharpes=sharpes)
    second = deflated_sharpe_probability(columns[0], all_trial_sharpes=sharpes)
    assert first == second
    assert math.isfinite(first["selected_sharpe"])
    assert 0.0 <= first["deflated_sharpe_probability"] <= 1.0


def test_pbo_rejects_inadequate_or_malformed_trial_inputs() -> None:
    with pytest.raises(ValueError, match="not enough rows"):
        pbo_cscv([[0.1, 0.2], [0.2, 0.1]], partitions=8)
    with pytest.raises(ValueError, match="at least two"):
        pbo_cscv([[0.1] for _ in range(8)], partitions=8)
    with pytest.raises(ValueError, match="even integer"):
        pbo_cscv(_return_matrix(), partitions=5)
