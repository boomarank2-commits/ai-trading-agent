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
MODULE_PATH = RESEARCH / "hixton_v1_dead_trend_analysis.py"
spec = importlib.util.spec_from_file_location("hixton_v1_dead_trend_analysis", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_hypothetical_exit_pnl_includes_both_fees() -> None:
    trade = {
        "amount": 1.0,
        "open_rate": 100.0,
        "fee_open": 0.002,
        "fee_close": 0.002,
    }
    result = module.hypothetical_exit_pnl(trade, 101.0)
    assert math.isclose(result, 1.0 - 0.2 - 0.202, rel_tol=0, abs_tol=1e-12)


def test_activation_time_is_first_causal_minute() -> None:
    frame = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            "2026-01-01T00:02:00Z",
        ], utc=True),
        "high": [100.1, 100.3, 100.5],
    })
    found = module.first_activation_time(frame, 100.0, 0.004)
    assert found == pd.Timestamp("2026-01-01T00:02:00Z")


def test_exit_feature_directions_are_preregistered() -> None:
    assert module.EXIT_FEATURES["giveback_fraction"] == "high20"
    assert module.EXIT_FEATURES["price_minus_vidya_atr"] == "low20"
    assert module.EXIT_FEATURES["trend_up_1h"] == "equals0"
    assert module.CHECKPOINT_MINUTES == (60, 120)
