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
    assert api.BACKTEST_WARMUP_DAYS >= 70
    assert api.STRATEGY_VERSION == "V12.22"


def test_market_data_is_updated_and_kept_in_the_repo_local_runtime_cache() -> None:
    assert api._DATA_ROOT == RUNTIME / "user_data" / "data" / "binance"
    assert api.REQUIRED_TIMEFRAMES == ("15m", "1m", "1h", "4h")
    source = Path(api.__file__).read_text(encoding="utf-8")
    adapter_source = Path(adapter.__file__).read_text(encoding="utf-8")
    assert '"download-data"' in source
    assert '"--prepend"' in source
    assert "_validate_candle_data" in source
    assert "_candle_path(pair, timeframe).unlink(missing_ok=True)" in adapter_source


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


def test_pair_breakdown_includes_entry_chunk_attribution() -> None:
    trades = [
        {
            "pair": "BTC/USDT",
            "profit_abs": 5.0,
            "orders": [
                {"ft_is_entry": True},
                {"ft_is_entry": True},
                {"ft_is_entry": False},
            ],
        },
        {"pair": "ETH/USDT", "profit_abs": -1.0, "orders": []},
    ]
    assert api._pair_breakdown(trades) == [
        {
            "pair": "BTC/USDT",
            "trades": 1,
            "wins": 1,
            "profit_usdt": 5.0,
            "entry_chunks": 2,
            "max_entries_per_trade": 2,
        },
        {
            "pair": "ETH/USDT",
            "trades": 1,
            "wins": 0,
            "profit_usdt": -1.0,
            "entry_chunks": 1,
            "max_entries_per_trade": 1,
        },
    ]


def test_backtest_ui_offers_selected_pair_and_one_click_ten_individual_runs() -> None:
    source = UI_SCRIPT.read_text(encoding="utf-8")
    for pair in TEN_PAIRS:
        assert pair in source
    assert "Alle 10 einzeln testen" in source
    assert 'id="tb-start-all"' not in source
    assert "startPortfolioBacktest" not in source
    assert "eigenen 250-USDT-Testwallet" in source
    assert "Jeder Coin beginnt mit eigenen 250 USDT" in source
    assert "const years = Number(yearsSelect.value);" in source
    assert 'fetch("/api/v1/testbot/backtest/batch/start"' in source
    assert 'fetch("/api/v1/testbot/backtest/batch/status"' in source
    assert "Plan, Fortschritt, Vorher/Nachher-Vergleich" in source
    assert "timing.market_data_seconds" in source
    assert "timing.simulation_seconds" in source
    assert "PAIRS.map(([pair]) => ({ pair, years }))" not in source
    assert 'startOneBacktest("PORTFOLIO", years)' not in source
    assert "runtime/user_data/data/binance" in source
    assert "ändert keine Parameter automatisch" in source
    assert "eigene, dokumentierte Parameter-Hypothese" in source
    assert 'const BODY_OPEN_CLASS = "testbot-backtest-open"' in source
    assert "body.${BODY_OPEN_CLASS} main { display: none !important; }" in source
    assert "document.body.classList.add(BODY_OPEN_CLASS)" in source
    assert "document.body.classList.remove(BODY_OPEN_CLASS)" in source
    assert "syncBacktestTop(view)" in source
    assert "Math.max(90" not in source
    assert 'value="1"' in source
    assert 'value="2"' in source
    assert 'value="3"' in source
    assert "Doppeltest übersprungen" in source
    assert "error.isDuplicate" in source


def test_batch_state_is_persisted_below_an_ignored_history_directory() -> None:
    assert adapter._BATCH_ROOT.name == "_BATCHES"
    source = Path(adapter.__file__).read_text(encoding="utf-8")
    assert '"batch-plan.json"' in source
    assert '"batch-result.json"' in source
    assert '"history_before"' in source
    assert "build_pair_history_context" in source


