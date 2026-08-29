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


def _synthetic_frame(rows: int, freq: str) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq=freq, tz="UTC")
    first = rows // 3
    second = rows // 3
    third = rows - first - second
    close = np.concatenate(
        [
            np.linspace(100.0, 102.0, first),
            np.linspace(102.0, 180.0, second),
            np.linspace(180.0, 80.0, third),
        ]
    )
    return pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(rows, 100.0),
        }
    )


def test_pine_rma_seed_and_recursion() -> None:
    module = _load_strategy_module()
    source = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = module._pine_rma(source, 3)
    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert result.iloc[2] == 2.0
    assert math.isclose(result.iloc[3], 8.0 / 3.0, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(
        result.iloc[4],
        (1.0 / 3.0) * 5.0 + (2.0 / 3.0) * result.iloc[3],
        rel_tol=0,
        abs_tol=1e-12,
    )


def test_pine_sma_uses_latest_non_na_values() -> None:
    module = _load_strategy_module()
    source = pd.Series([1.0, np.nan, 2.0, 3.0, 4.0])
    result = module._pine_sma_ignore_na(source, 3)
    assert result.iloc[:3].isna().all()
    assert result.iloc[3] == 2.0
    assert result.iloc[4] == 3.0


def test_hixton_indicator_runs_causally_on_synthetic_ohlcv() -> None:
    module = _load_strategy_module()
    result = module._hixton_state(_synthetic_frame(700, "15min"))
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
    assert "hixton_midline_cross_down" not in result.columns
    assert result["hixton_atr"].iloc[250:].notna().all()
    assert not (result["hixton_flip_up"] & result["hixton_flip_down"]).any()
    assert result.loc[result["hixton_flip_up"], "hixton_trend_up"].all()
    assert (~result.loc[result["hixton_flip_down"], "hixton_trend_up"]).all()
    assert int(result["hixton_flip_up"].sum()) >= 1
    assert int(result["hixton_flip_down"].sum()) >= 1


def test_native_hourly_guard_computes_slope_before_merge() -> None:
    module = _load_strategy_module()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["candle_type_def"] = "spot"
    strategy = module.CompressionBreakout250(config=config)
    result = strategy.populate_indicators_1h(_synthetic_frame(700, "1h"), {})
    assert "hixton_vidya_rising" in result.columns
    expected = result["hixton_vidya"] >= result["hixton_vidya"].shift(1)
    pd.testing.assert_series_equal(
        result["hixton_vidya_rising"],
        expected,
        check_names=False,
    )


def test_freqtrade_strategy_instantiates_with_clean_config() -> None:
    module = _load_strategy_module()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["candle_type_def"] = "spot"
    strategy = module.CompressionBreakout250(config=config)
    assert strategy.timeframe == "15m"
    assert strategy.can_short is False
    assert strategy.position_adjustment_enable is False
    assert strategy.max_entry_position_adjustment == 0
    assert strategy.STRATEGY_VERSION == "HIXTON-V3A"
    strategy.bot_start()