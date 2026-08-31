from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
MODULE_PATH = RESEARCH / "hixton_v6_sequence_analysis.py"
spec = importlib.util.spec_from_file_location("hixton_v6_sequence_analysis", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_fixed_routes_and_windows_are_preregistered() -> None:
    assert module.ROUTES == (
        "ROUTE_A_60_GIVEBACK_MACD_1H",
        "ROUTE_B_120_STRUCTURE_MACD_1H",
        "ROUTE_C_TWO_STAGE",
    )
    assert len(module.WINDOWS) == 4
    assert module.WINDOWS[0][1] == "2024-09-01T00:00:00Z"
    assert module.WINDOWS[-1][2] == "2026-09-01T00:00:00Z"


def test_thresholds_use_fixed_q20_q80() -> None:
    frame = pd.DataFrame(
        {
            "pair": ["BTC/USDT"] * 20,
            "checkpoint_minutes": [60] * 20,
            "giveback_fraction": list(range(20)),
            "macd_hist_atr": list(range(20)),
            "price_minus_vidya_atr": list(range(20)),
        }
    )
    threshold = module._build_thresholds(frame)[("BTC/USDT", 60)]
    assert threshold.giveback_q80 == frame["giveback_fraction"].quantile(0.80)
    assert threshold.macd_q20 == frame["macd_hist_atr"].quantile(0.20)
    assert threshold.price_vidya_q20 == frame["price_minus_vidya_atr"].quantile(0.20)


def test_two_stage_route_prefers_60_minute_trigger() -> None:
    thresholds = {
        ("BTC/USDT", 60): module.Thresholds(0.8, -0.1, -0.2),
        ("BTC/USDT", 120): module.Thresholds(0.8, -0.1, -0.2),
    }
    frame = pd.DataFrame(
        [
            {
                "pair": "BTC/USDT",
                "checkpoint_minutes": 60,
                "giveback_fraction": 0.9,
                "macd_hist_atr": -0.2,
                "price_minus_vidya_atr": -0.3,
                "trend_up_1h": 0,
                "hypothetical_exit_profit_abs": 1.0,
            },
            {
                "pair": "BTC/USDT",
                "checkpoint_minutes": 120,
                "giveback_fraction": 0.9,
                "macd_hist_atr": -0.2,
                "price_minus_vidya_atr": -0.3,
                "trend_up_1h": 0,
                "hypothetical_exit_profit_abs": 2.0,
            },
        ]
    )
    selected = module._choose_exit(module.ROUTE_C, frame, thresholds)
    assert selected is not None
    assert int(selected["checkpoint_minutes"]) == 60
    assert float(selected["hypothetical_exit_profit_abs"]) == 1.0


def test_fresh_oos_gate_requires_breadth_and_all_safety_caps() -> None:
    folds = pd.DataFrame(
        {
            "delta_pnl": [1.0, 1.0, -0.1, 1.0],
            "triggered_trades": [20, 20, 20, 20],
            "trigger_share": [0.1, 0.1, 0.1, 0.1],
            "dead_enrichment": [1.2, 1.2, 1.2, 1.2],
            "winner_damage_share": [0.05, 0.05, 0.05, 0.05],
            "fat_tail_damage_share": [0.05, 0.05, 0.05, 0.05],
            "fat_tail_trigger_rate": [0.1, 0.1, 0.1, 0.1],
        }
    )
    pairs = pd.DataFrame({"delta_pnl": [1, 1, 1, 1, 1, 1, -1, -1, -1, -1]})
    candidate, failures = module._route_gate(folds, pairs)
    assert candidate == 1
    assert failures == []

    pairs.loc[5, "delta_pnl"] = -1
    candidate, failures = module._route_gate(folds, pairs)
    assert candidate == 0
    assert "positive_coins<6" in failures
