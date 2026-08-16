from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from research_governance import (
    REQUIRED_LEDGER_COLUMNS,
    V8_LF_SHA256,
    validate_repository,
    validate_trial_ledger,
)


def test_repository_matches_authoritative_masterplan() -> None:
    result = validate_repository(REPO)
    assert result["ok"], result["errors"]
    assert result["frozen_v8_lf_sha256"] == V8_LF_SHA256


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
