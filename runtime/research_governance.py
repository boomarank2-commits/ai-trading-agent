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
V12_12_SHA256 = "9978cbcc00af80bb77933f8246cd9e78c73ef1d54b0a60e0b8f24e85e8f39993"
V12_13_SHA256 = "043916a93ef9aafac3622425496ca2cd75f01c639bb3dc345a79887e882813d9"
V12_14_SHA256 = "0141348dda98810508f23e6c1b63ed19fb9f5e384841b35a4d49f84d870a77f2"
V12_15_SHA256 = "3c5aaf823e16c1a2901c4861fcf6dbc21da4dd0f1314385d78be1f2de86c4a97"
V12_16_SHA256 = "9ad6f3e96d0f440a8a9cf4029cb6f64b7f6b73aba6ab524310f192797c1b6acf"
V12_17_SHA256 = "772084097ef718603dfe7eae06b9318efee9ee8bf9f90dc22fdd76f525ab0f0b"
V12_18_SHA256 = "ce0dc4938a365c593a4e06589f910b4c3b2a86020f6903b92bc1dbcca7f11fb4"
V12_19_SHA256 = "6f0a006a7c459a165105ddf245222d99b27961acfd5ccde47b46181534f256ce"
V12_20_SHA256 = "8eb1ad98e3cf13ea05c9c7f6dfb7c4b50b425741d3e225116e3b29f80391a3fb"
V12_21_SHA256 = "53642d7cddd1b55d66462c83d87d4093f428a9f797aee95c5f389f34541c8b1d"
V12_22_SHA256 = "f7aac4afe8204aa7ce28a4a2bbf1d3c579ff4f084effa8bbff1c78ad8e9d2caf"
V12_23_SHA256 = "248fdac232c65d3c13b9946059a3932f5ed568d5656cbed0fed729f0d6ec10a0"
V12_24_SHA256 = "b7a479b70b5dd0b82531ec5f24dcffd8493fdfbb77af1ce902e3d9a8fe08bb0d"
V12_25_SHA256 = "5b4ac18b86d38a86114a67955bd5b452c52526211513a880f8de2f86bce92c5d"
V12_26_SHA256 = "ba7752f8b03600cb244bab6b291e7200d56f6d6e14620ede6f6edd6443b10634"
V12_27_SHA256 = "a47396306f6b15c1cbc4f6e1c7339d8e494092e101fb858f2258c7c67bbd5544"
V12_28_SHA256 = "50b940c5d690fd06cdb7224ec4a3cbb8d05784c8c03bd21fa434cf16130c5aea"
V12_29_SHA256 = "c02334560907c7cc61b3265daf345c13e8eb5da78a5101684ec8f3e97d1fb8cf"
V12_30_SHA256 = "978c4626ba213de9bf8b93acceaf209074ab41b9d31a5a62da893e3018925630"
V12_31_SHA256 = "e13a324560a4941350edd30b53e69ed6286eeb77f2b31673a859c3144e8965d5"
V12_33_SHA256 = "58d59413ef41b798c75c41bab0f98e377316ad3b289b6ba874876e841cdfb263"
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
    "change_summary",
    "acceptance_criteria",
    "result_summary",
    "decision",
    "lessons",
    "next_experiment",
)
REQUIRED_TEST_FINGERPRINT_COLUMNS = (
    "test_fingerprint",
    "run_id",
    "experiment_id",
    "strategy_hash",
    "pair",
    "years",
    "executed_at_utc",
    "outcome",
    "formal_valid",
    "profit_usdt",
    "trades",
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
    hashes: list[str] = []
    detailed_fields = (
        "change_summary",
        "acceptance_criteria",
        "result_summary",
        "decision",
        "lessons",
        "next_experiment",
    )
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
        for field in detailed_fields:
            if not row.get(field, "").strip():
                errors.append(f"row {index}: {experiment_id} has no {field}")
        strategy_hash = row.get("strategy_hash", "").strip()
        if strategy_hash:
            hashes.append(strategy_hash)

    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        errors.append(f"duplicate experiment_id values: {', '.join(duplicates)}")

    duplicate_hashes = sorted({value for value in hashes if hashes.count(value) > 1})
    if duplicate_hashes:
        errors.append(
            "strategy hashes must identify exactly one experiment: "
            + ", ".join(value[:12] for value in duplicate_hashes)
        )

    id_set = set(ids)
    for row in rows:
        experiment_id = row.get("experiment_id", "").strip()
        parent = row.get("parent_experiment_id", "").strip()
        if parent and parent not in id_set:
            errors.append(f"{experiment_id}: unknown parent experiment {parent}")

    baseline = next((row for row in rows if row.get("experiment_id") == "V8-B0"), None)
    if baseline is None:
        errors.append("V8-B0 baseline is missing from trial ledger")
    else:
        if baseline.get("strategy_hash", "").strip() != V8_LF_SHA256:
            errors.append("V8-B0 strategy hash differs from frozen V8 LF SHA256")
        if baseline.get("status", "").strip() != "FROZEN_CHAMPION":
            errors.append("V8-B0 must remain FROZEN_CHAMPION until a manual promotion decision")

    v12_12 = next(
        (row for row in rows if row.get("experiment_id") == "V12.12-LIQUID-UNIVERSE"),
        None,
    )
    if v12_12 is None or v12_12.get("strategy_hash", "").strip() != V12_12_SHA256:
        errors.append("V12.12 strategy is not exactly registered in trial ledger")

    v12_13 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.13-REMOVE-ETH-RECLAIM"
        ),
        None,
    )
    if v12_13 is None or v12_13.get("strategy_hash", "").strip() != V12_13_SHA256:
        errors.append("V12.13 strategy is not exactly registered in trial ledger")

    v12_14 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.14-FIRST-LOSS-PAIR-PAUSE"
        ),
        None,
    )
    if v12_14 is None or v12_14.get("strategy_hash", "").strip() != V12_14_SHA256:
        errors.append("V12.14 strategy is not exactly registered in trial ledger")

    v12_15 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.15-LATE-PROFIT-RATCHET"
        ),
        None,
    )
    if v12_15 is None or v12_15.get("strategy_hash", "").strip() != V12_15_SHA256:
        errors.append("V12.15 strategy is not exactly registered in trial ledger")

    v12_16 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.16-ADA-LIQUID-UNIVERSE"
        ),
        None,
    )
    if v12_16 is None or v12_16.get("strategy_hash", "").strip() != V12_16_SHA256:
        errors.append("V12.16 strategy is not exactly registered in trial ledger")

    v12_17 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.17-TEN-PAIR-THREE-CHUNK-PAPER"
        ),
        None,
    )
    if v12_17 is None or v12_17.get("strategy_hash", "").strip() != V12_17_SHA256:
        errors.append("V12.17 strategy is not exactly registered in trial ledger")

    v12_18 = next(
        (
            row
            for row in rows
            if row.get("experiment_id")
            == "V12.18-TEN-PAIR-PROFIT-PYRAMID-REPAIR"
        ),
        None,
    )
    if v12_18 is None or v12_18.get("strategy_hash", "").strip() != V12_18_SHA256:
        errors.append("V12.18 strategy is not exactly registered in trial ledger")

    v12_19 = next(
        (
            row
            for row in rows
            if row.get("experiment_id")
            == "V12.19-PERSISTENT-PAIR-LEARNING-FAST-BACKTEST"
        ),
        None,
    )
    if v12_19 is None or v12_19.get("strategy_hash", "").strip() != V12_19_SHA256:
        errors.append("V12.19 strategy is not exactly registered in trial ledger")

    v12_20 = next(
        (
            row
            for row in rows
            if row.get("experiment_id")
            == "V12.20-SELECTIVE-PYRAMID-ELIGIBILITY"
        ),
        None,
    )
    if v12_20 is None or v12_20.get("strategy_hash", "").strip() != V12_20_SHA256:
        errors.append("V12.20 strategy is not exactly registered in trial ledger")

    v12_21 = next(
        (
            row
            for row in rows
            if row.get("experiment_id")
            == "V12.21-PAIR-LOCAL-LTC-BCH-VOLUME100"
        ),
        None,
    )
    if v12_21 is None or v12_21.get("strategy_hash", "").strip() != V12_21_SHA256:
        errors.append("V12.21 strategy is not exactly registered in trial ledger")

    v12_22 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.22-SOL-ADX21"
        ),
        None,
    )
    if v12_22 is None or v12_22.get("strategy_hash", "").strip() != V12_22_SHA256:
        errors.append("V12.22 strategy is not exactly registered in trial ledger")

    v12_23 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.23-LTC-EMA30-80-MACRO200"
        ),
        None,
    )
    if v12_23 is None or v12_23.get("strategy_hash", "").strip() != V12_23_SHA256:
        errors.append("V12.23 strategy is not exactly registered in trial ledger")

    v12_24 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.24-LTC-EMPTY-PORTFOLIO-ENTRY"
        ),
        None,
    )
    if v12_24 is None or v12_24.get("strategy_hash", "").strip() != V12_24_SHA256:
        errors.append("V12.24 strategy is not exactly registered in trial ledger")

    v12_25 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.25-BCH-EMA30-80-MACRO100"
        ),
        None,
    )
    if v12_25 is None or v12_25.get("strategy_hash", "").strip() != V12_25_SHA256:
        errors.append("V12.25 strategy is not exactly registered in trial ledger")

    v12_26 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.26-BCH-EMA30-80-MACRO100-FIX"
        ),
        None,
    )
    if v12_26 is None or v12_26.get("strategy_hash", "").strip() != V12_26_SHA256:
        errors.append("V12.26 strategy is not exactly registered in trial ledger")

    v12_27 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.27-TRX-DONCHIAN40-MACRO200"
        ),
        None,
    )
    if v12_27 is None or v12_27.get("strategy_hash", "").strip() != V12_27_SHA256:
        errors.append("V12.27 strategy is not exactly registered in trial ledger")

    v12_28 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.28-TRX40-SINGLE-BLOCK"
        ),
        None,
    )
    if v12_28 is None or v12_28.get("strategy_hash", "").strip() != V12_28_SHA256:
        errors.append("V12.28 strategy is not exactly registered in trial ledger")

    v12_29 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.29-BNB-DONCHIAN80-MACRO200"
        ),
        None,
    )
    if v12_29 is None or v12_29.get("strategy_hash", "").strip() != V12_29_SHA256:
        errors.append("V12.29 strategy is not exactly registered in trial ledger")

    v12_30 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.30-DOGE-SUPERTREND20X3-MACRO100"
        ),
        None,
    )
    if v12_30 is None or v12_30.get("strategy_hash", "").strip() != V12_30_SHA256:
        errors.append("V12.30 strategy is not exactly registered in trial ledger")

    v12_31 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.31-DOGE-BCH-FIXED-ROUTE-COMBINATION"
        ),
        None,
    )
    if v12_31 is None or v12_31.get("strategy_hash", "").strip() != V12_31_SHA256:
        errors.append("V12.31 strategy is not exactly registered in trial ledger")

    v12_33 = next(
        (
            row
            for row in rows
            if row.get("experiment_id") == "V12.33-LTC-NO-TRADE-COUNTERFACTUAL"
        ),
        None,
    )
    if v12_33 is None or v12_33.get("strategy_hash", "").strip() != V12_33_SHA256:
        errors.append("V12.33 strategy is not exactly registered in trial ledger")

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


