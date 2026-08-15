from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
USER_DATA = REPO_ROOT / "runtime" / "user_data"
STRATEGY = USER_DATA / "strategies" / "CompressionBreakout250.py"
CONFIG = USER_DATA / "config.json"
EXPECTED_V8_LF_SHA256 = "9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280"


def test_exact_validated_v8_strategy_source_is_promoted() -> None:
    # Git normalizes repository text to LF, while a Windows checkout may expose
    # CRLF depending on core.autocrlf. Fingerprint the normalized source so the
    # test locks strategy semantics rather than the checkout's newline policy.
    source = STRATEGY.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(source).hexdigest() == EXPECTED_V8_LF_SHA256
    text = source.decode("utf-8")
    assert "slow_20d_donchian_breakout" in text
    assert "failed_4h_breakout" in text
    assert "slow_trend_exit" in text


def test_v8_paper_configuration_keeps_validated_execution_contract() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["bot_name"] == "slow-donchian-v8-250-dryrun"
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


def test_v8_forward_database_is_isolated_from_legacy_paper_history() -> None:
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
