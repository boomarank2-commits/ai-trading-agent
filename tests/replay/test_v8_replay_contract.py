from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
V8_BASELINE = REPO_ROOT / "research" / "baselines" / "V8" / "CompressionBreakout250.py"
LOCKED = REPO_ROOT / "runtime" / "locked_freqtrade.py"

EXPECTED_V8_LF_SHA = "9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280"
EXPECTED_V9_LF_SHA = "b9ab4f995510b9d847e2b5c9793bb8072bd3d6a7f9c623eb8f283c85fad2a0e1"


def _lf_sha(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def test_v8_reference_is_preserved_while_v9_is_active() -> None:
    assert _lf_sha(V8_BASELINE) == EXPECTED_V8_LF_SHA
    assert _lf_sha(STRATEGY) == EXPECTED_V9_LF_SHA


def test_v9_has_btc_only_volume_ratio_entry_gate() -> None:
    text = STRATEGY.read_text(encoding="utf-8")
    execution_match = re.search(
        r"execution\s*=\s*\((.*?)\n\s*\)\n\s*enter_tag", text, re.DOTALL
    )
    assert execution_match is not None
    execution = execution_match.group(1)
    assert "volume_quality" in execution
    assert 'if pair == "BTC/USDT":' in text
    assert 'dataframe["volume_ratio"] >= self.BTC_VOLUME_RATIO_MIN' in text
    assert "BTC_VOLUME_RATIO_MIN = 1.00" in text


def test_replay_observability_is_installed_outside_strategy_source() -> None:
    text = LOCKED.read_text(encoding="utf-8")
    assert "install_paper_strategy_telemetry" in text
    assert "authorized_sha" in text
    assert "paper_decision_telemetry" in text
