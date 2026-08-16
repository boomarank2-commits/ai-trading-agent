"""Download/update the public Binance candle set required by historical replay."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from replay_data import PAIRS, REQUIRED_TIMEFRAMES, build_manifest

RUNTIME = Path(__file__).resolve().parent
USERDIR = RUNTIME / "user_data"
CONFIG = USERDIR / "config.json"
PUBLIC_CONFIG = USERDIR / "config-public.json"
DATA_ROOT = USERDIR / "data" / "binance"
MANIFEST = USERDIR / "replay_data_manifest_latest.json"
WARMUP_DAYS = 75


def clean_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("FREQTRADE__")
        and key != "AI_TRADING_KILL_SWITCH_FILE"
    }
    env["PYTHONUTF8"] = "1"
    return env


def run_checked(args: list[str]) -> None:
    print("$", subprocess.list2cmdline(args))
    completed = subprocess.run(
        args,
        cwd=RUNTIME,
        env=clean_env(),
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"data command failed with code {completed.returncode}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, choices=[1, 3, 4, 6], default=6)
    parser.add_argument("--end", help="UTC ISO timestamp; default now")
    args = parser.parse_args(argv)
    end = (
        datetime.fromisoformat(args.end.replace("Z", "+00:00")).astimezone(UTC)
        if args.end
        else datetime.now(UTC)
    )
    start = end - timedelta(days=365 * args.years + WARMUP_DAYS)
    open_timerange = start.strftime("%Y%m%d") + "-"
    closed_timerange = f"{start:%Y%m%d}-{end:%Y%m%d}"

    for required in (CONFIG, PUBLIC_CONFIG):
        if not required.is_file():
            raise RuntimeError(f"required config missing: {required}")

    for pair in PAIRS:
        base = [
            sys.executable,
            "-m",
            "freqtrade",
            "download-data",
            "--config",
            str(CONFIG),
            "--config",
            str(PUBLIC_CONFIG),
            "--userdir",
            str(USERDIR),
            "--timeframes",
            *REQUIRED_TIMEFRAMES,
            "--pairs",
            pair,
            "--trading-mode",
            "spot",
            "--timerange",
            open_timerange,
        ]
        run_checked(base)
        prepend = [*base[:-2], "--timerange", closed_timerange, "--prepend"]
        run_checked(prepend)

    manifest = build_manifest(DATA_ROOT, start=start, end=end, pairs=PAIRS)
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Datenmanifest: {MANIFEST}")
    print(f"Validiert: {start.isoformat()} bis {end.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
