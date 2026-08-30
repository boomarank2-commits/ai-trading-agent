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


def _synthetic_frame(rows: int = 900) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="15min", tz="UTC")
    close = np.concatenate(
        [
            np.linspace(100.0, 102.0, 300),
            np.linspace(102.0, 180.0, 180),
            np.linspace(180.0, 80.0, 220),
            np.linspace(80.0, 150.0, 200),
        ]
    )[:rows]
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
    result = module._hixton_state(_synthetic_frame().copy())
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


def test_diagnostic_state_adds_measurement_columns_without_changing_flips() -> None:
    module = _load_strategy_module()
    frame = _synthetic_frame()
    baseline = module._hixton_state(frame.copy())
    diagnostic = module._diagnostic_state(frame.copy())
    assert baseline["hixton_flip_up"].equals(diagnostic["hixton_flip_up"])
    assert baseline["hixton_flip_down"].equals(diagnostic["hixton_flip_down"])
    for column in (
        "diag_breakout_excess_atr",
        "diag_price_minus_vidya_atr",
        "diag_atr_vs_median_96",
        "diag_volume_ratio_20",
        "diag_rsi14",
        "diag_adx14",
        "diag_macd_hist_atr",
        "diag_prev_phase_bars",
        "diag_prev_phase_range_atr",
        "diag_red_rebound_atr",
        "diag_prev_green_range_atr",
    ):
        assert column in diagnostic.columns


def test_diagnostic_enter_tag_is_compact_and_decodable() -> None:
    module = _load_strategy_module()
    row = pd.Series(
        {
            "diag_breakout_excess_atr": 0.12,
            "diag_price_minus_vidya_atr": 2.12,
            "diag_candle_body_atr": 0.4,
            "diag_candle_range_atr": 0.8,
            "diag_atr_vs_median_96": 1.1,
            "diag_volume_ratio_20": 1.5,
            "diag_rsi14": 61.2,
            "diag_adx14": 24.5,
            "diag_macd_hist_atr": 0.08,
            "diag_vidya_slope_1_atr": 0.03,
            "diag_vidya_slope_4_atr": 0.08,
            "diag_prev_phase_bars": 17,
            "diag_prev_phase_range_atr": 3.1,
            "diag_prev_phase_net_atr": -0.7,
            "diag_red_rebound_atr": 2.6,
            "diag_prev_green_range_atr": 4.2,
            "hixton_trend_up_1h": True,
            "diag_rsi14_1h": 57.0,
            "diag_adx14_1h": 22.0,
            "diag_vidya_slope_1_atr_1h": 0.02,
            "hixton_trend_up_4h": False,
            "diag_rsi14_4h": 49.0,
            "diag_adx14_4h": 18.0,
            "diag_vidya_slope_1_atr_4h": -0.01,
        }
    )
    tag = module._diagnostic_enter_tag(row)
    assert tag.startswith("v1d|")
    assert "rb=17" in tag
    assert "t1=1" in tag
    assert "t4=0" in tag
    assert len(tag) <= 250


def test_freqtrade_strategy_instantiates_with_clean_config() -> None:
    module = _load_strategy_module()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["candle_type_def"] = "spot"
    strategy = module.CompressionBreakout250(config=config)
    assert strategy.timeframe == "15m"
    assert strategy.can_short is False
    assert strategy.position_adjustment_enable is False
    assert strategy.max_entry_position_adjustment == 0
    assert strategy.STRATEGY_VERSION == "HIXTON-V1-DIAG"
    strategy.bot_start()
