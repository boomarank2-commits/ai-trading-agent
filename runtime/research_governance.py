"""Repository-level research governance checks.

This module does not trade and does not modify strategy decisions. It validates
that the repository follows the current Deep-Research masterplan: V8 remains
frozen, the superseded Codex phase brief is gone, Deep-Research architecture
boundaries remain explicit, and the trial ledger keeps the fields required for
multiple-testing-aware research.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

V8_LF_SHA256 = "9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280"
MASTERPLAN = "RESEARCH_MASTERPLAN_DE.md"
GAP_AUDIT = "docs/DEEP_RESEARCH_GAP_AUDIT_DE.md"
SUPERSEDED_BRIEF = "CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md"

REQUIRED_LEDGER_COLUMNS = (
    "experiment_id",
    "parent_experiment_id",
    "strategy_version",
    "strategy_hash",
    "parameter_hash",
    "hypothesis",
    "status",
    "date_decided",
    "development_window",
    "validation_window",
    "holdout_window",
    "pairs",
    "fees",
    "trade_count",
    "net_return",
    "profit_factor",
    "sharpe",
    "max_drawdown",
    "reason_accepted_or_rejected",
    "notes",
)

ALLOWED_VOLUME_PARAMETER_HASHES = {"volume_ratio>=1.00", "volume_ratio>=1.25"}

MASTERPLAN_REQUIRED_PHRASES = (
    "V8 bleibt der eingefrorene Champion",
    "`TREND/BREAKOUT`",
    "`RANGE/MEAN_REVERSION`",
    "`NO_TRADE` ist die Default-Aktion",
    "Hot Path",
    "Cold Path / Research Plane",
    "ORB-Retest-Challenger",
    "Bollinger-Mean-Reversion-Challenger",
    "Ichimoku-Trend-Challenger",
    "Walk-Forward",
    "Partial Fills",
    "cancel rejected",
    "position exists at boot",
    "keine automatische Echtgeldfreigabe",
    "B1 = V8 + `volume_ratio >= 1.00`",
    "B2 = V8 + `volume_ratio >= 1.25`",
)

GAP_AUDIT_REQUIRED_PHRASES = (
    "Execution-/Cost-Simulator",
    "Red-Team-/Fault-Injection",
    "Partial Fills",
    "ORB-Retest als separater Challenger",
    "Ichimoku als separater Trend-Challenger",
    "Walk-Forward",
    "READY FOR EXTENDED PAPER TEST \N{EN DASH} NOT READY FOR REAL MONEY",
)


def load_trial_ledger(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("trial ledger has no header")
        rows = [dict(row) for row in reader]
    return list(reader.fieldnames), rows


def validate_trial_ledger(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        header, rows = load_trial_ledger(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    missing = [name for name in REQUIRED_LEDGER_COLUMNS if name not in header]
    if missing:
        errors.append(f"trial ledger missing columns: {', '.join(missing)}")
        return errors

    ids: list[str] = []
    for index, row in enumerate(rows, start=2):
        experiment_id = row.get("experiment_id", "").strip()
        if not experiment_id:
            errors.append(f"row {index}: empty experiment_id")
            continue
        ids.append(experiment_id)
        if not row.get("hypothesis", "").strip():
            errors.append(f"row {index}: {experiment_id} has no hypothesis")
        if not row.get("status", "").strip():
            errors.append(f"row {index}: {experiment_id} has no status")
        if not row.get("date_decided", "").strip():
            errors.append(f"row {index}: {experiment_id} has no date_decided")

    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        errors.append(f"duplicate experiment_id values: {', '.join(duplicates)}")

    id_set = set(ids)
    for row in rows:
        experiment_id = row.get("experiment_id", "").strip()
        parent = row.get("parent_experiment_id", "").strip()
        if parent and parent not in id_set:
            errors.append(f"{experiment_id}: unknown parent experiment {parent}")

    baseline = next(
        (row for row in rows if row.get("experiment_id") == "V8-B0"), None
    )
    if baseline is None:
        errors.append("V8-B0 baseline is missing from trial ledger")
    else:
        if baseline.get("strategy_hash", "").strip() != V8_LF_SHA256:
            errors.append("V8-B0 strategy hash differs from frozen V8 LF SHA256")
        if baseline.get("status", "").strip() != "FROZEN_CHAMPION":
            errors.append(
                "V8-B0 must remain FROZEN_CHAMPION until a manual promotion decision"
            )

    for row in rows:
        experiment_id = row.get("experiment_id", "").strip()
        parameter_hash = row.get("parameter_hash", "").strip()
        is_volume_trial = experiment_id.startswith("V8-B") and "VOLUME" in experiment_id
        if is_volume_trial and parameter_hash not in ALLOWED_VOLUME_PARAMETER_HASHES:
            errors.append(
                f"{experiment_id}: unregistered volume threshold {parameter_hash!r}; "
                "only 1.00 and 1.25 are allowed by the masterplan"
            )

    return errors


def _require_phrases(path: Path, phrases: tuple[str, ...], label: str) -> list[str]:
    if not path.is_file():
        return [f"missing {label}: {path.name}"]
    text = path.read_text(encoding="utf-8")
    return [
        f"{label} missing required contract phrase: {phrase}"
        for phrase in phrases
        if phrase not in text
    ]


def validate_repository(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    errors: list[str] = []

    masterplan = repo_root / MASTERPLAN
    errors.extend(_require_phrases(masterplan, MASTERPLAN_REQUIRED_PHRASES, "masterplan"))

    audit = repo_root / GAP_AUDIT
    errors.extend(_require_phrases(audit, GAP_AUDIT_REQUIRED_PHRASES, "gap audit"))

    if (repo_root / SUPERSEDED_BRIEF).exists():
        errors.append(f"superseded root brief must not be active: {SUPERSEDED_BRIEF}")

    agents = repo_root / "AGENTS.md"
    if not agents.is_file():
        errors.append("missing AGENTS.md")
    else:
        agents_text = agents.read_text(encoding="utf-8")
        if MASTERPLAN not in agents_text:
            errors.append("AGENTS.md does not bind agents to the authoritative masterplan")
        if GAP_AUDIT not in agents_text:
            errors.append("AGENTS.md does not bind agents to the Deep-Research gap audit")
        stale_priority = "Bollinger mean reversion ahead of Ichimoku/ORB ideas"
        if stale_priority in agents_text:
            errors.append("AGENTS.md still contains the superseded challenger priority")
        for phrase in ("ORB-Retest", "Ichimoku", "Bollinger Mean Reversion", "NO_TRADE"):
            if phrase not in agents_text:
                errors.append(f"AGENTS.md missing Deep-Research boundary: {phrase}")

    start_here = repo_root / "START_HERE_DE.md"
    if not start_here.is_file():
        errors.append("missing START_HERE_DE.md")
    else:
        start_text = start_here.read_text(encoding="utf-8")
        for phrase in (GAP_AUDIT, "NO_TRADE", "ORB-Retest", "Ichimoku"):
            if phrase not in start_text:
                errors.append(f"START_HERE_DE.md missing current architecture marker: {phrase}")

    errors.extend(validate_trial_ledger(repo_root / "research" / "trial_ledger.csv"))

    return {
        "ok": not errors,
        "errors": errors,
        "masterplan": MASTERPLAN,
        "gap_audit": GAP_AUDIT,
        "frozen_v8_lf_sha256": V8_LF_SHA256,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args(argv)
    result = validate_repository(args.repo_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
