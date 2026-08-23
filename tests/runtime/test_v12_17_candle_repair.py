from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from runtime import ten_pair_backtest_api as adapter


def test_failed_candle_integrity_rebuilds_only_requested_pair(monkeypatch, tmp_path: Path) -> None:
    validation_calls: list[str] = []
    states: list[dict[str, object]] = []
    commands: list[tuple[list[str], Path]] = []

    def fake_validate(pair: str, _start: object, _end: object) -> list[dict[str, object]]:
        validation_calls.append(pair)
        if len(validation_calls) == 1:
            raise RuntimeError("simulated candle gap")
        return [{"pair": pair, "ok": True}]

    paths = {
        timeframe: tmp_path / f"BTC_USDT-{timeframe}.feather"
        for timeframe in adapter.base.REQUIRED_TIMEFRAMES
    }
    for path in paths.values():
        path.write_bytes(b"stale")

    monkeypatch.setattr(adapter, "_original_validate_candle_data", fake_validate)
    monkeypatch.setattr(adapter.base, "_candle_path", lambda _pair, timeframe: paths[timeframe])
    monkeypatch.setattr(adapter.base, "_set_state", lambda **values: states.append(values))
    monkeypatch.setattr(adapter.base, "_RESULTS_ROOT", tmp_path / "results")

    def fake_run_checked(args: list[str], log_path: Path) -> None:
        commands.append((list(args), log_path))

    monkeypatch.setattr(adapter.base, "_run_checked", fake_run_checked)

    start = datetime(2023, 6, 1, tzinfo=UTC)
    end = datetime(2026, 8, 23, tzinfo=UTC)
    result = adapter._validate_or_repair_candle_data("BTC/USDT", start, end)

    assert result == [{"pair": "BTC/USDT", "ok": True}]
    assert validation_calls == ["BTC/USDT", "BTC/USDT"]
    assert all(not path.exists() for path in paths.values())
    assert len(commands) == 1

    args, log_path = commands[0]
    assert args[1:4] == ["-m", "freqtrade", "download-data"]
    assert "--pairs" in args
    pair_index = args.index("--pairs")
    assert args[pair_index + 1] == "BTC/USDT"
    assert "--timeframes" in args
    for timeframe in adapter.base.REQUIRED_TIMEFRAMES:
        assert timeframe in args
    assert "--timerange" in args
    assert log_path.name == "data-repair.log"
    assert any("neu aufgebaut" in str(state.get("stage", "")) for state in states)
    assert any("erfolgreich geprueft" in str(state.get("stage", "")) for state in states)


def test_repo_audit_excludes_only_exact_active_python_environment(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    dependency_prefix = repo / ".venv"
    dependency_file = dependency_prefix / "Lib" / "site-packages" / "pandas" / "__init__.py"
    runtime_file = repo / "runtime" / "locked_freqtrade.py"

    monkeypatch.setattr(adapter.base, "_REPO_ROOT", repo)
    monkeypatch.setattr(adapter, "_python_dependency_prefix", dependency_prefix.resolve())

    assert adapter._audit_boundary_is_within(dependency_file, repo) is False
    assert adapter._audit_boundary_is_within(runtime_file, repo) is True
    assert adapter._audit_boundary_is_within(dependency_file, dependency_prefix) is True
