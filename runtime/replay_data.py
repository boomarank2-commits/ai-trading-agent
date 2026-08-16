"""Historical Binance Feather validation and reproducible data manifests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

TIMEFRAME_SECONDS = {"1m": 60, "15m": 900, "1h": 3600, "4h": 14400}
REQUIRED_TIMEFRAMES = ("1m", "15m", "1h", "4h")
PAIRS = ("BTC/USDT", "ETH/USDT", "SOL/USDT")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def feather_path(data_root: Path, pair: str, timeframe: str) -> Path:
    return data_root / f"{pair.replace('/', '_')}-{timeframe}.feather"


def inspect_feather(
    path: Path,
    *,
    pair: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("pandas is required by replay data validation") from exc

    if timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    if not path.is_file():
        raise RuntimeError(f"historical data file missing: {path}")
    frame = pd.read_feather(path)
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise RuntimeError(f"{path.name} missing columns: {', '.join(missing)}")
    if frame.empty:
        raise RuntimeError(f"historical data file empty: {path}")

    dates = pd.to_datetime(frame["date"], utc=True, errors="raise")
    if dates.duplicated().any():
        raise RuntimeError(f"duplicate candles in {path.name}")
    diffs = dates.diff().dropna()
    delta = timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
    if (diffs <= timedelta(0)).any():
        raise RuntimeError(f"non-monotone candles in {path.name}")

    start = _utc(start)
    end = _utc(end)
    selected = frame.loc[(dates >= start) & (dates < end)].copy()
    selected_dates = dates[(dates >= start) & (dates < end)]
    if selected.empty:
        raise RuntimeError(f"no candles in requested interval for {path.name}")
    selected_diffs = selected_dates.diff().dropna()
    gap_count = int((selected_diffs > delta).sum())
    if gap_count:
        first_gap_idx = selected_diffs[selected_diffs > delta].index[0]
        raise RuntimeError(
            f"{path.name} has {gap_count} gap(s), first near row {int(first_gap_idx)}"
        )

    first = selected_dates.iloc[0].to_pydatetime()
    last = selected_dates.iloc[-1].to_pydatetime()
    if first > start + delta:
        raise RuntimeError(f"{path.name} starts too late: {first.isoformat()}")
    if last + delta < end - delta:
        raise RuntimeError(f"{path.name} ends too early: {last.isoformat()}")

    return {
        "pair": pair,
        "timeframe": timeframe,
        "path": str(path),
        "sha256": sha256_file(path),
        "file_bytes": path.stat().st_size,
        "rows_total": int(len(frame)),
        "rows_selected": int(len(selected)),
        "selected_first_open_utc": first.isoformat(),
        "selected_last_open_utc": last.isoformat(),
        "expected_interval_seconds": int(delta.total_seconds()),
        "gap_count": 0,
        "duplicate_count": 0,
        "timestamp_unit_note": "decoded by pandas/pyarrow; internal times normalized to UTC",
    }


def build_manifest(
    data_root: Path,
    *,
    start: datetime,
    end: datetime,
    pairs: Iterable[str] = PAIRS,
) -> dict[str, Any]:
    start = _utc(start)
    end = _utc(end)
    if end <= start:
        raise ValueError("end must be after start")
    pair_list = list(pairs)
    files: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for pair in pair_list:
        if pair not in PAIRS:
            raise ValueError(f"unsupported pair: {pair}")
        for timeframe in REQUIRED_TIMEFRAMES:
            key = (pair, timeframe)
            if key in seen:
                continue
            seen.add(key)
            files.append(
                inspect_feather(
                    feather_path(data_root, pair, timeframe),
                    pair=pair,
                    timeframe=timeframe,
                    start=start,
                    end=end,
                )
            )
    return {
        "schema": 1,
        "source": "public Binance candles via repository/Freqtrade data pipeline",
        "exchange": "binance",
        "trading_mode": "spot",
        "timezone": "UTC",
        "start_utc": start.isoformat(),
        "end_utc_exclusive": end.isoformat(),
        "pairs": pair_list,
        "timeframes": list(REQUIRED_TIMEFRAMES),
        "files": files,
    }
