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
EXPECTED_V9_LF_SHA256 = "b9ab4f995510b9d847e2b5c9793bb8072bd3d6a7f9c623eb8f283c85fad2a0e1"


def _lf_sha256(path: Path) -> str:
    source = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(source).hexdigest()


def test_v8_baseline_is_preserved_and_v9_is_active_candidate() -> None:
    assert _lf_sha256(V8_BASELINE) == EXPECTED_V8_LF_SHA256
    assert _lf_sha256(STRATEGY) == EXPECTED_V9_LF_SHA256

    text = STRATEGY.read_text(encoding="utf-8")
    assert 'STRATEGY_VERSION = "V9"' in text
    assert "BTC_VOLUME_RATIO_MIN = 1.00" in text
    assert 'if pair == "BTC/USDT":' in text
    assert 'dataframe["volume_ratio"] >= self.BTC_VOLUME_RATIO_MIN' in text
    assert "failed_4h_breakout" in text
    assert "slow_trend_exit" in text


def test_paper_configuration_keeps_validated_execution_contract() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["dry_run"] is True
    assert config["dry_run_wallet"] == 250
    assert config["available_capital"] == 250
    assert config["stake_amount"] == 80
    assert config["max_open_trades"] == 3
    assert config["minimal_roi"] == {"0": 0.50}
    assert config["stoploss"] == -0.055
    assert config["trailing_stop"] is False
    assert config["trading_mode"] == "spot"
    assert config["exchange"]["pair_whitelist"] == [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
    ]
    assert config["db_url"] == "sqlite:///user_data/tradesv8.dryrun.sqlite"


def test_existing_paper_database_remains_isolated_from_legacy_v2_v3_history() -> None:
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
