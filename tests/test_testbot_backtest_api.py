from __future__ import annotations

import os

import pytest
from fastapi import HTTPException

from runtime import testbot_backtest_api as api


def test_backtest_contract_has_only_current_pairs_and_periods() -> None:
    assert api.ALLOWED_PAIRS == ("BTC/USDT", "ETH/USDT", "SOL/USDT")
    assert api.ALLOWED_YEARS == (1, 2, 3)
    assert api.STRATEGY_NAME == "CompressionBreakout250"


def test_invalid_pair_is_rejected_before_background_process() -> None:
    request = api.BacktestRequest(pair="DOGE/USDT", years=1)
    with pytest.raises(HTTPException) as exc:
        api.start_backtest(request)
    assert exc.value.status_code == 400


def test_subprocess_environment_drops_freqtrade_and_kill_switch_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FREQTRADE__API_SERVER__PASSWORD", "secret")
    monkeypatch.setenv("FREQTRADE__API_SERVER__JWT_SECRET_KEY", "jwt")
    monkeypatch.setenv("AI_TRADING_KILL_SWITCH_FILE", "C:/secret/stop")
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))

    cleaned = api._clean_subprocess_environment()

    assert "FREQTRADE__API_SERVER__PASSWORD" not in cleaned
    assert "FREQTRADE__API_SERVER__JWT_SECRET_KEY" not in cleaned
    assert "AI_TRADING_KILL_SWITCH_FILE" not in cleaned
    assert "PATH" in cleaned
    assert cleaned["PYTHONUTF8"] == "1"
