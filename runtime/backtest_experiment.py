"""Fail-closed experiment identity and lineage for local UI backtests.

A raw strategy hash alone is not enough: changing only comments, docstrings or
``STRATEGY_VERSION`` must not make an otherwise identical test look new.  The
logic hash therefore fingerprints the normalized Python AST.  A material test
fingerprint combines that logic with the pair, period and frozen backtest
protocol.  Existing fingerprints are blocked before any download or result
directory is created.
"""

from __future__ import annotations

import ast
import csv
import difflib
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

BACKTEST_PROTOCOL_VERSION = "freqtrade-2026.7-ui-fixed-v1"
STRATEGY_NAME = "CompressionBreakout250"
PROTOCOL_CONTRACT = {
    "fee_per_order_side": 0.002,
    "timeframe": "15m",
    "timeframe_detail": "1m",
    "required_timeframes": ["15m", "1m", "1h", "4h"],
    "enable_protections": True,
    "dry_run_wallet_usdt": 250,
    "cache": "none",
    "export": "trades",
    "trading_mode": "spot",
}

DETAILED_EXPERIMENT_FIELDS = (
    "experiment_id",
    "parent_experiment_id",
    "strategy_version",
    "strategy_hash",
    "hypothesis",
    "change_summary",
    "acceptance_criteria",
    "result_summary",
    "decision",
    "lessons",
    "next_experiment",
)

_CONFIG_FIELDS = (
    "strategy",
    "timeframe",
    "max_open_trades",
    "stake_currency",
    "stake_amount",
    "available_capital",
    "tradable_balance_ratio",
    "dry_run",
    "dry_run_wallet",
    "trading_mode",
    "margin_mode",
    "position_adjustment_enable",
    "max_entry_position_adjustment",
    "minimal_roi",
    "stoploss",
    "trailing_stop",
    "use_exit_signal",
    "exit_profit_only",
    "ignore_roi_if_entry_signal",
    "unfilledtimeout",
    "order_types",
    "order_time_in_force",
)


class _LogicNormalizer(ast.NodeTransformer):
    """Remove metadata that cannot change Python trading behavior."""

    def visit_Expr(self, node: ast.Expr) -> ast.AST | None:
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return None
        return self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> ast.AST | None:
        if any(
            isinstance(target, ast.Name) and target.id == "STRATEGY_VERSION"
            for target in node.targets
        ):
            return None
        return self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST | None:
        if isinstance(node.target, ast.Name) and node.target.id == "STRATEGY_VERSION":
            return None
        return self.generic_visit(node)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def strategy_hashes(source: bytes) -> dict[str, str]:
    raw_hash = hashlib.sha256(source).hexdigest()
    try:
        tree = ast.parse(source.decode("utf-8"))
        normalized = _LogicNormalizer().visit(tree)
        ast.fix_missing_locations(normalized)
        logic = ast.dump(normalized, annotate_fields=True, include_attributes=False)
        logic_hash = hashlib.sha256(logic.encode("utf-8")).hexdigest()
    except (SyntaxError, UnicodeDecodeError, ValueError):
        logic_hash = raw_hash
    return {"strategy_sha256": raw_hash, "strategy_logic_sha256": logic_hash}


def config_contract(config: dict[str, Any]) -> dict[str, Any]:
    selected = {field: config.get(field) for field in _CONFIG_FIELDS}
    exchange = config.get("exchange")
    if not isinstance(exchange, dict):
        exchange = {}
    selected["exchange"] = {
        "name": exchange.get("name"),
        "pair_whitelist": exchange.get("pair_whitelist"),
        "pair_blacklist": exchange.get("pair_blacklist"),
    }
    selected["pairlists"] = config.get("pairlists")
    return selected


def load_config_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"config must be a JSON object: {path}")
    return config_contract(payload)