def validate_test_fingerprint_ledger(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing executed-test ledger: {path.name}"]
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames or []
        rows = list(reader)
    errors = [
        f"executed-test ledger missing column: {column}"
        for column in REQUIRED_TEST_FINGERPRINT_COLUMNS
        if column not in header
    ]
    fingerprints = []
    for index, row in enumerate(rows, start=2):
        fingerprint = str(row.get("test_fingerprint") or "").strip()
        fingerprints.append(fingerprint)
        if len(fingerprint) != 64 or any(ch not in "0123456789abcdef" for ch in fingerprint):
            errors.append(f"executed-test row {index}: invalid fingerprint")
        if str(row.get("formal_valid") or "").lower() not in {"true", "false"}:
            errors.append(f"executed-test row {index}: formal_valid must be true or false")
    duplicate_fingerprints = sorted(
        {value for value in fingerprints if value and fingerprints.count(value) > 1}
    )
    if duplicate_fingerprints:
        errors.append(
            "duplicate executed test fingerprints: "
            + ", ".join(value[:12] for value in duplicate_fingerprints)
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
    errors.extend(
        validate_test_fingerprint_ledger(
            repo_root / "research" / "executed_test_fingerprints.csv"
        )
    )

    return {
        "ok": not errors,
        "errors": errors,
        "masterplan": MASTERPLAN,
        "gap_audit": GAP_AUDIT,
        "frozen_v8_lf_sha256": V8_LF_SHA256,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    result = validate_repository(args.repo_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
