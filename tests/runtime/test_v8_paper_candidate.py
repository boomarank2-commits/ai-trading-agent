from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
USER_DATA = REPO_ROOT / "runtime" / "user_data"
STRATEGY = USER_DATA / "strategies" / "CompressionBreakout250.py"
V8_BASELINE = REPO_ROOT / "research" / "baselines" / "V8" / "CompressionBreakout250.py"
CONFIG = USER_DATA / "config.json"
EXPECTED_V8_LF_SHA256 = "9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280"
TEN_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "DOGE/USDT",
    "LINK/USDT",
    "TRX/USDT",
    "LTC/USDT",
    "BCH/USDT",
]


def _lf_sha256(path: Path) -> str:
    source = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(source).hexdigest()


def test_v8_baseline_is_preserved_and_v12_22_is_active_paper_candidate() -> None:
    assert _lf_sha256(V8_BASELINE) == EXPECTED_V8_LF_SHA256

    text = STRATEGY.read_text(encoding="utf-8")
    assert 'STRATEGY_VERSION = "V12.31"' in text
    assert "PAIR_PROFILES" in text
    assert "RECLAIM_PROFILES" in text
    assert 'REGIME_TREND = "TREND/BREAKOUT"' in text
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
    assert "v12_17_" in text
    assert "def adjust_trade_position(" in text
    assert "selective_pyramid_chunk" in text
    assert "current_profit <= 0.0" in text
    assert '"only_per_pair": True' in text


def test_paper_configuration_keeps_250_80_three_chunk_contract_on_ten_pairs() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["dry_run"] is True
    assert config["dry_run_wallet"] == 250
    assert config["available_capital"] == 250
    assert config["stake_amount"] == 80
    assert config["max_open_trades"] == 3
    assert config["position_adjustment_enable"] is True
    assert config["max_entry_position_adjustment"] == 2
    assert config["minimal_roi"] == {"0": 0.50}
    assert config["stoploss"] == -0.055
    assert config["trailing_stop"] is False
    assert config["trading_mode"] == "spot"
    assert config["exchange"]["pair_whitelist"] == TEN_PAIRS
    assert config["db_url"] == "sqlite:///user_data/tradesv8.dryrun.sqlite"


def test_existing_paper_database_is_isolated_from_legacy_v2_v3_history() -> None:
    launcher = (REPO_ROOT / "runtime" / "scripts" / "start-testbot-24x7.ps1").read_text(
        encoding="utf-8"
    )
    validator = (REPO_ROOT / "runtime" / "validate_dryrun_config.py").read_text(
        encoding="utf-8"
    )
    assert "tradesv8.dryrun.sqlite" in launcher
    assert "tradesv8.dryrun.sqlite" in validator
    assert "tradesv3.dryrun.sqlite" not in launcher
    assert "tradesv3.dryrun.sqlite" not in validator
