from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

from runtime import testbot_backtest_api as api

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "runtime"
STRATEGY = RUNTIME / "user_data" / "strategies" / "CompressionBreakout250.py"


def test_backtest_contract_has_only_current_pairs_and_periods() -> None:
    assert api.ALLOWED_PAIRS == ("BTC/USDT", "ETH/USDT", "SOL/USDT")
    assert api.ALLOWED_YEARS == (1, 2, 3)
    assert api.STRATEGY_NAME == "CompressionBreakout250"
    assert api.REQUIRED_TIMEFRAMES == ("15m", "1m", "1h", "4h")
    assert api.BACKTEST_WARMUP_DAYS >= 70


def test_backtest_download_adds_btc_market_context_for_altcoins() -> None:
    assert api._download_pairs("BTC/USDT") == ("BTC/USDT",)
    assert api._download_pairs("ETH/USDT") == ("ETH/USDT", "BTC/USDT")
    assert api._download_pairs("SOL/USDT") == ("SOL/USDT", "BTC/USDT")


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


def _run_locked_entrypoint(script_name: str, command: str) -> subprocess.CompletedProcess[str]:
    digest = hashlib.sha256(STRATEGY.read_bytes()).hexdigest()
    return subprocess.run(
        [
            sys.executable,
            str(RUNTIME / script_name),
            "--strategy-source",
            str(STRATEGY),
            "--strategy-sha256",
            digest,
            "--strategy-class",
            "CompressionBreakout250",
            "--",
            command,
            "--help",
        ],
        cwd=str(RUNTIME),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_locked_paper_entrypoint_runs_directly_without_runtime_import_error() -> None:
    result = _run_locked_entrypoint("locked_freqtrade.py", "trade")
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "No module named 'runtime'" not in combined


def test_locked_backtest_entrypoint_runs_directly_without_runtime_import_error() -> None:
    result = _run_locked_entrypoint("locked_backtest_freqtrade.py", "backtesting")
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "No module named 'runtime'" not in combined
