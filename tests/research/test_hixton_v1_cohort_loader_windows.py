from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))
MODULE_PATH = RESEARCH / "hixton_v1_cohort_loader_windows.py"
spec = importlib.util.spec_from_file_location("hixton_v1_cohort_loader_windows", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_relative_results_root_is_copied_into_visible_temp_view(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = tmp_path / "results"
    cases = []
    expected_run_ids: list[str] = []
    for index, pair in enumerate(module.cohort.base.PAIRS):
        run_id = f"run-{index}"
        expected_run_ids.append(run_id)
        run_dir = results / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "experiment-result.json").write_text("{}", encoding="utf-8")
        (run_dir / "backtest-result-test.zip").write_bytes(b"zip-placeholder")
        cases.append(
            {
                "pair": pair,
                "status": "reused",
                "result": {"run_id": run_id},
            }
        )

    batch = {"batch_id": "relative-root-test", "cases": cases}
    observed: list[str] = []

    def fake_parser(view: Path) -> list[dict]:
        assert view.is_absolute()
        for run_id in expected_run_ids:
            run_dir = view / run_id
            assert (run_dir / "experiment-result.json").is_file()
            assert (run_dir / "backtest-result-test.zip").is_file()
            observed.append(run_id)
        return []

    monkeypatch.setattr(module.cohort.base, "load_diagnostic_trades", fake_parser)
    monkeypatch.chdir(tmp_path)

    rows = module._load_exact_batch_rows_windows_safe(Path("results"), batch)

    assert rows == []
    assert observed == expected_run_ids
