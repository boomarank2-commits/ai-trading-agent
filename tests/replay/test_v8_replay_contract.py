from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
V8_BASELINE = REPO_ROOT / "research" / "baselines" / "V8" / "CompressionBreakout250.py"
LOCKED = REPO_ROOT / "runtime" / "locked_freqtrade.py"

EXPECTED_V8_LF_SHA = "9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280"
EXPECTED_V10_LF_SHA = "698fa520249bcb0b100fc172d2827735a4fbe9a22d01a9e484a53253ff18673c"


def _lf_sha(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def test_v8_reference_is_preserved_while_v10_is_active() -> None:
    assert _lf_sha(V8_BASELINE) == EXPECTED_V8_LF_SHA
    assert _lf_sha(STRATEGY) == EXPECTED_V10_LF_SHA


def test_v10_has_no_cross_pair_btc_regime_dependency() -> None:
    text = STRATEGY.read_text(encoding="utf-8")
    assert 'STRATEGY_VERSION = "V10"' in text
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text
    assert "btc_close_4h" not in text
    assert '"BTC/USDT": {' in text
    assert '"ETH/USDT": {' in text
    assert '"SOL/USDT": {' in text
    assert '"only_per_pair": True' in text


def test_replay_observability_is_installed_outside_strategy_source() -> None:
    text = LOCKED.read_text(encoding="utf-8")
    assert "install_paper_strategy_telemetry" in text
    assert "authorized_sha" in text
    assert "paper_decision_telemetry" in text
