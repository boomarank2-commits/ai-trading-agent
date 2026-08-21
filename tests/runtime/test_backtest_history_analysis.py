from __future__ import annotations

import json
import zipfile
from pathlib import Path

from runtime.backtest_history_analysis import (
    analyze_backtest_history,
    render_markdown,
    write_history_reports,
)


def _write_result(
    root: Path,
    run_id: str,
    *,
    pair: str,
    profit: float,
    source: str = '"""Test strategy V12.9."""\n',
) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    result = {
        "strategy": {
            "CompressionBreakout250": {
                "strategy_name": "CompressionBreakout250",
                "pairlist": [pair],
                "backtest_start": "2025-08-21 00:00:00",
                "backtest_end": "2026-08-21 00:00:00",
                "backtest_days": 365,
                "starting_balance": 250,
                "final_balance": 250 + profit,
                "profit_total_abs": profit,
                "profit_total": profit / 250,
                "total_trades": 2,
                "wins": 1 if profit > 0 else 0,
                "losses": 1,
                "draws": 0,
                "winrate": 0.5 if profit > 0 else 0,
                "profit_factor": 1.5 if profit > 0 else 0.5,
                "max_drawdown_account": 0.04,
                "trades": [
                    {
                        "profit_abs": profit,
                        "enter_tag": "v12_9_champion",
                        "exit_reason": "exit_signal",
                    }
                ],
            }
        }
    }
    archive = run_dir / "result.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("result.json", json.dumps(result))
        output.writestr(
            "result_CompressionBreakout250.py",
            source,
        )
        output.writestr(
            "result_config.json",
            json.dumps({"strategy": "CompressionBreakout250", "dry_run": True}),
        )
        output.writestr("audit/experiment-plan.json", json.dumps({"run_id": run_id}))


def test_history_keeps_completed_and_incomplete_attempts_separate(tmp_path: Path) -> None:
    _write_result(tmp_path, "run-good", pair="BTC/USDT", profit=5.0)
    (tmp_path / "run-incomplete").mkdir()
    (tmp_path / "run-incomplete" / "backtest.log").write_text("aborted", encoding="utf-8")
    (tmp_path / "ui.rar").write_bytes(b"preserved backup")

    report = analyze_backtest_history(tmp_path)

    assert report["summary"] == {
        "attempts": 2,
        "completed": 1,
        "incomplete": 1,
        "strategy_snapshots": 1,
        "unique_material_tests": 1,
        "duplicate_runs": 0,
        "duplicate_groups": 0,
        "supplementary_archives": ["ui.rar"],
    }
    run = report["runs"][0]
    assert run["strategy_version"] == "V12.9"
    assert run["pair"] == "BTC/USDT"
    assert run["period_years"] == 1
    assert run["profit_usdt"] == 5.0
    assert report["incomplete_runs"][0]["run_id"] == "run-incomplete"


def test_history_writes_json_and_readable_markdown(tmp_path: Path) -> None:
    results = tmp_path / "results"
    _write_result(results, "run-good", pair="ETH/USDT", profit=-3.0)
    output_json = tmp_path / "report.json"
    output_markdown = tmp_path / "report.md"

    report = write_history_reports(
        results,
        output_json=output_json,
        output_markdown=output_markdown,
    )

    assert json.loads(output_json.read_text(encoding="utf-8"))["summary"]["completed"] == 1
    markdown = output_markdown.read_text(encoding="utf-8")
    assert markdown == render_markdown(report)
    assert "ETH/USDT" in markdown
    assert "Überlappende Zeiträume" in markdown
    assert (results / "run-good" / "result.zip").is_file()


def test_history_marks_identical_material_runs_without_deleting_evidence(
    tmp_path: Path,
) -> None:
    _write_result(tmp_path, "run-original", pair="BTC/USDT", profit=5.0)
    _write_result(tmp_path, "run-duplicate", pair="BTC/USDT", profit=5.0)

    report = analyze_backtest_history(tmp_path, trial_ledger_path=None)

    assert report["summary"]["completed"] == 2
    assert report["summary"]["unique_material_tests"] == 1
    assert report["summary"]["duplicate_runs"] == 1
    assert len(report["duplicate_test_groups"]) == 1
    assert any(run.get("duplicate_of") for run in report["runs"])
    assert (tmp_path / "run-original" / "result.zip").is_file()
    assert (tmp_path / "run-duplicate" / "result.zip").is_file()
