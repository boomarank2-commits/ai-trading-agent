from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
LOCKED = REPO_ROOT / "runtime" / "locked_freqtrade.py"

EXPECTED_V8_LF_SHA = "9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280"


def test_frozen_v8_source_is_not_modified_by_replay_work() -> None:
    raw = STRATEGY.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_V8_LF_SHA


def test_v8_still_has_no_active_volume_ratio_entry_gate() -> None:
    text = STRATEGY.read_text(encoding="utf-8")
    execution_match = re.search(
        r"execution\s*=\s*\((.*?)\n\s*\)\n\s*dataframe\.loc", text, re.DOTALL
    )
    assert execution_match is not None
    execution = execution_match.group(1)
    assert 'dataframe["volume"] > 0' in execution
    assert 'dataframe["volume_ratio"]' not in execution


def test_replay_observability_is_installed_outside_strategy_source() -> None:
    text = LOCKED.read_text(encoding="utf-8")
    assert "install_paper_strategy_telemetry" in text
    assert "authorized_sha" in text
    assert "paper_decision_telemetry" in text
