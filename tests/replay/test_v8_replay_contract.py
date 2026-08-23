from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
V8_BASELINE = REPO_ROOT / "research" / "baselines" / "V8" / "CompressionBreakout250.py"
LOCKED = REPO_ROOT / "runtime" / "locked_freqtrade.py"

EXPECTED_V8_LF_SHA = "9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280"


def _lf_sha(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def test_v8_reference_is_preserved_while_v12_18_is_active() -> None:
    assert _lf_sha(V8_BASELINE) == EXPECTED_V8_LF_SHA
    assert STRATEGY.is_file()


def test_v12_18_is_pair_local_without_btc_regime_dependency() -> None:
    text = STRATEGY.read_text(encoding="utf-8")
    assert 'STRATEGY_VERSION = "V12.18"' in text
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text
    assert "btc_close_4h" not in text
    assert '"BTC/USDT": {' in text
    assert '"ETH/USDT": {' in text
    assert '"SOL/USDT": {' in text
    assert 'REGIME_TREND = "TREND/BREAKOUT"' in text
    assert 'REGIME_NO_TRADE = "NO_TRADE"' in text
    assert 'FAMILY_DONCHIAN = "DONCHIAN_TREND"' in text
    assert 'FAMILY_RECLAIM = "TREND_RECLAIM"' in text
    assert "FAST_DONCHIAN_TREND" not in text
    assert "ORB_RETEST" not in text
    assert "ICHIMOKU_TREND" not in text
    assert "BOLLINGER_MR" not in text
    assert 'champion_quality = dataframe["volume_ratio"] >= 1.00' in text
    assert '"method": "LowProfitPairs"' in text
    assert "use_custom_stoploss = True" in text
    assert "stoploss_from_open" in text
    assert '"only_per_pair": True' in text


def test_replay_observability_is_installed_outside_strategy_source() -> None:
    text = LOCKED.read_text(encoding="utf-8")
    assert "install_paper_strategy_telemetry" in text
    assert "authorized_sha" in text
    assert "paper_decision_telemetry" in text
