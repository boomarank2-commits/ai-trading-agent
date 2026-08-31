from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))
MODULE_PATH = RESEARCH / "hixton_v1_coherent_batch.py"
spec = importlib.util.spec_from_file_location("hixton_v1_coherent_batch", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_batch(root: Path, *, source_commit: str, complete: bool = True, batch_id: str = "batch-test") -> None:
    cases = []
    for index, pair in enumerate(module.base.PAIRS):
        cases.append(
            {
                "pair": pair,
                "status": "completed" if complete or index else "running",
                "result": {"run_id": f"{batch_id}-run-{index}"},
            }
        )
    state = {
        "batch_id": batch_id,
        "years": 3,
        "failed_cases": 0,
        "finished_at_utc": "2026-08-30T18:00:00+00:00",
        "plan": {
            "strategy_sha256": module.base.STRATEGY_SHA256,
            "source_commit": source_commit,
        },
        "cases": cases,
    }
    folder = root / "_BATCHES" / batch_id
    folder.mkdir(parents=True)
    (folder / "batch-result.json").write_text(json.dumps(state), encoding="utf-8")


def _fake_rows(delta: int = 0) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    counter = 0
    for pair, count in module.EXPECTED_PAIR_TRADES.items():
        adjusted = count + (delta if pair == "XRP/USDT" else 0)
        for _ in range(adjusted):
            rows.append(
                {
                    "pair": pair,
                    "open_timestamp": counter,
                    "close_timestamp": counter + 1,
                    "open_rate": 1.0,
                    "close_rate": 1.01,
                    "profit_abs": 0.1,
                }
            )
            counter += 2
    return rows


def test_expected_trade_contract_is_6328() -> None:
    assert module.EXPECTED_TOTAL_TRADES == 6328
    assert module.EXPECTED_PAIR_TRADES["XRP/USDT"] == 624
    assert module.EXPECTED_PAIR_TRADES["DOGE/USDT"] == 648


def test_preregistered_evidence_fingerprint_accepts_committed_btc_summary() -> None:
    expected = module.EXPECTED_PAIR_EVIDENCE["BTC/USDT"]
    metrics = {
        "trades": module.EXPECTED_PAIR_TRADES["BTC/USDT"],
        "net_pnl": expected["net_pnl"],
        "gross_pnl": expected["gross_pnl"],
        "fees": expected["fees"],
        "loss_damage": expected["loss_damage"],
        "winner_profit": expected["winner_profit"],
        "losers": expected["losers"],
    }
    assert module._matches_preregistered_evidence("BTC/USDT", metrics)


def test_preregistered_evidence_fingerprint_rejects_fresh_run_drift() -> None:
    expected = module.EXPECTED_PAIR_EVIDENCE["BTC/USDT"]
    metrics = {
        "trades": module.EXPECTED_PAIR_TRADES["BTC/USDT"],
        "net_pnl": float(expected["net_pnl"]) - 0.19,
        "gross_pnl": expected["gross_pnl"],
        "fees": expected["fees"],
        "loss_damage": expected["loss_damage"],
        "winner_profit": expected["winner_profit"],
        "losers": expected["losers"],
    }
    assert not module._matches_preregistered_evidence("BTC/USDT", metrics)


def test_selector_does_not_require_final_branch_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_batch(tmp_path, source_commit="older-diagnostic-commit")
    monkeypatch.setattr(module, "_load_exact_batch_rows", lambda *_: _fake_rows())
    selected, rows, _ = module.select_locked_batch(tmp_path)
    assert selected["batch_id"] == "batch-test"
    assert len(rows) == 6328


def test_selector_rejects_wrong_trade_cohort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_batch(tmp_path, source_commit="anything")
    monkeypatch.setattr(module, "_load_exact_batch_rows", lambda *_: _fake_rows(delta=1))
    with pytest.raises(RuntimeError, match="No complete 6328-trade"):
        module.select_locked_batch(tmp_path)


def test_selector_rejects_different_complete_cohorts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_batch(tmp_path, source_commit="a", batch_id="batch-a")
    _write_batch(tmp_path, source_commit="b", batch_id="batch-b")
    rows_a = _fake_rows()
    rows_b = _fake_rows()
    rows_b[0] = {**rows_b[0], "profit_abs": 0.2}

    def fake_loader(_root: Path, batch: dict[str, object]) -> list[dict[str, object]]:
        return rows_a if batch["batch_id"] == "batch-a" else rows_b

    monkeypatch.setattr(module, "_load_exact_batch_rows", fake_loader)
    with pytest.raises(RuntimeError, match="trade content differs"):
        module.select_locked_batch(tmp_path)


def test_selector_rejects_incomplete_batch(tmp_path: Path) -> None:
    _write_batch(tmp_path, source_commit="anything", complete=False)
    with pytest.raises(RuntimeError, match="refuses to mix"):
        module.select_locked_batch(tmp_path)