def build_test_identity(
    *,
    strategy_source: bytes,
    pair: str,
    years: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    hashes = strategy_hashes(strategy_source)
    material = {
        "schema_version": 1,
        "protocol_version": BACKTEST_PROTOCOL_VERSION,
        "strategy_logic_sha256": hashes["strategy_logic_sha256"],
        "strategy_name": STRATEGY_NAME,
        "pair": pair,
        "years": years,
        "protocol": PROTOCOL_CONTRACT,
        "config_contract": config,
    }
    return {
        **hashes,
        "test_fingerprint": canonical_sha256(material),
        "material": material,
    }


def load_trial_ledger(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("trial ledger has no header")
        rows = [{key: str(value or "").strip() for key, value in row.items()} for row in reader]
    return list(reader.fieldnames), rows


def registered_experiment(
    path: Path, strategy_hash: str
) -> tuple[dict[str, str], list[dict[str, str]]]:
    header, rows = load_trial_ledger(path)
    missing = [field for field in DETAILED_EXPERIMENT_FIELDS if field not in header]
    if missing:
        raise ValueError("trial ledger lacks detailed fields: " + ", ".join(missing))
    matches = [row for row in rows if row.get("strategy_hash") == strategy_hash]
    if len(matches) != 1:
        raise ValueError(
            f"strategy hash {strategy_hash[:12]} must have exactly one trial-ledger entry; "
            f"found {len(matches)}"
        )
    experiment = matches[0]
    required = (
        "experiment_id",
        "strategy_version",
        "hypothesis",
        "change_summary",
        "acceptance_criteria",
        "decision",
        "lessons",
        "next_experiment",
    )
    blank = [field for field in required if not experiment.get(field)]
    if blank:
        raise ValueError(
            f"experiment {experiment.get('experiment_id') or '?'} lacks: {', '.join(blank)}"
        )
    lineage = experiment_lineage(rows, experiment["experiment_id"])
    if len(lineage) > 1:
        parent = lineage[-2]
        parent_open = parent.get("decision", "").upper().startswith("PLANNED")
        parent_unrun = parent.get("result_summary", "").lower().startswith("not run")
        if parent_open or parent_unrun:
            raise ValueError(
                f"parent experiment {parent['experiment_id']} has no final result decision"
            )
    return experiment, lineage


def experiment_lineage(rows: list[dict[str, str]], experiment_id: str) -> list[dict[str, str]]:
    by_id = {row.get("experiment_id", ""): row for row in rows}
    lineage: list[dict[str, str]] = []
    seen: set[str] = set()
    current = experiment_id
    while current:
        if current in seen:
            raise ValueError(f"cycle in trial ledger at {current}")
        seen.add(current)
        row = by_id.get(current)
        if row is None:
            raise ValueError(f"unknown trial-ledger experiment: {current}")
        lineage.append({field: row.get(field, "") for field in DETAILED_EXPERIMENT_FIELDS})
        current = row.get("parent_experiment_id", "")
    lineage.reverse()
    return lineage


def find_archived_strategy_source(results_root: Path, strategy_hash: str) -> bytes | None:
    if not strategy_hash or not results_root.is_dir():
        return None
    for archive_path in sorted(results_root.glob("*/*.zip"), reverse=True):
        try:
            with ZipFile(archive_path) as archive:
                for name in archive.namelist():
                    if not name.endswith(f"_{STRATEGY_NAME}.py"):
                        continue
                    source = archive.read(name)
                    if hashlib.sha256(source).hexdigest() == strategy_hash:
                        return source
        except (BadZipFile, OSError):
            continue
    return None


def find_git_strategy_source(
    repo_root: Path,
    strategy_path: Path,
    strategy_hash: str,
) -> bytes | None:
    """Return only a versioned strategy blob matching the exact registered hash."""
    if not strategy_hash:
        return None
    try:
        root = repo_root.resolve()
        relative_path = strategy_path.resolve().relative_to(root).as_posix()
    except ValueError:
        return None

    safe_directory = str(root).replace("\\", "/")
    history = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={safe_directory}",
            "-C",
            str(root),
            "log",
            "--format=%H",
            "--",
            relative_path,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    if history.returncode != 0:
        return None

    for commit in history.stdout.splitlines():
        commit = commit.strip()
        if len(commit) != 40:
            continue
        blob = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={safe_directory}",
                "-C",
                str(root),
                "show",
                f"{commit}:{relative_path}",
            ],
            capture_output=True,
            check=False,
            timeout=5,
        )
        if (
            blob.returncode == 0
            and hashlib.sha256(blob.stdout).hexdigest() == strategy_hash
        ):
            return blob.stdout
    return None


def strategy_change_diff(parent_source: bytes | None, current_source: bytes) -> str:
    if parent_source is None:
        return "Parent strategy source is not available in the preserved archive.\n"
    parent = parent_source.decode("utf-8", errors="replace").splitlines(keepends=True)
    current = current_source.decode("utf-8", errors="replace").splitlines(keepends=True)
    return (
        "".join(
            difflib.unified_diff(
                parent,
                current,
                fromfile="parent/CompressionBreakout250.py",
                tofile="candidate/CompressionBreakout250.py",
            )
        )
        or "No source difference. This test must be blocked as a duplicate.\n"
    )


def current_git_commit(repo_root: Path) -> str | None:
    safe_directory = str(repo_root.resolve()).replace("\\", "/")
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={safe_directory}",
            "-C",
            str(repo_root),
            "rev-parse",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) == 40 else None


def build_run_plan(
    *,
    run_id: str,
    pair: str,
    years: int,
    identity: dict[str, Any],
    experiment: dict[str, str],
    lineage: list[dict[str, str]],
    source_commit: str | None,
    strategy_diff: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "experiment": {field: experiment.get(field, "") for field in DETAILED_EXPERIMENT_FIELDS},
        "lineage": lineage,
        "test_identity": identity,
        "source_commit": source_commit,
        "pair": pair,
        "years": years,
        "strategy_change_diff_sha256": hashlib.sha256(strategy_diff.encode("utf-8")).hexdigest(),
        "duplicate_policy": {
            "exact_fingerprint_reuse_allowed": False,
            "metadata_only_strategy_changes_create_new_test": False,
            "new_market_data_alone_creates_new_ui_test": False,
        },
    }
