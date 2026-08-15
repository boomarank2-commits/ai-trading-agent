from __future__ import annotations

# These tests are intentionally part of the Windows Backtest UI contract CI.
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from runtime import testbot_backtest_api as api


def _write_dates(path, dates) -> None:
    pd.DataFrame({"date": pd.to_datetime(dates, utc=True)}).to_feather(path)


def test_inspect_candle_file_accepts_complete_minute_window(tmp_path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(minutes=9)
    path = tmp_path / "BTC_USDT-1m.feather"
    _write_dates(path, pd.date_range(start, end, freq="1min"))

    report = api._inspect_candle_file(path, "1m", start, end)

    assert report["rows_in_required_window"] == 10
    assert report["duplicates"] == 0
    assert report["gaps"] == 0


def test_inspect_candle_file_rejects_duplicate_timestamp(tmp_path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    path = tmp_path / "BTC_USDT-1m.feather"
    dates = list(pd.date_range(start, periods=5, freq="1min"))
    dates.insert(3, dates[2])
    _write_dates(path, dates)

    with pytest.raises(RuntimeError, match="Duplikate=1"):
        api._inspect_candle_file(path, "1m", start, start + timedelta(minutes=4))


def test_inspect_candle_file_rejects_missing_candle(tmp_path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    path = tmp_path / "ETH_USDT-15m.feather"
    dates = [
        start,
        start + timedelta(minutes=15),
        start + timedelta(minutes=45),
        start + timedelta(minutes=60),
    ]
    _write_dates(path, dates)

    with pytest.raises(RuntimeError, match="Luecken=1"):
        api._inspect_candle_file(path, "15m", start, start + timedelta(minutes=60))


def test_inspect_candle_file_rejects_stale_end(tmp_path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    path = tmp_path / "SOL_USDT-4h.feather"
    _write_dates(path, pd.date_range(start, periods=4, freq="4h"))

    with pytest.raises(RuntimeError, match="enden zu frueh"):
        api._inspect_candle_file(path, "4h", start, start + timedelta(hours=24))
