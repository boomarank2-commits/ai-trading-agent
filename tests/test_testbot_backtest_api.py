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

from runtime import testbot_backtest_api as api

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "runtime"
STRATEGY = RUNTIME / "user_data" / "strategies" / "CompressionBreakout250.py"
UI_SCRIPT = RUNTIME / "ui" / "testbot-backtest.js"


def test_backtest_contract_has_only_current_pairs_and_periods() -> None:
    assert api.ALLOWED_PAIRS == (
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "XRP/USDT",
        "BNB/USDT",
        "DOGE/USDT",
    )
    assert (*api.ALLOWED_PAIRS, "PORTFOLIO") == api.ALLOWED_TARGETS
    assert api._pairs_for_target("PORTFOLIO") == api.ALLOWED_PAIRS
    assert api._pairs_for_target("ETH/USDT") == ("ETH/USDT",)
    assert api.ALLOWED_YEARS == (1, 2, 3)
    assert api.STRATEGY_NAME == "CompressionBreakout250"
    assert api.REQUIRED_TIMEFRAMES == ("15m", "1m", "1h", "4h")
    assert api.BACKTEST_WARMUP_DAYS >= 70


def test_v12_12_backtest_downloads_no_cross_pair_market_context() -> None:
    for pair in api.ALLOWED_PAIRS:
        assert api._btc_context_pair(pair) is None

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


def test_backtest_ui_has_exact_sequential_fourteen_run_audit() -> None:
    source = UI_SCRIPT.read_text(encoding="utf-8")
    batch_block = source.split("const BATCH_CASES = [", maxsplit=1)[1].split("];", maxsplit=1)[0]

    assert 'id="tb-start-all"' in source
    assert "async function startAllBacktests()" in source
    assert "await startOneBacktest(test.pair, test.years)" in source
    assert batch_block.count('pair: "BTC/USDT"') == 2
    assert batch_block.count('pair: "ETH/USDT"') == 2
    assert batch_block.count('pair: "SOL/USDT"') == 2
    assert batch_block.count('pair: "XRP/USDT"') == 2
    assert batch_block.count('pair: "BNB/USDT"') == 2
    assert batch_block.count('pair: "DOGE/USDT"') == 2
    assert batch_block.count('pair: "PORTFOLIO"') == 2
    assert batch_block.count("years: 3") == 7
    assert batch_block.count("years: 1") == 7
    assert "years: 2" not in batch_block
    assert "Doppeltest übersprungen" in source
    assert "error.isDuplicate" in source
    assert "Kapitalzeit genutzt" in source
    assert "Zeit ohne Position" in source
    assert "Dateikontrolle" in source
    assert "Alle 14 Backtests" in source


def test_invalid_pair_is_rejected_before_background_process() -> None:
    request = api.BacktestRequest(pair="ADA/USDT", years=1)
    with pytest.raises(HTTPException) as exc:
        api.start_backtest(request)
    assert exc.value.status_code == 400


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
                "backtest_start": "2025-08-21 00:00:00",
                "backtest_end": "2026-08-21 00:00:00",
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
    assert "PATH" in cleaned
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


