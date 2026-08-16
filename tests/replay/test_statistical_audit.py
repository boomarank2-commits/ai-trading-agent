from __future__ import annotations

import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from statistical_audit import deflated_sharpe_probability, pbo_cscv


def test_dsr_probability_is_bounded() -> None:
    selected = [0.01, -0.005, 0.007, 0.002, -0.003, 0.011] * 8
    result = deflated_sharpe_probability(
        selected, all_trial_sharpes=[0.2, 0.4, 0.6, 0.1], periods_per_year=52
    )
    assert 0 <= result["deflated_sharpe_probability"] <= 1


def test_pbo_cscv_is_deterministic_and_bounded() -> None:
    matrix = []
    for index in range(80):
        matrix.append(
            [
                0.01 if index % 5 else -0.02,
                0.004 if index % 2 else -0.003,
                0.002,
            ]
        )
    first = pbo_cscv(matrix, partitions=8)
    second = pbo_cscv(matrix, partitions=8)
    assert first == second
    assert 0 <= first["pbo"] <= 1
