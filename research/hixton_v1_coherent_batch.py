from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import zipfile
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

# These values were committed before the accidental fresh STARTBOT run in
# research/reports/hixton_v1_causal/coin_summary.csv at 14580e6.  They are used
# only as a provenance fingerprint to recover the original diagnostic evidence
# when old copies do not contain _BATCHES metadata.
EXPECTED_PAIR_EVIDENCE = {
    "BTC/USDT": {"net_pnl": -149.15657177, "gross_pnl": 65.65059660000021, "fees": 214.8071683352, "loss_damage": 512.7834997, "winner_profit": 363.62692793, "losers": 484},
    "ETH/USDT": {"net_pnl": -93.63737592999999, "gross_pnl": 114.55438200000022, "fees": 208.191757824, "loss_damage": 613.63360497, "winner_profit": 519.99622904, "losers": 454},
    "SOL/USDT": {"net_pnl": -57.09453484, "gross_pnl": 155.5210400000001, "fees": 212.61557484, "loss_damage": 786.34676332, "winner_profit": 729.25222848, "losers": 438},
    "XRP/USDT": {"net_pnl": -46.15740648, "gross_pnl": 153.64634000000015, "fees": 199.80374648, "loss_damage": 684.48828268, "winner_profit": 638.3308762, "losers": 444},
    "BNB/USDT": {"net_pnl": -170.06360396, "gross_pnl": 17.04621999999988, "fees": 187.10982396, "loss_damage": 507.8592431, "winner_profit": 337.79563914, "losers": 417},
    "DOGE/USDT": {"net_pnl": -49.65728444, "gross_pnl": 157.80886000000015, "fees": 207.46614444, "loss_damage": 778.79744788, "winner_profit": 729.14016344, "losers": 452},
    "LINK/USDT": {"net_pnl": -130.64238516, "gross_pnl": 85.65947999999997, "fees": 216.30186516, "loss_damage": 851.28389264, "winner_profit": 720.64150748, "losers": 465},
    "TRX/USDT": {"net_pnl": -37.225370180000006, "gross_pnl": 214.04834600000004, "fees": 251.273716236, "loss_damage": 414.67258183, "winner_profit": 377.44721165, "losers": 543},
    "LTC/USDT": {"net_pnl": -172.0374509, "gross_pnl": -37.78358999999993, "fees": 134.2538609, "loss_damage": 479.96802458, "winner_profit": 307.93057368, "losers": 297},
    "BCH/USDT": {"net_pnl": -170.6423166, "gross_pnl": 20.91209999999999, "fees": 191.5544166, "loss_damage": 705.5332596, "winner_profit": 534.890943, "losers": 423},
}
FLOAT_TOLERANCE = 1e-6


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
    payload = [
        (
            str(row["pair"]),
            int(row["open_timestamp"]),
            int(row["close_timestamp"]),
            round(float(row["open_rate"]), 12),
            round(float(row["close_rate"]), 12),
            round(float(row["profit_abs"]), 12),
        )
        for row in sorted(
            rows,
            key=lambda r: (
                str(r["pair"]),
                int(r["open_timestamp"]),
                int(r["close_timestamp"]),
            ),
        )
    ]
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _trade_signature(pair: str, trades: list[dict[str, Any]]) -> str:
    payload = [
        (
            pair,
            int(trade["open_timestamp"]),
            int(trade["close_timestamp"]),
            round(float(trade["open_rate"]), 12),
            round(float(trade["close_rate"]), 12),
            round(float(trade["profit_abs"]), 12),
        )
        for trade in trades
    ]
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _run_metrics(trades: list[dict[str, Any]]) -> dict[str, float | int]:
    net_pnl = sum(float(trade["profit_abs"]) for trade in trades)
    gross_pnl = 0.0
    fees = 0.0
    loss_damage = 0.0
    winner_profit = 0.0
    losers = 0
    for trade in trades:
        open_rate = float(trade["open_rate"])
        close_rate = float(trade["close_rate"])
        amount = float(trade["amount"])
        profit_abs = float(trade["profit_abs"])
        fee_open = float(trade.get("fee_open") or 0.0)
        fee_close = float(trade.get("fee_close") or 0.0)
        gross_pnl += amount * (close_rate - open_rate)
        fees += amount * open_rate * fee_open + amount * close_rate * fee_close
        if profit_abs < 0:
            losers += 1
            loss_damage += -profit_abs
        elif profit_abs > 0:
            winner_profit += profit_abs
    return {
        "trades": len(trades),
        "net_pnl": net_pnl,
        "gross_pnl": gross_pnl,
        "fees": fees,
        "loss_damage": loss_damage,
        "winner_profit": winner_profit,
        "losers": losers,
    }


def _matches_preregistered_evidence(pair: str, metrics: dict[str, float | int]) -> bool:
    if int(metrics["trades"]) != EXPECTED_PAIR_TRADES[pair]:
        return False
    expected = EXPECTED_PAIR_EVIDENCE[pair]
    if int(metrics["losers"]) != int(expected["losers"]):
        return False
    for key in ("net_pnl", "gross_pnl", "fees", "loss_damage", "winner_profit"):
        if not math.isclose(
            float(metrics[key]),
            float(expected[key]),
            rel_tol=0.0,
            abs_tol=FLOAT_TOLERANCE,
        ):
            return False
    return True