def test_locked_backtest_writes_exact_source_file_audit(tmp_path: Path) -> None:
    digest = hashlib.sha256(STRATEGY.read_bytes()).hexdigest()
    audit_path = tmp_path / "file-access-audit.json"
    result = subprocess.run(
        [
            sys.executable,
            str(RUNTIME / "locked_backtest_freqtrade.py"),
            "--strategy-source",
            str(STRATEGY),
            "--strategy-sha256",
            digest,
            "--strategy-class",
            "CompressionBreakout250",
            "--file-audit-output",
            str(audit_path),
            "--",
            "backtesting",
            "--help",
        ],
        cwd=str(RUNTIME),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["context"]["strategy_source"] == str(STRATEGY.resolve())
    assert audit["context"]["strategy_sha256"] == digest
    assert audit["spawned_processes"] == []
    assert str(STRATEGY.resolve()) in {row["path"] for row in audit["opened_files"]}


def test_file_access_audit_hashes_native_candle_boundary(tmp_path: Path) -> None:
    from runtime.locked_backtest_freqtrade import _FileAccessAudit

    candle = tmp_path / "BTC_USDT-15m.feather"
    candle.write_bytes(b"exact candle bytes")
    output = tmp_path / "audit.json"
    audit = _FileAccessAudit(output, {"test": True})

    audit.record_candle_load(candle, "15m")
    audit.record_candle_load(candle, "15m")
    audit.write()

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["candle_loads"] == [
        {
            "path": str(candle.resolve()),
            "timeframe": "15m",
            "sha256_at_load": hashlib.sha256(candle.read_bytes()).hexdigest(),
            "size_at_load": len(b"exact candle bytes"),
            "mtime_ns_at_load": candle.stat().st_mtime_ns,
            "load_count": 2,
        }
    ]


def test_result_finder_ignores_freqtrade_pointer_json(tmp_path: Path) -> None:
    result_zip = tmp_path / "backtest-result-2026-08-22.zip"
    result_zip.write_bytes(b"zip placeholder")
    pointer = tmp_path / ".last_result.json"
    pointer.write_text('{"latest_backtest":"wrong"}', encoding="utf-8")

    assert api._find_result_file(tmp_path) == result_zip


def test_file_audit_accepts_only_exact_requested_candle_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    runtime = repo / "runtime"
    userdir = runtime / "user_data"
    data_root = userdir / "data" / "binance"
    run_dir = userdir / "backtest_results" / "ui" / "run"
    strategy = userdir / "strategies" / "CompressionBreakout250.py"
    config = userdir / "config.json"
    public = userdir / "config-public.json"
    runner = runtime / "locked_backtest_freqtrade.py"
    locked = runtime / "locked_freqtrade.py"
    for path in (strategy, config, public, runner, locked):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(path.name.encode())
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(api, "_REPO_ROOT", repo)
    monkeypatch.setattr(api, "_RUNTIME_ROOT", runtime)
    monkeypatch.setattr(api, "_USERDIR", userdir)
    monkeypatch.setattr(api, "_DATA_ROOT", data_root)
    monkeypatch.setattr(api, "_STRATEGY", strategy)
    monkeypatch.setattr(api, "_CONFIG", config)
    monkeypatch.setattr(api, "_PUBLIC_CONFIG", public)
    monkeypatch.setattr(api, "_BACKTEST_RUNNER", runner)

    candle_rows = []
    for timeframe in api.REQUIRED_TIMEFRAMES:
        path = data_root / f"BTC_USDT-{timeframe}.feather"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(timeframe.encode())
        candle_rows.append(
            {
                "path": str(path.resolve()),
                "sha256_at_load": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    audit_path = run_dir / "file-access-audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "context": {
                    "strategy_sha256": hashlib.sha256(strategy.read_bytes()).hexdigest(),
                    "strategy_source": str(strategy.resolve()),
                },
                "opened_files": [
                    {"path": str(path.resolve())} for path in (strategy, config, public)
                ],
                "candle_loads": candle_rows,
                "spawned_processes": [],
            }
        ),
        encoding="utf-8",
    )

    validation = api._validate_file_access_audit(
        audit_path,
        run_dir,
        ("BTC/USDT",),
        hashlib.sha256(strategy.read_bytes()).hexdigest(),
    )
    assert validation["passed"] is True
    assert validation["expected_candle_sets"] == 4

    unexpected = data_root / "BTC_USDT-5m.feather"
    unexpected.write_bytes(b"unexpected")
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    payload["candle_loads"].append(
        {
            "path": str(unexpected.resolve()),
            "sha256_at_load": hashlib.sha256(unexpected.read_bytes()).hexdigest(),
        }
    )
    audit_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Dateiaudit fehlgeschlagen"):
        api._validate_file_access_audit(
            audit_path,
            run_dir,
            ("BTC/USDT",),
            hashlib.sha256(strategy.read_bytes()).hexdigest(),
        )
