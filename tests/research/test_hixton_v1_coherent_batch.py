from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

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


def _write_batch(root: Path, *, source_commit: str, complete: bool = True) -> None:
    cases = []
    for index, pair in enumerate(module.base.PAIRS):
        cases.append(
            {
                "pair": pair,
                "status": "completed" if complete or index else "running",
                "result": {"run_id": f"run-{index}"},
            }
        )
    state = {
        "batch_id": "batch-test",
        "years": 3,
        "failed_cases": 0,
        "finished_at_utc": "2026-08-30T18:00:00+00:00",
        "plan": {
            "strategy_sha256": module.base.STRATEGY_SHA256,
            "source_commit": source_commit,
        },
        "cases": cases,
    }
    folder = root / "_BATCHES" / "batch-test"
    folder.mkdir(parents=True)
    (folder / "batch-result.json").write_text(json.dumps(state), encoding="utf-8")


def test_expected_trade_contract_is_6328() -> None:
    assert module.EXPECTED_TOTAL_TRADES == 6328
    assert module.EXPECTED_PAIR_TRADES["XRP/USDT"] == 624
    assert module.EXPECTED_PAIR_TRADES["DOGE/USDT"] == 648


def test_selector_accepts_only_locked_source_commit(tmp_path: Path) -> None:
    _write_batch(tmp_path, source_commit=module.EXPECTED_SOURCE_COMMIT)
    selected = module.select_locked_batch(tmp_path)
    assert selected["batch_id"] == "batch-test"


def test_selector_rejects_other_source_commit(tmp_path: Path) -> None:
    _write_batch(tmp_path, source_commit="14580e694271d3dfa1b3ab3d93d11f3dcc56ff4c")
    try:
        module.select_locked_batch(tmp_path)
    except RuntimeError as exc:
        assert "refuses to mix" in str(exc)
    else:
        raise AssertionError("Expected fail-closed rejection")


def test_selector_rejects_incomplete_batch(tmp_path: Path) -> None:
    _write_batch(tmp_path, source_commit=module.EXPECTED_SOURCE_COMMIT, complete=False)
    try:
        module.select_locked_batch(tmp_path)
    except RuntimeError as exc:
        assert "refuses to mix" in str(exc)
    else:
        raise AssertionError("Expected fail-closed rejection")
