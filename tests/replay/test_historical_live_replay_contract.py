from __future__ import annotations

import copy
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from historical_live_replay import (
    ACTIVE_DRYRUN_PAIRS,
    CONFIG,
    EXPECTED_V8_LF_SHA256,
    PAIRS,
    STRATEGY,
    _latest_common_end,
    _validate_contract,
    _validate_frozen_strategy,
)
from replay_data import REQUIRED_TIMEFRAMES, TIMEFRAME_SECONDS, feather_path


def _config() -> dict:
    return json.loads(Path(CONFIG).read_text(encoding="utf-8"))


def test_frozen_v8_replay_accepts_current_ten_pair_dryrun_bundle() -> None:
    # The replay itself stays frozen to its historical three pairs.  Only the
    # active runtime bundle it validates has grown to ten pairs.
    assert PAIRS == ("BTC/USDT", "ETH/USDT", "SOL/USDT")
    assert ACTIVE_DRYRUN_PAIRS == (
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "XRP/USDT",
        "BNB/USDT",
        "DOGE/USDT",
        "LINK/USDT",
        "TRX/USDT",
        "LTC/USDT",
        "BCH/USDT",
    )
    _validate_contract(_config())


def test_replay_loads_only_the_frozen_v8_baseline() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    expected_strategy = (
        repo_root / "research" / "baselines" / "V8" / "CompressionBreakout250.py"
    )
    active_strategy = (
        repo_root / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
    )

    assert expected_strategy.samefile(STRATEGY)
    assert not active_strategy.samefile(STRATEGY)
    assert _validate_frozen_strategy() == EXPECTED_V8_LF_SHA256


def test_replay_contract_rejects_an_unregistered_active_pair() -> None:
    config = copy.deepcopy(_config())
    config["exchange"]["pair_whitelist"].append("ADA/USDT")

    with pytest.raises(RuntimeError, match="replay safety contract mismatch"):
        _validate_contract(config)


def test_latest_common_end_uses_every_required_timeframe(tmp_path: Path) -> None:
    common_end = datetime(2026, 8, 22, 16, tzinfo=UTC)
    for pair in PAIRS:
        for timeframe in REQUIRED_TIMEFRAMES:
            path = feather_path(tmp_path, pair, timeframe)
            path.parent.mkdir(parents=True, exist_ok=True)
            candidate_end = common_end
            if (pair, timeframe) != ("BTC/USDT", "4h"):
                candidate_end += timedelta(hours=4)
            last_open = candidate_end - timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
            pd.DataFrame({"date": [last_open]}).to_feather(path)

    end = _latest_common_end(tmp_path)

    assert end.isoformat() == "2026-08-22T16:00:00+00:00"
