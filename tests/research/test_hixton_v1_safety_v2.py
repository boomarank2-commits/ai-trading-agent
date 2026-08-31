from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))


def _load(name: str, filename: str):
    path = RESEARCH / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


causal_v2 = _load("hixton_v1_causal_analysis_v2", "hixton_v1_causal_analysis_v2.py")
dead_v2 = _load("hixton_v1_dead_trend_analysis_v2", "hixton_v1_dead_trend_analysis_v2.py")


def test_activation_requires_completed_minute_close_not_wick() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:01:00Z",
                    "2026-01-01T00:02:00Z",
                ],
                utc=True,
            ),
            "high": [100.5, 100.6, 100.7],
            "close": [100.1, 100.3, 100.5],
        }
    )
    found = dead_v2.first_confirmed_activation_time(frame, 100.0, 0.004)
    assert found == pd.Timestamp("2026-01-01T00:03:00Z")


def test_segment_fat_tail_stats_protect_profit_mass_not_only_count() -> None:
    universe = [
        {"profit_abs": 1.0},
        {"profit_abs": 2.0},
        {"profit_abs": 3.0},
        {"profit_abs": 4.0},
        {"profit_abs": 100.0},
        {"profit_abs": -1.0},
    ]
    removed = [universe[4]]
    stats = causal_v2._segment_fat_tail_stats(universe, removed)
    assert stats["fat_tail_removed_count"] == 1.0
    assert math.isclose(stats["fat_tail_profit_removed_share"], 1.0)


def test_safety_v2_checkpoints_remain_preregistered() -> None:
    assert dead_v2.CHECKPOINT_MINUTES == (60, 120)
    assert dead_v2.EXIT_FEATURES["giveback_fraction"] == "high20"
    assert dead_v2.EXIT_FEATURES["price_minus_vidya_atr"] == "low20"
