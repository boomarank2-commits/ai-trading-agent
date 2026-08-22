from __future__ import annotations

import csv
import hashlib
import subprocess
from pathlib import Path

import pytest

from runtime.backtest_experiment import (
    DETAILED_EXPERIMENT_FIELDS,
    build_test_identity,
    config_contract,
    find_git_strategy_source,
    registered_experiment,
    strategy_hashes,
)


def test_exact_parent_strategy_can_be_recovered_from_git_history(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    strategy = repo / "runtime" / "user_data" / "strategies" / "Candidate.py"
    strategy.parent.mkdir(parents=True)
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
    )
    parent_source = b"VALUE = 1\n"
    strategy.write_bytes(parent_source)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "parent"],
        check=True,
        capture_output=True,
    )
    strategy.write_bytes(b"VALUE = 2\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "candidate"],
        check=True,
        capture_output=True,
    )

    recovered = find_git_strategy_source(
        repo,
        strategy,
        hashlib.sha256(parent_source).hexdigest(),
    )

    assert recovered == parent_source
    assert find_git_strategy_source(repo, strategy, "f" * 64) is None


def test_logic_hash_ignores_comments_docstrings_and_version_labels() -> None:
    first = b'''"""Version V1."""\nSTRATEGY_VERSION = "V1"\nVALUE = 7\n'''
    second = b'''"""Version V999."""\n# cosmetic only\nSTRATEGY_VERSION = "V999"\nVALUE = 7\n'''

    first_hashes = strategy_hashes(first)
    second_hashes = strategy_hashes(second)

    assert first_hashes["strategy_sha256"] != second_hashes["strategy_sha256"]
    assert first_hashes["strategy_logic_sha256"] == second_hashes["strategy_logic_sha256"]


def test_logic_hash_changes_for_material_code_change() -> None:
    first = strategy_hashes(b"VALUE = 7\n")
    second = strategy_hashes(b"VALUE = 8\n")

    assert first["strategy_logic_sha256"] != second["strategy_logic_sha256"]


def test_test_fingerprint_covers_logic_pair_period_and_safe_config() -> None:
    source = b"VALUE = 7\n"
    base = {"strategy": "CompressionBreakout250", "dry_run": True}
    with_secret_change = {
        **base,
        "api_server": {"password": "different-secret"},
    }
    first = build_test_identity(
        strategy_source=source,
        pair="BTC/USDT",
        years=3,
        config=config_contract(base),
    )
    secret_only = build_test_identity(
        strategy_source=source,
        pair="BTC/USDT",
        years=3,
        config=config_contract(with_secret_change),
    )
    other_pair = build_test_identity(
        strategy_source=source,
        pair="ETH/USDT",
        years=3,
        config=config_contract(base),
    )

    assert first["test_fingerprint"] == secret_only["test_fingerprint"]
    assert first["test_fingerprint"] != other_pair["test_fingerprint"]
    assert "api_server" not in first["material"]["config_contract"]


def _write_ledger(path: Path, strategy_hash: str) -> None:
    fields = [*DETAILED_EXPERIMENT_FIELDS]
    parent = {field: "documented" for field in fields}
    parent.update(
        {
            "experiment_id": "PARENT",
            "parent_experiment_id": "",
            "strategy_version": "V1",
            "strategy_hash": "a" * 64,
        }
    )
    candidate = {field: "documented" for field in fields}
    candidate.update(
        {
            "experiment_id": "CANDIDATE",
            "parent_experiment_id": "PARENT",
            "strategy_version": "V2",
            "strategy_hash": strategy_hash,
        }
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows([parent, candidate])


def test_exact_strategy_must_have_one_detailed_registered_lineage(
    tmp_path: Path,
) -> None:
    strategy_hash = "b" * 64
    ledger = tmp_path / "ledger.csv"
    _write_ledger(ledger, strategy_hash)

    experiment, lineage = registered_experiment(ledger, strategy_hash)

    assert experiment["experiment_id"] == "CANDIDATE"
    assert [row["experiment_id"] for row in lineage] == ["PARENT", "CANDIDATE"]
    with pytest.raises(ValueError, match="exactly one"):
        registered_experiment(ledger, "c" * 64)
