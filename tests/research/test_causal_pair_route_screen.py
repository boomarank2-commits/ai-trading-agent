import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research"))

from causal_pair_route_screen import Candidate, _simulate  # noqa: E402


def test_open_trade_is_liquidated_at_last_close_before_window_end() -> None:
    start = pd.Timestamp("2025-01-01", tz="UTC")
    end = pd.Timestamp("2025-01-01 16:00", tz="UTC")
    frame = pd.DataFrame(
        {
            "date": pd.date_range(start, periods=5, freq="4h"),
            "open": [100.0, 100.0, 100.0, 108.0, 50.0],
            "high": [101.0, 101.0, 109.0, 111.0, 51.0],
            "low": [99.0, 99.0, 99.0, 107.0, 1.0],
            "close": [100.0, 100.0, 108.0, 110.0, 1.0],
        }
    )
    candidate = Candidate(
        family="boundary_test",
        parameters={},
        entry=pd.Series([False, True, False, False, False]),
        exit=pd.Series(False, index=frame.index),
    )

    result = _simulate(frame, candidate, start, end, fee=0.002)

    expected = 80.0 * (1.10 * 0.998 / 1.002 - 1.0)
    assert result.trades == 1
    assert result.profit_usdt == pytest.approx(expected, abs=0.0001)
    # The candle exactly at `end` is exclusive; its artificial crash cannot
    # affect the result.
    assert result.profit_usdt > 0
