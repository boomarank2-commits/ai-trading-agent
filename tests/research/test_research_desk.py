import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from research.collect_output import collect, safe_remove_tree
from research.stage_market_data import stage

ROOT = Path(__file__).resolve().parents[2]


def test_schedule_is_bounded_and_points_to_existing_upstream_roles() -> None:
    config = json.loads((ROOT / "research" / "desk.json").read_text(encoding="utf-8"))

    assert config["schema_version"] == 1
    assert config["poll_seconds"] >= 15
    assert 5 <= config["max_cycle_minutes"] <= 120
    assert 1024 <= config["max_output_bytes"] <= 10 * 1024 * 1024
    assert config["holdout_cutoff_utc"].endswith("Z")

    names: set[str] = set()
    for role in config["roles"]:
        assert role["name"] not in names
        names.add(role["name"])
        assert role["interval_minutes"] >= 15

        path = (ROOT / role["file"]).resolve()
        assert path.is_relative_to(ROOT.resolve())
        assert path.is_file()


def test_experimental_calendar_role_is_opt_in() -> None:
    config = json.loads((ROOT / "research" / "desk.json").read_text(encoding="utf-8"))
    calendar = next(role for role in config["roles"] if role["name"] == "calendar-baseline")
    assert calendar["enabled"] is False


def test_scheduler_sanitizes_exchange_secrets_and_keeps_sandbox() -> None:
    script = (ROOT / "research" / "Start-ResearchDesk.ps1").read_text(encoding="utf-8")

    assert "Clear-ResearchEnvironment" in script
    assert "Get-ChildItem Env:" in script
    assert "temporaryRoot" in script
    assert "New-IsolatedWorkspace" in script
    assert "registry-snapshot.json" in script
    assert "research\\inbox" not in script  # joined safely from its path components
    assert '"--sandbox", "workspace-write"' in script
    assert "--ignore-user-config" in script
    assert "--skip-git-repo-check" in script
    assert "--dangerously-bypass-approvals-and-sandbox" not in script
    assert "Start-Process" in script
    assert "taskkill.exe" in script
    assert "FileShare]::None" in script
    assert "stage_market_data.py" in script
    assert "collect_output.py" in script
    assert "Copy-Item -Recurse" not in script
    assert "Remove-Item -Recurse" not in script
    assert "Do not start dry-run or live" in script
    assert "place orders" in script
    assert "Tee-Object" not in script


def test_autonomous_scheduler_is_hard_disabled_before_any_cycle() -> None:
    script = (ROOT / "research" / "Start-ResearchDesk.ps1").read_text(encoding="utf-8")

    guard = 'throw "AUTONOMOUS_RESEARCH_DISABLED:'
    assert guard in script
    assert script.index(guard) < script.index("Acquire-DeskLock\ntry")


def test_candidate_contract_has_no_lifecycle_self_promotion() -> None:
    contract = (ROOT / "local-prompts" / "candidate-contract.md").read_text(encoding="utf-8")

    for required in (
        '"strategy_class"',
        '"hypothesis"',
        '"major_change"',
        '"research_timerange"',
        '"validation_timerange"',
        '"holdout_label"',
        '"fee_ratio"',
        '"slippage_ratio"',
    ):
        assert required in contract

    assert "Do not set a lifecycle" in contract


def test_market_data_staging_excludes_holdout_candles() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "source"
        destination = root / "destination"
        source.mkdir()
        destination.mkdir()
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    ["2025-08-11T23:45:00Z", "2025-08-12T00:00:00Z"], utc=True
                ),
                "open": [1.0, 2.0],
                "high": [1.1, 2.1],
                "low": [0.9, 1.9],
                "close": [1.05, 2.05],
                "volume": [10.0, 20.0],
            }
        )
        frame.to_feather(source / "BTC_USDT-15m.feather")
        result = stage(source, destination, "2025-08-12T00:00:00Z")
        staged = pd.read_feather(destination / "BTC_USDT-15m.feather")
        assert result["ok"] is True
        assert len(staged) == 1
        assert staged.iloc[0]["date"] < pd.Timestamp("2025-08-12T00:00:00Z")


def test_output_collector_accepts_only_small_regular_contract() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "output"
        destination = root / "inbox"
        candidates = source / "candidates"
        candidates.mkdir(parents=True)
        (source / "report.md").write_text("result\n", encoding="utf-8")
        (candidates / "Alpha.py").write_text("x = 1\n", encoding="utf-8")
        (candidates / "Alpha.candidate.json").write_text("{}\n", encoding="utf-8")
        result = collect(source, destination, 4096)
        assert result["files"] == [
            "candidates/Alpha.candidate.json",
            "candidates/Alpha.py",
            "report.md",
        ]
        assert (destination / "report.md").read_text(encoding="utf-8") == "result\n"


def test_output_collector_rejects_hardlinks_and_unexpected_files() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "output"
        source.mkdir()
        original = root / "original.md"
        original.write_text("linked\n", encoding="utf-8")
        try:
            os.link(original, source / "report.md")
        except OSError:
            pytest.skip("hardlinks are unavailable on this filesystem")
        with pytest.raises(ValueError, match="hardlinks"):
            collect(source, root / "inbox", 4096)

        (source / "report.md").unlink()
        (source / "report.md").write_text("ok\n", encoding="utf-8")
        (source / "unexpected.txt").write_text("no\n", encoding="utf-8")
        with pytest.raises(ValueError, match="unexpected research output"):
            collect(source, root / "other-inbox", 4096)


def test_safe_cleanup_is_confined_to_direct_temporary_child() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        parent = Path(temporary)
        workspace = parent / "one-cycle"
        workspace.mkdir()
        (workspace / "scratch.txt").write_text("temporary\n", encoding="utf-8")
        safe_remove_tree(workspace, parent)
        assert not workspace.exists()