def _read_legacy_run(experiment_path: Path) -> dict[str, Any] | None:
    try:
        experiment_result = json.loads(experiment_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    experiment = experiment_result.get("experiment") or {}
    identity = experiment_result.get("test_identity") or {}
    pair = str(experiment_result.get("pair") or "")
    if experiment.get("experiment_id") != base.EXPERIMENT_ID:
        return None
    if identity.get("strategy_sha256") != base.STRATEGY_SHA256:
        return None
    if pair not in base.PAIRS:
        return None

    zips = list(experiment_path.parent.glob("backtest-result-*.zip"))
    if len(zips) != 1:
        return None
    try:
        with zipfile.ZipFile(zips[0]) as archive:
            result_names = [
                name
                for name in archive.namelist()
                if name.endswith(".json")
                and "_config" not in name
                and not name.startswith("audit/")
            ]
            if len(result_names) != 1:
                return None
            payload = json.loads(archive.read(result_names[0]))
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError):
        return None

    strategy = payload.get("strategy", {}).get("CompressionBreakout250")
    if not isinstance(strategy, dict) or not isinstance(strategy.get("trades"), list):
        return None
    trades = strategy["trades"]
    metrics = _run_metrics(trades)
    return {
        "pair": pair,
        "run_id": experiment_path.parent.name,
        "metrics": metrics,
        "trade_signature": _trade_signature(pair, trades),
    }


def _reconstruct_preregistered_legacy_batch(results_root: Path) -> dict[str, Any]:
    by_pair: dict[str, list[dict[str, Any]]] = {pair: [] for pair in base.PAIRS}
    inspected = 0
    for experiment_path in results_root.glob("*/experiment-result.json"):
        candidate = _read_legacy_run(experiment_path)
        if candidate is None:
            continue
        inspected += 1
        pair = str(candidate["pair"])
        if _matches_preregistered_evidence(pair, candidate["metrics"]):
            by_pair[pair].append(candidate)

    missing = [pair for pair in base.PAIRS if not by_pair[pair]]
    if missing:
        raise RuntimeError(
            "No complete preregistered legacy evidence cohort could be reconstructed. "
            f"Missing exact evidence matches for {missing}; inspected_valid_runs={inspected}."
        )

    selected: dict[str, dict[str, Any]] = {}
    for pair in base.PAIRS:
        candidates = by_pair[pair]
        signatures = {str(item["trade_signature"]) for item in candidates}
        if len(signatures) != 1:
            raise RuntimeError(
                f"Multiple legacy runs match the preregistered summary for {pair} "
                "but their trade content differs. Manual provenance review is required."
            )
        selected[pair] = sorted(candidates, key=lambda item: str(item["run_id"]))[0]

    fingerprint_payload = [
        (pair, selected[pair]["trade_signature"])
        for pair in base.PAIRS
    ]
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "batch_id": "legacy-reconstructed-preregistered-v1",
        "batch_fingerprint": fingerprint,
        "years": 3,
        "failed_cases": 0,
        "finished_at_utc": None,
        "plan": {
            "strategy_sha256": base.STRATEGY_SHA256,
            "source_commit": "legacy-evidence-reconstruction",
        },
        "cases": [
            {
                "pair": pair,
                "status": "reused",
                "result": {"run_id": selected[pair]["run_id"]},
            }
            for pair in base.PAIRS
        ],
        "selection_rule": "reconstructed from preregistered per-pair V1 evidence metrics; duplicate matches must have identical trade content",
    }


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
        try:
            legacy_batch = _reconstruct_preregistered_legacy_batch(results_root)
            rows = _load_exact_batch_rows(results_root, legacy_batch)
        except RuntimeError as exc:
            details = "; ".join(rejected[-5:]) if rejected else "no usable _BATCHES metadata"
            raise RuntimeError(
                "No complete 6328-trade diagnostic evidence cohort was found. "
                "The causal analysis refuses to mix or guess standalone runs. "
                f"Batch check: {details}. Legacy reconstruction: {exc}"
            ) from exc
        counts = _pair_counts(rows)
        if counts != EXPECTED_PAIR_TRADES or len(rows) != EXPECTED_TOTAL_TRADES:
            raise RuntimeError(
                "Legacy evidence reconstruction did not produce the exact 6328-trade contract. "
                f"counts={counts}, total={len(rows)}"
            )
        evidence_matches.append((legacy_batch, rows, _cohort_signature(rows)))

    signatures = {sig for _, _, sig in evidence_matches}
    if len(signatures) > 1:
        ids = [str(batch.get("batch_id")) for batch, _, _ in evidence_matches]
        raise RuntimeError(
            "Multiple complete 6328-trade diagnostic cohorts exist but their trade content differs. "
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
        "selection_rule": batch.get("selection_rule")
        or "single coherent 10-run batch; diagnostic strategy hash; exact preregistered 6328 trade counts; identical-content duplicates allowed",
    }
    return rows, metadata
