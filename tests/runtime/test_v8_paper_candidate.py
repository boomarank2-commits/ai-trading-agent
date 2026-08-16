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


def _lf_sha256(path: Path) -> str:
    source = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(source).hexdigest()


def test_v8_baseline_is_preserved_and_v11_is_active_candidate() -> None:
    assert _lf_sha256(V8_BASELINE) == EXPECTED_V8_LF_SHA256

    text = STRATEGY.read_text(encoding="utf-8")
    assert 'STRATEGY_VERSION = "V11"' in text
    assert "PAIR_PROFILES" in text
    assert 'REGIME_TREND = "TREND/BREAKOUT"' in text
    assert 'REGIME_RANGE = "RANGE/MEAN_REVERSION"' in text
    assert 'REGIME_NO_TRADE = "NO_TRADE"' in text
    assert 'FAMILY_ORB = "ORB_RETEST"' in text
    assert 'FAMILY_ICHIMOKU = "ICHIMOKU_TREND"' in text
    assert 'FAMILY_BOLLINGER = "BOLLINGER_MR"' in text
    assert "ROUNDTRIP_COST_STRESS" in text
    assert "v11_" in text
    assert "populate_indicators_btc_4h" not in text
    assert "btc_market_up" not in text
    assert '"only_per_pair": True' in text
    assert "_closed_profit_since(day_start_utc, pair)" in text


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
