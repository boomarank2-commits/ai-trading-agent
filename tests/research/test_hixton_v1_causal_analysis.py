from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "research" / "hixton_v1_causal_analysis.py"
spec = importlib.util.spec_from_file_location("hixton_v1_causal_analysis", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_parse_enter_tag() -> None:
    parsed = module.parse_enter_tag("v1d|x=0.25|r=51.2|t1=1|t4=0|bad=9")
    assert parsed["breakout_excess_atr"] == 0.25
    assert parsed["rsi14"] == 51.2
    assert parsed["trend_up_1h"] == 1.0
    assert parsed["trend_up_4h"] == 0.0
    assert math.isnan(parsed["adx14"])


def test_exact_fee_break_even_threshold() -> None:
    threshold = module.break_even_mfe_ratio(0.002, 0.002)
    assert math.isclose(threshold, (1.002 / 0.998) - 1.0, rel_tol=0, abs_tol=1e-15)
    assert 0.004 < threshold < 0.00402


def test_profit_factor() -> None:
    rows = [{"profit_abs": 3.0}, {"profit_abs": -1.0}, {"profit_abs": -1.0}]
    assert module.profit_factor(rows) == 1.5


def test_chronological_split_is_60_20_20() -> None:
    rows = [{"open_timestamp": i} for i in range(10)]
    mapping = module.chronological_segments(rows)
    assert [mapping[id(row)] for row in rows] == [
        "discovery", "discovery", "discovery", "discovery", "discovery", "discovery",
        "validation", "validation", "holdout", "holdout",
    ]