def test_server_batch_persists_each_completed_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch_root = tmp_path / "_BATCHES"
    monkeypatch.setattr(adapter, "_BATCH_ROOT", batch_root)
    monkeypatch.setattr(adapter, "_BATCH_POINTER", batch_root / "latest.json")
    cases = [
        {
            "pair": pair,
            "years": 3,
            "test_fingerprint": pair.replace("/", "-"),
            "status": "pending",
            "result": None,
            "error": None,
        }
        for pair in TEN_PAIRS[:2]
    ]
    state = {
        "schema_version": 1,
        "batch_id": "test-batch",
        "batch_fingerprint": "f" * 64,
        "status": "running",
        "stage": "test",
        "progress": 0,
        "years": 3,
        "started_at_utc": "2026-08-23T00:00:00+00:00",
        "updated_at_utc": "2026-08-23T00:00:00+00:00",
        "finished_at_utc": None,
        "current_pair": None,
        "completed_cases": 0,
        "failed_cases": 0,
        "cases": cases,
        "plan": {
            "schema_version": 1,
            "strategy_sha256": api._sha256(api._STRATEGY),
            "cases": cases,
        },
    }
    monkeypatch.setattr(adapter, "_batch_state", state)

    def completed(request):
        return {
            "status": "completed",
            "result": {
                "run_id": request.pair.replace("/", "-"),
                "pair": request.pair,
                "years": request.years,
                "profit_usdt": 1.0,
                "trades": 1,
                "historical_context": {"assessment_de": "erfasst"},
                "test_identity": {
                    "test_fingerprint": request.pair.replace("/", "-")
                },
            },
        }

    monkeypatch.setattr(adapter, "start_backtest", completed)

    adapter._run_batch()

    saved = json.loads(
        (batch_root / "test-batch" / "batch-result.json").read_text(encoding="utf-8")
    )
    assert saved["status"] == "completed"
    assert saved["completed_cases"] == 2
    assert [case["result"]["historical_context"]["assessment_de"] for case in saved["cases"]] == [
        "erfasst",
        "erfasst",
    ]
    assert (batch_root / "test-batch" / "batch-plan.json").is_file()
    assert (batch_root / "latest.json").is_file()


def test_manual_single_run_is_rejected_while_server_batch_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter,
        "_batch_state",
        {"status": "running", "stage": "ETH/USDT", "cases": []},
    )
    adapter._batch_worker_context.active = False

    with pytest.raises(HTTPException, match="kein paralleler Einzeltest") as exc:
        api.start_backtest(api.BacktestRequest(pair="BTC/USDT", years=3))

    assert exc.value.status_code == 409


def test_reused_result_keeps_saved_history_and_timing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = {
        "runs": [
            {
                "run_id": "saved-run",
                "test_fingerprint": "expected",
                "experiment_result": {
                    "historical_context": {"assessment_de": "Vorgänger erfasst"},
                    "timing": {"simulation_seconds": 12.5},
                },
            }
        ]
    }
    monkeypatch.setattr(
        adapter.base,
        "build_test_identity",
        lambda **_kwargs: {
            "test_fingerprint": "expected",
            "strategy_sha256": "6f0a" + "0" * 60,
        },
    )
    monkeypatch.setattr(
        adapter.base,
        "analyze_backtest_history",
        lambda *_args, **_kwargs: existing,
    )
    monkeypatch.setattr(
        adapter.base,
        "registered_experiment",
        lambda *_args: ({"experiment_id": "V12.22"}, []),
    )

    result = adapter._existing_completed_result(
        api.BacktestRequest(pair="BTC/USDT", years=3)
    )

    assert result is not None
    assert result["historical_context"]["assessment_de"] == "Vorgänger erfasst"
    assert result["timing"]["simulation_seconds"] == 12.5


def test_portfolio_target_is_exposed_as_one_shared_wallet_run() -> None:
    source = UI_SCRIPT.read_text(encoding="utf-8")
    assert "PORTFOLIO" not in source
    assert "PORTFOLIO" in api.ALLOWED_TARGETS
    assert "real ten-pair" in Path(
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
