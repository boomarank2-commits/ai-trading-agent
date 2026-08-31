from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

import hixton_v1_coherent_batch as cohort


def _load_exact_batch_rows_windows_safe(
    results_root: Path,
    batch: dict[str, Any],
) -> list[dict[str, Any]]:
    """Load an exact cohort without directory symlinks.

    The caller commonly passes a relative results_root.  A directory symlink
    created from that relative path inside TemporaryDirectory points at the
    wrong location on Windows.  Copy only the two audited input artifacts per
    run into an isolated absolute temp view instead.
    """
    run_ids = {
        str(case["pair"]): str(case["result"]["run_id"])
        for case in batch["cases"]
    }
    root = results_root.resolve()

    with tempfile.TemporaryDirectory(prefix="hixton-cohort-") as tmp:
        view = Path(tmp)
        for pair, run_id in run_ids.items():
            source = (root / run_id).resolve()
            if not source.is_dir():
                raise RuntimeError(
                    f"Batch {batch.get('batch_id')}: missing run folder {run_id} for {pair}"
                )
            try:
                source.relative_to(root)
            except ValueError as exc:
                raise RuntimeError(
                    f"Batch {batch.get('batch_id')}: run folder escaped results root: {run_id}"
                ) from exc

            target = view / run_id
            target.mkdir(parents=True, exist_ok=True)
            copied = 0
            for src in source.iterdir():
                is_result_zip = (
                    src.name.startswith("backtest-result-") and src.suffix == ".zip"
                )
                if src.name != "experiment-result.json" and not is_result_zip:
                    continue
                shutil.copy2(src, target / src.name)
                copied += 1
            if copied < 2:
                raise RuntimeError(
                    f"Batch {batch.get('batch_id')}: incomplete audited run files for {pair} ({run_id})"
                )

        return cohort.base.load_diagnostic_trades(view)


# The selection functions in hixton_v1_coherent_batch resolve this helper from
# their module globals at call time.  Replacing only this internal loader keeps
# all existing fail-closed evidence/fingerprint logic unchanged.
cohort._load_exact_batch_rows = _load_exact_batch_rows_windows_safe

load_locked_diagnostic_trades = cohort.load_locked_diagnostic_trades
select_locked_batch = cohort.select_locked_batch
EXPECTED_PAIR_TRADES = cohort.EXPECTED_PAIR_TRADES
EXPECTED_TOTAL_TRADES = cohort.EXPECTED_TOTAL_TRADES
EXPECTED_PAIR_EVIDENCE = cohort.EXPECTED_PAIR_EVIDENCE
