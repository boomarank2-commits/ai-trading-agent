from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
STRATEGY_PATH = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
CONFIG_PATH = ROOT / "runtime" / "user_data" / "config.json"


def _load_strategy_module():
    spec = importlib.util.spec_from_file_location("hixton_runtime_smoke", STRATEGY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pine_rma_seed_and_recursion() -> None:
    module = _load_strategy_module()
    source = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = module._pine_rma(source, 3)
    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert result.iloc[2] == 2.0
    assert math.isclose(result.iloc[3], 2.0 / 3.0 + 8.0 / 3.0, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(result.iloc[4], (1.0 / 3.0) * 5.0 + (2.0 / 3.0) * result.iloc[3], rel_tol=0, abs_tol=1e-12)


def test_pine_sma_uses_latest_non_na_values() -> None:
    module = _load_strategy_module()
    source = pd.Series([1.0, np.nan, 2.0, 3.0, 4.0])
    result = module._pine_sma_ignore_na(source, 3)
    assert result.iloc[:3].isna().all()
    assert result.iloc[3] == 2.0
    assert result.iloc[4] == 3.0


def test_hixton_indicator_runs_causally_on_synthetic_ohlcv() -> None:
    module = _load_strategy_module()
    rows = 700
    dates = pd.date_range("2026-01-01", periods=rows, freq="15min", tz="UTC")
    # Quiet start, strong rise, then strong fall.  This is deliberately simple:
    # it only proves the translated indicator can create both state transitions
    # without future data or pair-specific helpers.
    close = np.concatenate(
        [
            np.linspace(100.0, 102.0, 300),
            np.linspace(102.0, 180.0, 180),
            np.linspace(180.0, 80.0, 220),
        ]
    )
    frame = pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(rows, 100.0),
        }
    )
    result = module._hixton_state(frame.copy())
    for column in (
        "hixton_vidya",
        "hixton_atr",
        "hixton_upper",
        "hixton_lower",
        "hixton_trend_up",
        "hixton_flip_up",
        "hixton_flip_down",
    ):
        assert column in result.columns
    assert result["hixton_atr"].iloc[250:].notna().all()
    assert not (result["hixton_flip_up"] & result["hixton_flip_down"]).any()
    assert result.loc[result["hixton_flip_up"], "hixton_trend_up"].all()
    assert (~result.loc[result["hixton_flip_down"], "hixton_trend_up"]).all()
    assert int(result["hixton_flip_up"].sum()) >= 1
    assert int(result["hixton_flip_down"].sum()) >= 1


def test_freqtrade_strategy_instantiates_with_clean_config() -> None:
    module = _load_strategy_module()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    strategy = module.CompressionBreakout250(config=config)
    assert strategy.timeframe == "15m"
    assert strategy.can_short is False
    assert strategy.position_adjustment_enable is False
    assert strategy.max_entry_position_adjustment == 0
    assert strategy.STRATEGY_VERSION == "HIXTON-V1"
    strategy.bot_start()
