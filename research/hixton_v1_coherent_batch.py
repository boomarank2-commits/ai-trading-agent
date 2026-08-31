from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import hixton_v1_causal_analysis as base

EXPECTED_PAIR_TRADES = {
    "BTC/USDT": 674,
    "ETH/USDT": 651,
    "SOL/USDT": 664,
    "XRP/USDT": 624,
    "BNB/USDT": 587,
    "DOGE/USDT": 648,
    "LINK/USDT": 676,
    "TRX/USDT": 784,
    "LTC/USDT": 420,
    "BCH/USDT": 600,
}
EXPECTED_TOTAL_TRADES = sum(EXPECTED_PAIR_TRADES.values())


def _completed_batch_candidates(results_root: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    batch_root = results_root / "_BATCHES"
    for path in batch_root.glob("*/batch-result.json"):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        plan = state.get("plan") or {}
        cases = state.get("cases") or []
        if int(state.get("years") or 0) != 3:
            continue
        if plan.get("strategy_sha256") != base.STRATEGY_SHA256:
            continue
        if int(state.get("failed_cases") or 0) != 0:
            continue
        if len(cases) != len(base.PAIRS):
            continue
        if {str(case.get("pair") or "") for case in cases} != set(base.PAIRS):
            continue
        if any(case.get("status") not in {"completed", "reused"} for case in cases):
            continue
        if any(not isinstance(case.get("result"), dict) for case in cases):
            continue
        if any(not str(case["result"].get("run_id") or "") for case in cases):
            continue
        candidates.append({"path": path, "state": state})
    return candidates


def _load_exact_batch_rows(results_root: Path, batch: dict[str, Any]) -> list[dict[str, Any]]:
    run_ids = {
        str(case["pair"]): str(case["result"]["run_id"])
        for case in batch["cases"]
    }

    # Expose only the ten exact run directories to the already-audited parser.
    # Duplicate standalone runs elsewhere in results_root can therefore never
    # affect which trades enter the causal analysis.
    with tempfile.TemporaryDirectory(prefix="hixton-cohort-") as tmp:
        view = Path(tmp)
        for pair, run_id in run_ids.items():
            source = results_root / run_id
            if not source.is_dir():
                raise RuntimeError(
                    f"Batch {batch.get('batch_id')}: missing run folder {run_id} for {pair}"
                )
            target = view / run_id
            try:
                os.symlink(source, target, target_is_directory=True)
            except OSError:
                target.mkdir(parents=True, exist_ok=True)
                for src in source.iterdir():
                    is_result_zip = src.name.startswith("backtest-result-") and src.suffix == ".zip"
                    if src.name != "experiment-result.json" and not is_result_zip:
                        continue
                    dst = target / src.name
                    try:
                        os.link(src, dst)
                    except OSError:
                        dst.write_bytes(src.read_bytes())
        return base.load_diagnostic_trades(view)


def _pair_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {pair: 0 for pair in base.PAIRS}
    for row in rows:
        counts[str(row["pair"])] += 1
    return counts


def _cohort_signature(rows: list[dict[str, Any]]) -> str:
    """Stable evidence signature independent of batch/run folder names."""
    payload = [
        (
            str(row["pair"]),
            int(row["open_timestamp"]),
            int(row["close_timestamp"]),
            round(float(row["open_rate"]), 12),
            round(float(row["close_rate"]), 12),
            round(float(row["profit_abs"]), 12),
        )
        for row in sorted(rows, key=lambda r: (str(r["pair"]), int(r["open_timestamp"]), int(r["close_timestamp"])))
    ]
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def select_locked_batch(results_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    structural = _completed_batch_candidates(results_root)
    evidence_matches: list[tuple[dict[str, Any], list[dict[str, Any]], str]] = []
    rejected: list[str] = []

    for item in structural:
        batch = item["state"]
        batch_id = str(batch.get("batch_id") or item["path"].parent.name)
        try:
            rows = _load_exact_batch_rows(results_root, batch)
        except RuntimeError as exc:
            rejected.append(f"{batch_id}: {exc}")
            continue
        counts = _pair_counts(rows)
        if counts != EXPECTED_PAIR_TRADES or len(rows) != EXPECTED_TOTAL_TRADES:
            rejected.append(f"{batch_id}: counts={counts}, total={len(rows)}")
            continue
        evidence_matches.append((batch, rows, _cohort_signature(rows)))

    if not evidence_matches:
        details = "; ".join(rejected[-5:]) if rejected else "no structurally complete matching-strategy batches"
        raise RuntimeError(
            "No complete 6328-trade diagnostic evidence cohort was found. "
            "The causal analysis refuses to mix standalone runs from different batches. "
            f"Checked: {details}"
        )

    signatures = {sig for _, _, sig in evidence_matches}
    if len(signatures) > 1:
        ids = [str(batch.get("batch_id")) for batch, _, _ in evidence_matches]
        raise RuntimeError(
            "Multiple complete 6328-trade diagnostic batches exist but their trade content differs. "
            f"Manual cohort selection is required; batch_ids={ids}."
        )

    evidence_matches.sort(
        key=lambda item: str(
            item[0].get("finished_at_utc")
            or item[0].get("updated_at_utc")
            or item[0].get("started_at_utc")
            or ""
        ),
        reverse=True,
    )
    return evidence_matches[0]


def load_locked_diagnostic_trades(
    results_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    batch, rows, signature = select_locked_batch(results_root)
    per_pair = _pair_counts(rows)
    run_ids = {
        str(case["pair"]): str(case["result"]["run_id"])
        for case in batch["cases"]
    }

    # Defense in depth even though select_locked_batch already checked this.
    if per_pair != EXPECTED_PAIR_TRADES or len(rows) != EXPECTED_TOTAL_TRADES:
        raise RuntimeError(
            "Locked diagnostic cohort does not match the preregistered 6328-trade evidence set. "
            f"Expected {EXPECTED_PAIR_TRADES}, got {per_pair}; total={len(rows)}."
        )

    metadata = {
        "batch_id": batch.get("batch_id"),
        "batch_fingerprint": batch.get("batch_fingerprint"),
        "source_commit": (batch.get("plan") or {}).get("source_commit"),
        "finished_at_utc": batch.get("finished_at_utc"),
        "run_ids": run_ids,
        "pair_trade_counts": per_pair,
        "total_trades": len(rows),
        "evidence_signature_sha256": signature,
        "selection_rule": "single coherent 10-run batch; diagnostic strategy hash; exact preregistered 6328 trade counts; identical-content duplicates allowed",
    }
    return rows, metadata
