from __future__ import annotations

import json
import zipfile
from pathlib import Path

from runtime.backtest_history_analysis import (
    analyze_backtest_history,
    build_pair_history_context,
    capital_utilization_metrics,
    render_markdown,
    render_pair_history_markdown,
    write_history_reports,
)


def _write_result(
    root: Path,
    run_id: str,
    *,
    pair: str | list[str],
    profit: float,
    source: str = '"""Test strategy V12.9."""\n',
) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    result = {
        "strategy": {
            "CompressionBreakout250": {
                "strategy_name": "CompressionBreakout250",
                "pairlist": [pair] if isinstance(pair, str) else pair,
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


def test_failed_run_contract_keeps_generated_zip_as_incomplete_evidence(tmp_path: Path) -> None:
    _write_result(tmp_path, "audit-failed", pair="BTC/USDT", profit=5.0)
    result_path = tmp_path / "audit-failed" / "experiment-result.json"
    result_path.write_text(
        json.dumps({"outcome": "failed", "error": "native candle audit missing"}),
        encoding="utf-8",
    )

    report = analyze_backtest_history(tmp_path, trial_ledger_path=None)

    assert report["summary"]["completed"] == 0
    assert report["summary"]["incomplete"] == 1
    failed = report["incomplete_runs"][0]
    assert failed["run_id"] == "audit-failed"
    assert failed["test_fingerprint"]
    assert "native candle audit missing" in failed["reason"]


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


def test_pair_history_records_previous_material_run_and_metric_deltas(
    tmp_path: Path,
) -> None:
    _write_result(
        tmp_path,
        "run-v12-18",
        pair="ETH/USDT",
        profit=4.0,
        source='"""Test strategy V12.18."""\nVALUE = 18\n',
    )
    _write_result(
        tmp_path,
        "run-v12-19",
        pair="ETH/USDT",
        profit=9.5,
        source='"""Test strategy V12.19."""\nVALUE = 19\n',
    )

    report = analyze_backtest_history(tmp_path, trial_ledger_path=None)
    history = build_pair_history_context(
        report,
        pair="ETH/USDT",
        years=1,
        current_run_id="run-v12-19",
    )

    assert history["current"]["run_id"] == "run-v12-19"
    assert history["previous"]["run_id"] == "run-v12-18"
    assert history["delta_vs_previous"]["profit_usdt"] == 5.5
    assert history["duplicate_execution_allowed"] is False
    assert len(history["all_preserved_runs"]) == 2
    assert "change_summary" in history["current"]
    assert "hypothesis" in history["current"]
    assert "lessons" in history["current"]
    markdown = render_pair_history_markdown(history)
    assert "ETH/USDT" in markdown
    assert "+5.50 USDT" in markdown


def test_pair_history_includes_only_same_pair_ledger_attempts_without_ui_run(
    tmp_path: Path,
) -> None:
    _write_result(tmp_path, "run-eth", pair="ETH/USDT", profit=4.0)
    report = analyze_backtest_history(tmp_path, trial_ledger_path=None)
    report["experiment_ledger"] = [
        {
            "experiment_id": "ETH-REJECTED",
            "strategy_version": "V99.1",
            "pairs": "ETH/USDT",
            "hypothesis": "ETH-only idea",
            "decision": "REJECT_DO_NOT_REPEAT",
            "lessons": "Did not survive costs.",
            "next_experiment": "Use a different ETH family.",
        },
        {
            "experiment_id": "BTC-ONLY",
            "strategy_version": "V99.2",
            "pairs": "BTC/USDT",
            "hypothesis": "BTC-only idea",
        },
        {
            "experiment_id": "PORTFOLIO-SOL-CHANGE",
            "strategy_version": "V99.3",
            "pairs": "ETH/USDT;SOL/USDT",
            "hypothesis": "Change only SOL and preserve ETH.",
            "change_summary": "Replace only SOL.",
        },
        {
            "experiment_id": "PORTFOLIO-ETH-CHANGE",
            "strategy_version": "V99.4",
            "pairs": "ETH/USDT;SOL/USDT",
            "hypothesis": "Change only ETH and preserve SOL.",
            "change_summary": "Replace only ETH.",
        },
    ]

    history = build_pair_history_context(report, pair="ETH/USDT", years=1)

    documented = history["documented_pair_experiments"]
    assert [row["experiment_id"] for row in documented] == [
        "PORTFOLIO-ETH-CHANGE",
        "ETH-REJECTED",
    ]
    markdown = render_pair_history_markdown(history)
    assert "ETH-REJECTED" in markdown
    assert "BTC-ONLY" not in markdown
    assert "PORTFOLIO-SOL-CHANGE" not in markdown


def test_history_report_writes_separate_pair_learning_files(tmp_path: Path) -> None:
    _write_result(tmp_path, "run-good", pair="BTC/USDT", profit=5.0)

    write_history_reports(tmp_path, trial_ledger_path=None)

    pair_root = tmp_path / "_PAIR_HISTORIEN"
    assert (pair_root / "BTC_USDT-1J.json").is_file()
    assert (pair_root / "BTC_USDT-1J.md").is_file()
    # Generated learning directories are not mistaken for failed simulations.
    assert analyze_backtest_history(tmp_path, trial_ledger_path=None)["summary"][
        "incomplete"
    ] == 0


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


def test_capital_utilization_measures_overlap_and_idle_time() -> None:
    trades = [
        {
            "open_date": "2026-01-01 00:00:00+00:00",
            "close_date": "2026-01-06 00:00:00+00:00",
            "stake_amount": 80,
        },
        {
            "open_date": "2026-01-04 00:00:00+00:00",
            "close_date": "2026-01-09 00:00:00+00:00",
            "stake_amount": 80,
        },
    ]

    metrics = capital_utilization_metrics(
        trades,
        "2026-01-01 00:00:00+00:00",
        "2026-01-11 00:00:00+00:00",
    )

    assert metrics == {
        "capital_time_utilization_pct": 32.0,
        "no_position_time_pct": 20.0,
        "average_open_positions": 1.0,
        "max_simultaneous_positions": 2,
        "total_entry_chunks": 2,
        "additional_entry_chunks": 0,
        "trades_with_multiple_entries": 0,
        "max_entries_per_trade": 1,
        "max_active_entry_chunks": 2,
        "max_deployed_capital_usdt": 160.0,
    }


def test_capital_utilization_uses_actual_position_adjustment_fill_times() -> None:
    trades = [
        {
            "open_date": "2026-01-01 00:00:00+00:00",
            "close_date": "2026-01-11 00:00:00+00:00",
            "stake_amount": 240,
            "orders": [
                {
                    "ft_is_entry": True,
                    "order_filled_timestamp": 1767225600000,
                    "cost": 80,
                },
                {
                    "ft_is_entry": True,
                    "order_filled_timestamp": 1767657600000,
                    "cost": 80,
                },
                {
                    "ft_is_entry": True,
                    "order_filled_timestamp": 1767916800000,
                    "cost": 80,
                },
            ],
        }
    ]

    metrics = capital_utilization_metrics(
        trades,
        "2026-01-01 00:00:00+00:00",
        "2026-01-11 00:00:00+00:00",
    )

    # 80 for five days, 160 for three days and 240 for two days.
    assert metrics["capital_time_utilization_pct"] == 54.4
    assert metrics["total_entry_chunks"] == 3
    assert metrics["additional_entry_chunks"] == 2
    assert metrics["trades_with_multiple_entries"] == 1
    assert metrics["max_entries_per_trade"] == 3
    assert metrics["max_active_entry_chunks"] == 3
    assert metrics["max_deployed_capital_usdt"] == 240.0


def test_portfolio_archive_is_separate_from_single_pair_matrix(tmp_path: Path) -> None:
    _write_result(
        tmp_path,
        "portfolio",
        pair=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        profit=7.0,
    )

    report = analyze_backtest_history(tmp_path, trial_ledger_path=None)

    assert report["runs"][0]["pair"] == "PORTFOLIO"
    matrix = report["strategy_matrices"][0]
    assert matrix["portfolio_runs"] == 1
    assert matrix["latest_cells"] == 0
    assert matrix["current_six_run_matrix"] is False


def test_v12_18_matrix_requires_all_ten_pairs_for_each_available_period(
    tmp_path: Path,
) -> None:
    pairs = (
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
    source = '\"\"\"Test strategy V12.18.\"\"\"\n'
    for index, pair in enumerate(pairs):
        _write_result(
            tmp_path,
            f"v12-18-{index}",
            pair=pair,
            profit=1.0,
            source=source,
        )

    report = analyze_backtest_history(tmp_path, trial_ledger_path=None)
    matrix = report["strategy_matrices"][0]

    assert matrix["matrix_pairs"] == list(pairs)
    assert matrix["latest_cells"] == 10
    assert matrix["expected_cells"] == 10
    assert matrix["matrix_complete"] is True
    assert matrix["current_ten_pair_matrix"] is True
