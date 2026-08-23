from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException

# Importing the active adapter deliberately binds the mature locked API to the
# current ten-pair paper universe before the tests exercise it.
from runtime import ten_pair_backtest_api as adapter
from runtime import testbot_backtest_api as api

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "runtime"
STRATEGY = RUNTIME / "user_data" / "strategies" / "CompressionBreakout250.py"
UI_SCRIPT = RUNTIME / "ui" / "testbot-backtest.js"
TEN_PAIRS = (
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
)


def test_backtest_contract_is_bound_to_active_ten_pairs_and_all_three_periods() -> None:
    assert adapter.TEN_PAIR_UNIVERSE == TEN_PAIRS
    assert api.ALLOWED_PAIRS == TEN_PAIRS
    assert (*TEN_PAIRS, "PORTFOLIO") == api.ALLOWED_TARGETS
    assert api._pairs_for_target("PORTFOLIO") == TEN_PAIRS
    assert api._pairs_for_target("LINK/USDT") == ("LINK/USDT",)
    assert api.ALLOWED_YEARS == (1, 2, 3)
    assert api.STRATEGY_NAME == "CompressionBreakout250"
    assert api.REQUIRED_TIMEFRAMES == ("15m", "1m", "1h", "4h")
    assert api.BACKTEST_WARMUP_DAYS >= 70


def test_pair_backtests_remain_pair_local_without_cross_pair_market_context() -> None:
    for pair in TEN_PAIRS:
        assert api._btc_context_pair(pair) is None
    source = (RUNTIME / "testbot_backtest_api.py").read_text(encoding="utf-8")
    assert "context_args" not in source
    assert '"cross_pair_context": False' in source


def test_trade_breakdown_attributes_profit_by_entry_or_exit_label() -> None:
    trades = [
        {"enter_tag": "champion", "profit_abs": 5.0},
        {"enter_tag": "reclaim", "profit_abs": -1.5},
        {"enter_tag": "reclaim", "profit_abs": 2.0},
    ]
    assert api._trade_breakdown(trades, key="enter_tag", fallback="missing") == [
        {"label": "reclaim", "trades": 2, "wins": 1, "profit_usdt": 0.5},
        {"label": "champion", "trades": 1, "wins": 1, "profit_usdt": 5.0},
    ]


def test_backtest_ui_runs_ten_independent_250_wallet_tests_for_selected_period() -> None:
    source = UI_SCRIPT.read_text(encoding="utf-8")
    for pair in TEN_PAIRS:
        assert pair in source
    assert "Alle 10 nacheinander" in source
    assert "eigenen 250-USDT-Testwallet" in source
    assert "kein gemeinsames 2.500-USDT-Portfolio" in source
    assert "const years = Number(yearsSelect.value);" in source
    assert "PAIRS.map(([pair]) => ({ pair, years }))" in source
    assert 'value="1"' in source
    assert 'value="2"' in source
    assert 'value="3"' in source
    assert 'value="PORTFOLIO"' not in source
    assert "Doppeltest übersprungen" in source
    assert "error.isDuplicate" in source


def test_internal_portfolio_target_is_not_exposed_in_normal_ui() -> None:
    source = UI_SCRIPT.read_text(encoding="utf-8")
    assert "PORTFOLIO" not in source
    assert "PORTFOLIO" in api.ALLOWED_TARGETS
    assert "shared 250-USDT 3x80 system backtest" in Path(
        adapter.__file__
    ).read_text(encoding="utf-8")


def test_invalid_pair_is_rejected_before_background_process() -> None:
    request = api.BacktestRequest(pair="ADA/USDT", years=1)
    with pytest.raises(HTTPException) as exc:
        api.start_backtest(request)
    assert exc.value.status_code == 400


def test_each_single_pair_target_resolves_to_only_that_pair() -> None:
    for pair in TEN_PAIRS:
        assert api._pairs_for_target(pair) == (pair,)


def test_identical_registered_test_is_blocked_before_new_run_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = tmp_path / "existing-run"
    existing.mkdir()
    payload = {
        "strategy": {
            api.STRATEGY_NAME: {
                "strategy_name": api.STRATEGY_NAME,
                "pairlist": ["BTC/USDT"],
                "backtest_start": "2025-08-23 00:00:00",
                "backtest_end": "2026-08-23 00:00:00",
                "backtest_days": 365,
                "starting_balance": 250,
                "final_balance": 251,
                "profit_total_abs": 1,
                "total_trades": 1,
                "trades": [],
            }
        }
    }
    with zipfile.ZipFile(existing / "result.zip", "w") as archive:
        archive.writestr("result.json", json.dumps(payload))
        archive.writestr(f"result_{api.STRATEGY_NAME}.py", api._STRATEGY.read_bytes())
        archive.writestr("result_config.json", api._CONFIG.read_bytes())
    monkeypatch.setattr(api, "_RESULTS_ROOT", tmp_path)

    before = sorted(path.name for path in tmp_path.iterdir())
    with pytest.raises(HTTPException, match="Doppeltest blockiert") as exc:
        api.start_backtest(api.BacktestRequest(pair="BTC/USDT", years=1))
    assert exc.value.status_code == 409
    assert sorted(path.name for path in tmp_path.iterdir()) == before


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
    assert cleaned["PYTHONUTF8"] == "1"
    assert cleaned["PYTHONDONTWRITEBYTECODE"] == "1"


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
