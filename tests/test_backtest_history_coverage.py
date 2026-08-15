from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from runtime import testbot_backtest_api as api


def test_closed_timerange_is_absolute_and_closed() -> None:
    start = datetime(2023, 6, 2, tzinfo=UTC)
    end = datetime(2026, 8, 15, 20, 30, tzinfo=UTC)
    assert api._closed_timerange(start, end) == "20230602-20260815"


def test_three_year_request_rejects_old_733_day_result() -> None:
    now = datetime(2026, 8, 15, 20, 30, tzinfo=UTC)
    requested_start = now - timedelta(days=365 * 3)
    result = {
        "backtest_start": "2024-08-12 04:00:00",
        "backtest_end": "2026-08-15 20:00:00",
        "backtest_days": 733,
    }

    with pytest.raises(RuntimeError, match="Backtest-Zeitraum unvollstaendig"):
        api._validate_result_coverage(result, requested_start, now, 3)


def test_three_year_request_accepts_complete_result() -> None:
    now = datetime(2026, 8, 15, 20, 30, tzinfo=UTC)
    requested_start = now - timedelta(days=365 * 3)
    result = {
        "backtest_start": "2023-08-16 00:00:00",
        "backtest_end": "2026-08-15 20:00:00",
        "backtest_days": 1095,
    }

    api._validate_result_coverage(result, requested_start, now, 3)
