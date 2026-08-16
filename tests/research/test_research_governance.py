from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from research_governance import (
    GAP_AUDIT,
    MASTERPLAN_REQUIRED_PHRASES,
    REQUIRED_LEDGER_COLUMNS,
    V8_LF_SHA256,
    validate_repository,
    validate_trial_ledger,
)


def test_repository_matches_authoritative_masterplan() -> None:
    result = validate_repository(REPO)
    assert result["ok"], result["errors"]
    assert result["frozen_v8_lf_sha256"] == V8_LF_SHA256
    assert result["gap_audit"] == GAP_AUDIT


def test_masterplan_contains_full_deep_research_contract() -> None:
    text = (REPO / "RESEARCH_MASTERPLAN_DE.md").read_text(encoding="utf-8")
    for phrase in MASTERPLAN_REQUIRED_PHRASES:
        assert phrase in text

    assert "ORB-Retest-Challenger" in text
    assert "Ichimoku-Trend-Challenger" in text
    assert "Bollinger-Mean-Reversion-Challenger" in text
    assert "`NO_TRADE` ist die Default-Aktion" in text
    assert "Partial Fills" in text
    assert "Walk-Forward" in text


def test_gap_audit_keeps_known_incomplete_layers_visible() -> None:
    text = (REPO / GAP_AUDIT).read_text(encoding="utf-8")
    assert "Execution-/Cost-Simulator" in text
    assert "Partial Fills" in text
    assert "PLANNED" in text
    assert "Red-Team-/Fault-Injection" in text
    assert "Die bisherige Datei `tests/replay/test_replay_fault_injection.py`" in text


def test_trial_ledger_rejects_missing_required_columns(tmp_path: Path) -> None:
    path = tmp_path / "trial_ledger.csv"
    path.write_text("experiment_id,hypothesis\nX,test\n", encoding="utf-8")
    errors = validate_trial_ledger(path)
    assert errors
    assert "missing columns" in errors[0]


def test_trial_ledger_rejects_unregistered_volume_threshold(tmp_path: Path) -> None:
    path = tmp_path / "trial_ledger.csv"
    row = {name: "" for name in REQUIRED_LEDGER_COLUMNS}
    row.update(
        {
            "experiment_id": "V8-B3-VOLUME150",
            "strategy_version": "V8-B3",
            "parameter_hash": "volume_ratio>=1.50",
            "hypothesis": "unregistered threshold",
            "status": "RESEARCH",
            "date_decided": "2026-08-16",
            "reason_accepted_or_rejected": "test",
        }
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REQUIRED_LEDGER_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    errors = validate_trial_ledger(path)
    assert any("unregistered volume threshold" in error for error in errors)
