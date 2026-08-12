"""Copy only pre-holdout OHLCV into an isolated research workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
MAX_FILES = 16


def stage(source: Path, destination: Path, cutoff_utc: str) -> dict[str, object]:
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=True)
    cutoff = pd.Timestamp(cutoff_utc)
    if cutoff.tzinfo is None or str(cutoff.tzinfo) != "UTC":
        raise ValueError("holdout cutoff must include the UTC timezone")
    files = sorted(source.glob("*.feather"))
    if not files or len(files) > MAX_FILES:
        raise ValueError(f"expected 1..{MAX_FILES} Feather market-data files")
    if any(path.is_symlink() or not path.is_file() for path in files):
        raise ValueError("market-data inputs must be regular files")
    if any(destination.iterdir()):
        raise ValueError("staging market-data destination must be empty")

    summaries: list[dict[str, object]] = []
    for path in files:
        frame = pd.read_feather(path)
        if list(frame.columns) != REQUIRED_COLUMNS:
            raise ValueError(f"unexpected OHLCV columns in {path.name}")
        dates = pd.to_datetime(frame["date"], utc=True)
        training = frame.loc[dates < cutoff].copy()
        if training.empty:
            raise ValueError(f"no pre-holdout candles in {path.name}")
        training_dates = pd.to_datetime(training["date"], utc=True)
        if bool((training_dates >= cutoff).any()):
            raise ValueError(f"holdout candle leaked into staged file {path.name}")
        output = destination / path.name
        training.reset_index(drop=True).to_feather(output)
        summaries.append(
            {
                "file": path.name,
                "candles": len(training),
                "first_utc": training_dates.iloc[0].isoformat(),
                "last_utc": training_dates.iloc[-1].isoformat(),
            }
        )
    return {
        "ok": True,
        "holdout_cutoff_utc": cutoff.isoformat(),
        "files": summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--holdout-cutoff-utc", required=True)
    args = parser.parse_args()
    result = stage(args.source, args.destination, args.holdout_cutoff_utc)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
