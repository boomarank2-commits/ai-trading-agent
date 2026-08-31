from __future__ import annotations

import json
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
        case_pairs = {str(case.get("pair") or "") for case in cases}
        if case_pairs != set(base.PAIRS):
            continue
        if any(case.get("status") not in {"completed", "reused"} for case in cases):
            continue
        if any(not isinstance(case.get("result"), dict) for case in cases):
            continue
        if any(not str(case["result"].get("run_id") or "") for case in cases):
            continue
        candidates.append({"path": path, "state": state})
    return candidates


def select_locked_batch(results_root: Path) -> dict[str, Any]:
    candidates = _completed_batch_candidates(results_root)
    if not candidates:
        raise RuntimeError(
            "No complete 10-coin HIXTON-V1 diagnostic batch found. "
            "The causal analysis refuses to mix standalone runs from different batches."
        )

    # Prefer the newest fully completed coherent batch, but only accept the
    # preregistered 6328-trade evidence cohort below.
    candidates.sort(
        key=lambda item: str(
            item["state"].get("finished_at_utc")
            or item["state"].get("updated_at_utc")
            or item["state"].get("started_at_utc")
            or ""
        ),
        reverse=True,
    )
    return candidates[0]["state"]


def load_locked_diagnostic_trades(results_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    batch = select_locked_batch(results_root)
    run_ids = {
        str(case["pair"]): str(case["result"]["run_id"])
        for case in batch["cases"]
    }

    # Reuse the audited base parser, but expose only the exact ten run folders
    # from the selected coherent batch through a temporary view directory.
    # This avoids any dependence on glob order when duplicate results exist.
    import tempfile
    import os

    with tempfile.TemporaryDirectory(prefix="hixton-cohort-") as tmp:
        view = Path(tmp)
        for pair, run_id in run_ids.items():
            source = results_root / run_id
            if not source.is_dir():
                raise RuntimeError(f"Locked batch {batch['batch_id']}: missing run folder {run_id} for {pair}")
            target = view / run_id
            try:
                os.symlink(source, target, target_is_directory=True)
            except OSError:
                # Windows may deny symlink creation. Fall back to a lightweight
                # directory containing hardlinks/copies only for the files read
                # by the parser.
                target.mkdir(parents=True, exist_ok=True)
                for src in source.iterdir():
                    if src.name == "experiment-result.json" or src.name.startswith("backtest-result-") and src.suffix == ".zip":
                        dst = target / src.name
                        try:
                            os.link(src, dst)
                        except OSError:
                            dst.write_bytes(src.read_bytes())
        rows = base.load_diagnostic_trades(view)

    per_pair = {pair: 0 for pair in base.PAIRS}
    for row in rows:
        per_pair[str(row["pair"])] += 1

    if per_pair != EXPECTED_PAIR_TRADES:
        raise RuntimeError(
            "Locked diagnostic cohort does not match the preregistered V1 evidence set. "
            f"Expected {EXPECTED_PAIR_TRADES}, got {per_pair}."
        )
    if len(rows) != EXPECTED_TOTAL_TRADES:
        raise RuntimeError(
            f"Locked diagnostic cohort must contain exactly {EXPECTED_TOTAL_TRADES} trades, got {len(rows)}."
        )

    metadata = {
        "batch_id": batch.get("batch_id"),
        "batch_fingerprint": batch.get("batch_fingerprint"),
        "finished_at_utc": batch.get("finished_at_utc"),
        "run_ids": run_ids,
        "pair_trade_counts": per_pair,
        "total_trades": len(rows),
    }
    return rows, metadata
