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
UI_SCRIPT = RUNTIME / "ui" / "testbot-backtest.js"


def test_backtest_contract_has_only_current_pairs_and_periods() -> None:
    assert api.ALLOWED_PAIRS == ("BTC/USDT", "ETH/USDT", "SOL/USDT")
    assert api.ALLOWED_YEARS == (1, 2, 3)
    assert api.STRATEGY_NAME == "CompressionBreakout250"
    assert api.REQUIRED_TIMEFRAMES == ("15m", "1m", "1h", "4h")
    assert api.BACKTEST_WARMUP_DAYS >= 70


def test_v12_9_backtest_downloads_no_cross_pair_market_context() -> None:
    assert api._btc_context_pair("BTC/USDT") is None
    assert api._btc_context_pair("ETH/USDT") is None
    assert api._btc_context_pair("SOL/USDT") is None

    source = (RUNTIME / "testbot_backtest_api.py").read_text(encoding="utf-8")
    assert "context_args" not in source
    assert "context_prepend_args" not in source
    assert '"cross_pair_context": False' in source
    assert '"adaptive_router": False' in source


def test_trade_breakdown_attributes_profit_by_entry_or_exit_label() -> None:
    trades = [
        {"enter_tag": "champion", "profit_abs": 5.0},
        {"enter_tag": "reclaim", "profit_abs": -1.5},
        {"enter_tag": "reclaim", "profit_abs": 2.0},
    ]

    rows = api._trade_breakdown(trades, key="enter_tag", fallback="missing")

    assert rows == [
        {"label": "reclaim", "trades": 2, "wins": 1, "profit_usdt": 0.5},
        {"label": "champion", "trades": 1, "wins": 1, "profit_usdt": 5.0},
    ]


def test_backtest_ui_has_exact_sequential_six_run_matrix() -> None:
    source = UI_SCRIPT.read_text(encoding="utf-8")
    batch_block = source.split("const BATCH_CASES = [", maxsplit=1)[1].split(
        "];", maxsplit=1
    )[0]

    assert 'id="tb-start-all"' in source
    assert "async function startAllBacktests()" in source
    assert "await startOneBacktest(test.pair, test.years)" in source
    assert batch_block.count('pair: "BTC/USDT"') == 2
    assert batch_block.count('pair: "ETH/USDT"') == 2
    assert batch_block.count('pair: "SOL/USDT"') == 2
    assert batch_block.count("years: 3") == 3
    assert batch_block.count("years: 1") == 3
    assert "years: 2" not in batch_block


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
