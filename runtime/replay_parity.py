"""Compare captured paper decisions with a historical replay decision stream."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL {path}:{line_no}") from exc
            if isinstance(value, dict):
                rows.append(value)
    return rows


def compare_signal_decisions(paper_path: Path, replay_path: Path) -> dict[str, Any]:
    paper_rows = [
        row
        for row in _jsonl(paper_path)
        if row.get("type") == "strategy_signal_decision"
    ]
    replay = _jsonl(replay_path)
    replay_by_key = {
        (row.get("pair"), row.get("candle_open")): row
        for row in replay
        if row.get("pair") and row.get("candle_open")
    }

    results: dict[str, dict[str, Any]] = {}
    all_mismatches: list[dict[str, Any]] = []
    total_missing = 0
    total_compared = 0
    for kind, paper_field, replay_field in (
        ("entry", "enter_long", "enter_candidate"),
        ("exit", "exit_long", "exit_candidate"),
    ):
        subset = [row for row in paper_rows if row.get("kind") == kind]
        compared = 0
        missing = 0
        mismatches: list[dict[str, Any]] = []
        for row in subset:
            key = (row.get("pair"), row.get("candle_open_utc"))
            other = replay_by_key.get(key)
            if other is None:
                missing += 1
                continue
            compared += 1
            expected = bool(row.get(paper_field))
            actual = bool(other.get(replay_field))
            if expected != actual:
                mismatches.append(
                    {
                        "pair": key[0],
                        "candle_open": key[1],
                        "field": paper_field,
                        "paper": expected,
                        "replay": actual,
                    }
                )
        results[kind] = {
            "paper_rows": len(subset),
            "compared_rows": compared,
            "missing_replay_rows": missing,
            "mismatches": len(mismatches),
            "parity": compared > 0 and not mismatches and missing == 0,
        }
        total_compared += compared
        total_missing += missing
        all_mismatches.extend(mismatches)

    return {
        "paper_signal_rows": len(paper_rows),
        "replay_signal_rows": len(replay),
        "compared_rows": total_compared,
        "missing_replay_rows": total_missing,
        "signal_mismatches": len(all_mismatches),
        "signal_parity": results["entry"]["parity"] and results["exit"]["parity"],
        "entry": results["entry"],
        "exit": results["exit"],
        "mismatch_examples": all_mismatches[:20],
    }


def compare_runtime_confirmations(paper_path: Path, replay_path: Path) -> dict[str, Any]:
    paper = [
        row
        for row in _jsonl(paper_path)
        if row.get("type") == "runtime_entry_confirmation"
    ]
    replay_candidates = [row for row in _jsonl(replay_path) if row.get("enter_candidate")]
    by_pair_paper: dict[str, list[bool]] = defaultdict(list)
    by_pair_replay: dict[str, list[bool]] = defaultdict(list)
    for row in paper:
        by_pair_paper[str(row.get("pair"))].append(bool(row.get("allowed")))
    for row in replay_candidates:
        by_pair_replay[str(row.get("pair"))].append(bool(row.get("entry_allowed")))
    pairs = sorted(set(by_pair_paper) | set(by_pair_replay))
    details: dict[str, Any] = {}
    all_match = bool(pairs)
    for pair in pairs:
        paper_sequence = by_pair_paper[pair]
        replay_sequence = by_pair_replay[pair]
        same = paper_sequence == replay_sequence
        details[pair] = {
            "paper_count": len(paper_sequence),
            "replay_count": len(replay_sequence),
            "same_allowed_sequence": same,
        }
        all_match = all_match and same
    return {
        "risk_confirmation_parity": all_match,
        "note": (
            "confirmation comparison is order-based per pair because paper callback wall-clock "
            "times can differ from candle-close timestamps; signal parity is the stronger exact "
            "pair+candle check"
        ),
        "pairs": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = {
        "signals": compare_signal_decisions(args.paper, args.replay),
        "risk": compare_runtime_confirmations(args.paper, args.replay),
    }
    raw = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8", newline="\n")
    print(raw, end="")
    return 0 if result["signals"]["signal_parity"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
