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


def _strategy(module):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["candle_type_def"] = "spot"
    return module.CompressionBreakout250(config=config)


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


def _route_frame(rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "volume": np.full(rows, 100.0),
            "hixton_flip_up": np.full(rows, True),
            "hixton_flip_down": np.full(rows, False),
            "close_1h": np.full(rows, 110.0),
            "hixton_vidya_1h": np.full(rows, 100.0),
            "hixton_vidya_rising_1h": np.full(rows, True),
            "hixton_flip_up_1h": [False, True, True][:rows],
            "hixton_flip_down_1h": [False, True, True][:rows],
            "hixton_trend_up_4h": np.full(rows, True),
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
    strategy = _strategy(module)
    result = strategy.populate_indicators_1h(_synthetic_frame(700, "1h"), {})
    assert "hixton_vidya_rising" in result.columns
    expected = result["hixton_vidya"] >= result["hixton_vidya"].shift(1)
    pd.testing.assert_series_equal(
        result["hixton_vidya_rising"],
        expected,
        check_names=False,
    )


def test_four_hour_informative_uses_actual_hixton_trend_state() -> None:
    module = _load_strategy_module()
    strategy = _strategy(module)
    result = strategy.populate_indicators_4h(_synthetic_frame(700, "4h"), {})
    assert "hixton_trend_up" in result.columns
    assert "hixton_flip_up" in result.columns
    assert "hixton_flip_down" in result.columns
    assert "hixton_vidya_rising" not in result.columns


def test_forward_filled_informative_event_fires_once() -> None:
    module = _load_strategy_module()
    series = pd.Series([False, True, True, True, False, False, True, True])
    event = module._first_forward_filled_true(series)
    assert event.tolist() == [False, True, False, False, False, False, True, False]


def test_route_a_controls_require_one_hour_guard_but_no_four_hour_gate() -> None:
    module = _load_strategy_module()
    strategy = _strategy(module)
    frame = _route_frame(3)
    frame["hixton_trend_up_4h"] = False
    for pair in ("ETH/USDT", "XRP/USDT", "DOGE/USDT", "TRX/USDT"):
        result = strategy.populate_entry_trend(frame.copy(), {"pair": pair})
        assert result["enter_long"].fillna(0).astype(int).tolist() == [1, 1, 1]
        assert set(result["enter_tag"].dropna()) == {"hixton_15m_flip_up_1h_guard"}

    frame["hixton_vidya_rising_1h"] = False
    blocked = strategy.populate_entry_trend(frame.copy(), {"pair": "ETH/USDT"})
    assert "enter_long" not in blocked.columns or not blocked["enter_long"].fillna(0).any()


def test_route_b_btc_sol_link_bnb_require_four_hour_hixton_trend() -> None:
    module = _load_strategy_module()
    strategy = _strategy(module)
    for pair in ("BTC/USDT", "SOL/USDT", "LINK/USDT", "BNB/USDT"):
        blocked_frame = _route_frame(3)
        blocked_frame["hixton_trend_up_4h"] = False
        blocked = strategy.populate_entry_trend(blocked_frame, {"pair": pair})
        assert "enter_long" not in blocked.columns or not blocked["enter_long"].fillna(0).any()

        allowed_frame = _route_frame(3)
        allowed = strategy.populate_entry_trend(allowed_frame, {"pair": pair})
        assert allowed["enter_long"].fillna(0).astype(int).tolist() == [1, 1, 1]
        assert set(allowed["enter_tag"].dropna()) == {"hixton_15m_flip_up_1h_4h_trend"}


def test_route_b_uses_trend_state_not_four_hour_vidya_slope_proxy() -> None:
    module = _load_strategy_module()
    strategy = _strategy(module)
    frame = _route_frame(3)
    frame["close_4h"] = 80.0
    frame["hixton_vidya_4h"] = 100.0
    frame["hixton_vidya_rising_4h"] = False
    frame["hixton_trend_up_4h"] = True
    sol = strategy.populate_entry_trend(frame, {"pair": "SOL/USDT"})
    assert sol["enter_long"].fillna(0).astype(int).tolist() == [1, 1, 1]


def test_ltc_bch_use_one_shot_one_hour_route_and_one_hour_exit() -> None:
    module = _load_strategy_module()
    strategy = _strategy(module)
    for pair in ("LTC/USDT", "BCH/USDT"):
        frame = _route_frame(3)
        result = strategy.populate_entry_trend(frame.copy(), {"pair": pair})
        assert result["enter_long"].fillna(0).astype(int).tolist() == [0, 1, 0]
        assert result.loc[result["enter_long"].fillna(0).astype(bool), "enter_tag"].iloc[0] == "hixton_1h_flip_up_4h_trend"

        blocked_frame = _route_frame(3)
        blocked_frame["hixton_trend_up_4h"] = False
        blocked = strategy.populate_entry_trend(blocked_frame, {"pair": pair})
        assert "enter_long" not in blocked.columns or not blocked["enter_long"].fillna(0).any()

        exit_frame = frame.copy()
        exit_frame["hixton_flip_down"] = False
        exited = strategy.populate_exit_trend(exit_frame, {"pair": pair})
        assert exited["exit_long"].fillna(0).astype(int).tolist() == [0, 1, 0]
        assert exited.loc[exited["exit_long"].fillna(0).astype(bool), "exit_tag"].iloc[0] == "hixton_1h_flip_down"


def test_freqtrade_strategy_instantiates_with_clean_config() -> None:
    module = _load_strategy_module()
    strategy = _strategy(module)
    assert strategy.timeframe == "15m"
    assert strategy.can_short is False
    assert strategy.position_adjustment_enable is False
    assert strategy.max_entry_position_adjustment == 0
    assert strategy.use_custom_stoploss is False
    assert strategy.STRATEGY_VERSION == "HIXTON-V5B"
    strategy.bot_start()