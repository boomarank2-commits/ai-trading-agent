"""Deterministic, fail-closed SQLite strategy registry and trial ledger."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .errors import (
    AlreadyInitializedError,
    ApprovalArtifactError,
    ArtifactError,
    ArtifactPathError,
    ArtifactVerificationError,
    DatabaseIntegrityError,
    DeploymentAuthorizationError,
    GateRejectedError,
    ManualApprovalRequired,
    NotFoundError,
    RegistryNotInitializedError,
    RiskPolicyError,
    TransitionError,
    ValidationError,
)
from .models import (
    ALLOWED_TRANSITIONS,
    MANUAL_APPROVAL_STATES,
    METRICS_GATED_STATES,
    SAFETY_STATES,
    GateCriteria,
    GateDecision,
    Lifecycle,
    RiskPolicy,
)

SCHEMA_VERSION = 4
SAMPLE_TYPES = frozenset(
    {
        "BACKTEST",
        "IN_SAMPLE",
        "VALIDATION",
        "OUT_OF_SAMPLE",
        "WALK_FORWARD",
        "HOLDOUT",
        "SHADOW",
        "PAPER",
        "CANARY",
        "PRODUCTION",
    }
)
TRIAL_STATUSES = frozenset(
    {"PLANNED", "RUNNING", "PASSED", "FAILED", "REJECTED", "CANCELLED"}
)
RESEARCH_EVIDENCE_TYPES = frozenset(
    {"BACKTEST", "VALIDATION", "OUT_OF_SAMPLE"}
)
STAGE_EVIDENCE_TYPES: dict[Lifecycle, frozenset[str]] = {
    Lifecycle.VALIDATED: RESEARCH_EVIDENCE_TYPES,
    Lifecycle.HOLDOUT_PASSED: frozenset({"HOLDOUT"}),
    # Entry into SHADOW deliberately reuses the just-passed HOLDOUT evidence.
    # Forward evidence is always collected *inside* the named active state and
    # then evaluated for the transition out of that state.
    Lifecycle.SHADOW: frozenset({"HOLDOUT"}),
    Lifecycle.PAPER: frozenset({"SHADOW"}),
    Lifecycle.CANARY: frozenset({"PAPER"}),
    Lifecycle.PRODUCTION: frozenset({"CANARY"}),
}
EVIDENCE_PREDECESSOR_STATE: dict[Lifecycle, Lifecycle] = {
    Lifecycle.VALIDATED: Lifecycle.RESEARCH,
    Lifecycle.HOLDOUT_PASSED: Lifecycle.VALIDATED,
    Lifecycle.SHADOW: Lifecycle.VALIDATED,
    Lifecycle.PAPER: Lifecycle.SHADOW,
    Lifecycle.CANARY: Lifecycle.PAPER,
    Lifecycle.PRODUCTION: Lifecycle.CANARY,
}
SAMPLE_COLLECTION_STATES: dict[str, frozenset[Lifecycle]] = {
    "HOLDOUT": frozenset({Lifecycle.VALIDATED}),
    "SHADOW": frozenset({Lifecycle.SHADOW}),
    "PAPER": frozenset({Lifecycle.PAPER}),
    "CANARY": frozenset({Lifecycle.CANARY}),
    "PRODUCTION": frozenset({Lifecycle.PRODUCTION}),
}
LIVE_STATES = frozenset({Lifecycle.CANARY, Lifecycle.PRODUCTION})
APPROVAL_FIELDS = frozenset(
    {
        "strategy",
        "version",
        "target",
        "artifact_sha256",
        "approver",
        "expires_at",
    }
)
MAX_APPROVAL_BYTES = 16 * 1024
MAX_APPROVAL_LIFETIME_SECONDS = 15 * 60
SQLITE_APPLICATION_ID = 1280590924
REQUIRED_TRIGGERS = frozenset(
    {
        "active_version_belongs_to_strategy",
        "evaluations_no_delete",
        "evaluations_no_update",
        "lifecycle_transition_is_allowed",
        "promotion_event_requires_registry_gate",
        "promotion_events_no_delete",
        "promotion_events_no_update",
        "trials_no_delete",
        "trials_no_update",
        "versions_artifact_fields_immutable",
        "versions_no_delete",
    }
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _json_dump(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"value is not valid deterministic JSON: {exc}") from exc


def _json_load(value: str, *, label: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise DatabaseIntegrityError(f"stored {label} is not valid JSON") from exc


def _clean_text(
    label: str, value: Any, *, required: bool = True, max_length: int = 4096
) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise ValidationError(f"{label} must not be empty")
    if len(cleaned) > max_length:
        raise ValidationError(f"{label} exceeds {max_length} characters")
    if any(ord(character) < 32 and character not in "\t\n\r" for character in cleaned):
        raise ValidationError(f"{label} contains control characters")
    return cleaned


def _finite_metric(label: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError(f"{label} must be a finite number")
    return result


_SCHEMA = """
PRAGMA application_id = 1280590924;
PRAGMA user_version = 4;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) STRICT;

CREATE TABLE strategies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    active_version_id INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (active_version_id) REFERENCES versions(id)
) STRICT;

CREATE TABLE versions (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id),
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    parent_version_id INTEGER REFERENCES versions(id),
    lifecycle TEXT NOT NULL DEFAULT 'IDEA' CHECK (lifecycle IN (
        'IDEA', 'RESEARCH', 'VALIDATED', 'HOLDOUT_PASSED', 'SHADOW',
        'PAPER', 'CANARY', 'PRODUCTION', 'DEGRADED', 'PAUSED'
    )),
    source_path TEXT NOT NULL,
    source_root TEXT NOT NULL CHECK (source_root IN ('candidate', 'promoted')),
    artifact_sha256 TEXT NOT NULL CHECK (
        length(artifact_sha256) = 64 AND artifact_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    artifact_size INTEGER NOT NULL CHECK (artifact_size >= 0),
    risk_policy_json TEXT NOT NULL CHECK (json_valid(risk_policy_json)),
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    UNIQUE (strategy_id, version_number),
    UNIQUE (strategy_id, source_root, artifact_sha256)
) STRICT;

CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES versions(id),
    trial_id INTEGER REFERENCES trials(id),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    sample_type TEXT NOT NULL CHECK (sample_type IN (
        'BACKTEST', 'IN_SAMPLE', 'VALIDATION', 'OUT_OF_SAMPLE', 'WALK_FORWARD',
        'HOLDOUT', 'SHADOW', 'PAPER', 'CANARY', 'PRODUCTION'
    )),
    evidence_id TEXT NOT NULL,
    dataset_sha256 TEXT CHECK (
        dataset_sha256 IS NULL OR (
            length(dataset_sha256) = 64 AND dataset_sha256 NOT GLOB '*[^0-9a-f]*'
        )
    ),
    provenance_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(provenance_json)),
    evidence_fingerprint TEXT NOT NULL CHECK (
        length(evidence_fingerprint) = 64 AND evidence_fingerprint NOT GLOB '*[^0-9a-f]*'
    ),
    net_profit REAL NOT NULL,
    profit_factor REAL NOT NULL CHECK (profit_factor >= 0),
    max_drawdown REAL NOT NULL CHECK (max_drawdown >= 0 AND max_drawdown <= 100),
    win_rate REAL NOT NULL CHECK (win_rate >= 0 AND win_rate <= 100),
    trade_count INTEGER NOT NULL CHECK (trade_count >= 0),
    avg_trade REAL NOT NULL,
    max_daily_loss_abs REAL CHECK (
        max_daily_loss_abs IS NULL OR max_daily_loss_abs >= 0
    ),
    notes TEXT NOT NULL DEFAULT '',
    recorded_at TEXT NOT NULL,
    UNIQUE (version_id, evidence_id),
    UNIQUE (version_id, evidence_fingerprint)
) STRICT;

CREATE TABLE trials (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id),
    version_id INTEGER NOT NULL REFERENCES versions(id),
    trial_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'PLANNED', 'RUNNING', 'PASSED', 'FAILED', 'REJECTED', 'CANCELLED'
    )),
    hypothesis TEXT NOT NULL DEFAULT '',
    parameters_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(parameters_json)),
    result_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(result_json)),
    recorded_at TEXT NOT NULL
) STRICT;

CREATE TABLE promotion_events (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id),
    version_id INTEGER NOT NULL REFERENCES versions(id),
    from_state TEXT NOT NULL CHECK (from_state IN (
        'IDEA', 'RESEARCH', 'VALIDATED', 'HOLDOUT_PASSED', 'SHADOW',
        'PAPER', 'CANARY', 'PRODUCTION', 'DEGRADED', 'PAUSED'
    )),
    to_state TEXT NOT NULL CHECK (to_state IN (
        'IDEA', 'RESEARCH', 'VALIDATED', 'HOLDOUT_PASSED', 'SHADOW',
        'PAPER', 'CANARY', 'PRODUCTION', 'DEGRADED', 'PAUSED'
    )),
    approved_by TEXT NOT NULL,
    manual_approval INTEGER NOT NULL CHECK (manual_approval IN (0, 1)),
    approval_file_path TEXT NOT NULL DEFAULT '',
    approval_sha256 TEXT UNIQUE CHECK (
        approval_sha256 IS NULL OR (
            length(approval_sha256) = 64 AND approval_sha256 NOT GLOB '*[^0-9a-f]*'
        )
    ),
    approval_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(approval_json)),
    evaluation_cutoff_id INTEGER NOT NULL CHECK (evaluation_cutoff_id >= 0),
    reason TEXT NOT NULL DEFAULT '',
    gate_snapshot_json TEXT NOT NULL CHECK (json_valid(gate_snapshot_json)),
    recorded_at TEXT NOT NULL,
    CHECK (
        to_state NOT IN ('CANARY', 'PRODUCTION') OR
        (
            manual_approval = 1 AND length(trim(approved_by)) > 0 AND
            lower(trim(approved_by)) NOT IN ('system', 'auto', 'automation', 'bot') AND
            length(trim(approval_file_path)) > 0 AND approval_sha256 IS NOT NULL
        )
    )
) STRICT;

CREATE INDEX idx_versions_strategy ON versions(strategy_id, version_number);
CREATE INDEX idx_evaluations_version ON evaluations(version_id, sample_type);
CREATE INDEX idx_trials_version ON trials(version_id, recorded_at);
CREATE INDEX idx_events_version ON promotion_events(version_id, recorded_at);

CREATE TRIGGER versions_artifact_fields_immutable
BEFORE UPDATE OF strategy_id, version_number, parent_version_id, source_path,
    source_root, artifact_sha256, artifact_size, risk_policy_json, metadata_json,
    created_at ON versions
BEGIN
    SELECT RAISE(ABORT, 'version artifact fields are immutable');
END;

CREATE TRIGGER versions_no_delete
BEFORE DELETE ON versions
BEGIN
    SELECT RAISE(ABORT, 'versions are append-only');
END;

CREATE TRIGGER evaluations_no_update
BEFORE UPDATE ON evaluations
BEGIN
    SELECT RAISE(ABORT, 'evaluations are append-only');
END;

CREATE TRIGGER evaluations_no_delete
BEFORE DELETE ON evaluations
BEGIN
    SELECT RAISE(ABORT, 'evaluations are append-only');
END;

CREATE TRIGGER trials_no_update
BEFORE UPDATE ON trials
BEGIN
    SELECT RAISE(ABORT, 'trials are append-only');
END;

CREATE TRIGGER trials_no_delete
BEFORE DELETE ON trials
BEGIN
    SELECT RAISE(ABORT, 'trials are append-only');
END;

CREATE TRIGGER promotion_events_no_update
BEFORE UPDATE ON promotion_events
BEGIN
    SELECT RAISE(ABORT, 'promotion events are append-only');
END;

CREATE TRIGGER promotion_events_no_delete
BEFORE DELETE ON promotion_events
BEGIN
    SELECT RAISE(ABORT, 'promotion events are append-only');
END;

CREATE TRIGGER promotion_event_requires_registry_gate
BEFORE INSERT ON promotion_events
BEGIN
    SELECT CASE WHEN _local_trader_gate_authorized() <> 1
        THEN RAISE(ABORT, 'promotion event requires registry gate authorization')
    END;
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM versions
        WHERE id = NEW.version_id
          AND strategy_id = NEW.strategy_id
          AND lifecycle = NEW.from_state
    ) THEN RAISE(ABORT, 'promotion event does not match current version state') END;
    SELECT CASE WHEN NEW.evaluation_cutoff_id <> COALESCE((
        SELECT MAX(id) FROM evaluations WHERE version_id = NEW.version_id
    ), 0) THEN RAISE(ABORT, 'promotion event evidence cutoff is not current') END;
    SELECT CASE WHEN NOT (
        (NEW.from_state = 'IDEA' AND NEW.to_state IN ('RESEARCH', 'PAUSED')) OR
        (NEW.from_state = 'RESEARCH' AND NEW.to_state IN ('VALIDATED', 'PAUSED')) OR
        (NEW.from_state = 'VALIDATED'
            AND NEW.to_state IN ('HOLDOUT_PASSED', 'RESEARCH', 'PAUSED')) OR
        (NEW.from_state = 'HOLDOUT_PASSED'
            AND NEW.to_state IN ('SHADOW', 'RESEARCH', 'PAUSED')) OR
        (NEW.from_state = 'SHADOW'
            AND NEW.to_state IN ('PAPER', 'DEGRADED', 'PAUSED')) OR
        (NEW.from_state = 'PAPER'
            AND NEW.to_state IN ('CANARY', 'DEGRADED', 'PAUSED')) OR
        (NEW.from_state = 'CANARY'
            AND NEW.to_state IN ('PRODUCTION', 'DEGRADED', 'PAUSED')) OR
        (NEW.from_state = 'PRODUCTION'
            AND NEW.to_state IN ('DEGRADED', 'PAUSED')) OR
        (NEW.from_state = 'DEGRADED'
            AND NEW.to_state IN ('RESEARCH', 'PAUSED')) OR
        (NEW.from_state = 'PAUSED' AND NEW.to_state = 'RESEARCH')
    ) THEN RAISE(ABORT, 'promotion event transition is not allowed') END;
END;

CREATE TRIGGER active_version_belongs_to_strategy
BEFORE UPDATE OF active_version_id ON strategies
WHEN NEW.active_version_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM versions
    WHERE id = NEW.active_version_id AND strategy_id = OLD.id
)
BEGIN
    SELECT RAISE(ABORT, 'active version belongs to another strategy');
END;

CREATE TRIGGER lifecycle_transition_is_allowed
BEFORE UPDATE OF lifecycle ON versions
BEGIN
    SELECT CASE WHEN NOT (
        (OLD.lifecycle = 'IDEA' AND NEW.lifecycle IN ('RESEARCH', 'PAUSED')) OR
        (OLD.lifecycle = 'RESEARCH' AND NEW.lifecycle IN ('VALIDATED', 'PAUSED')) OR
        (OLD.lifecycle = 'VALIDATED'
            AND NEW.lifecycle IN ('HOLDOUT_PASSED', 'RESEARCH', 'PAUSED')) OR
        (OLD.lifecycle = 'HOLDOUT_PASSED'
            AND NEW.lifecycle IN ('SHADOW', 'RESEARCH', 'PAUSED')) OR
        (OLD.lifecycle = 'SHADOW' AND NEW.lifecycle IN ('PAPER', 'DEGRADED', 'PAUSED')) OR
        (OLD.lifecycle = 'PAPER' AND NEW.lifecycle IN ('CANARY', 'DEGRADED', 'PAUSED')) OR
        (OLD.lifecycle = 'CANARY' AND NEW.lifecycle IN ('PRODUCTION', 'DEGRADED', 'PAUSED')) OR
        (OLD.lifecycle = 'PRODUCTION' AND NEW.lifecycle IN ('DEGRADED', 'PAUSED')) OR
        (OLD.lifecycle = 'DEGRADED' AND NEW.lifecycle IN ('RESEARCH', 'PAUSED')) OR
        (OLD.lifecycle = 'PAUSED' AND NEW.lifecycle = 'RESEARCH')
    ) THEN RAISE(ABORT, 'lifecycle transition is not allowed') END;
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM promotion_events AS event
        WHERE event.id = (
            SELECT MAX(latest.id) FROM promotion_events AS latest
            WHERE latest.version_id = OLD.id
        )
        AND event.version_id = OLD.id
        AND event.from_state = OLD.lifecycle
        AND event.to_state = NEW.lifecycle
    ) THEN RAISE(ABORT, 'matching promotion event is required') END;
END;
"""


class _RegistryConnection(sqlite3.Connection):
    """SQLite connection carrying state unavailable to ordinary raw SQL."""

    gate_state: dict[str, bool]


class StrategyRegistry:
    """Persistent strategy registry with immutable artifacts and promotion gates."""

    def __init__(self, database: str | os.PathLike[str]) -> None:
        self.database = Path(database).expanduser().resolve(strict=False)
        metadata = self._read_metadata()
        try:
            schema_version = int(metadata["schema_version"])
            candidate_value = metadata["candidate_root"]
            promoted_value = metadata["promoted_root"]
            criteria_value = metadata["gate_criteria"]
            risk_value = metadata["risk_policy"]
        except (KeyError, TypeError, ValueError) as exc:
            raise DatabaseIntegrityError("registry metadata is incomplete") from exc
        if schema_version != SCHEMA_VERSION:
            raise DatabaseIntegrityError(
                f"unsupported registry schema {schema_version}; expected {SCHEMA_VERSION}"
            )
        if not isinstance(candidate_value, str) or not isinstance(promoted_value, str):
            raise DatabaseIntegrityError("stored artifact roots are invalid")
        self.candidate_root = Path(candidate_value).resolve(strict=False)
        self.promoted_root = Path(promoted_value).resolve(strict=False)
        try:
            self.gate_criteria = GateCriteria.from_dict(criteria_value)
            self.risk_policy = RiskPolicy.from_dict(risk_value)
        except (ValidationError, RiskPolicyError) as exc:
            raise DatabaseIntegrityError(f"stored safety policy is invalid: {exc}") from exc

    @classmethod
    def initialize(
        cls,
        database: str | os.PathLike[str],
        candidate_root: str | os.PathLike[str],
        promoted_root: str | os.PathLike[str],
        *,
        gate_criteria: GateCriteria | None = None,
        risk_policy: RiskPolicy | None = None,
    ) -> StrategyRegistry:
        database_path = Path(database).expanduser().resolve(strict=False)
        if database_path.exists():
            raise AlreadyInitializedError(
                f"refusing to overwrite existing registry: {database_path}"
            )
        candidate = Path(candidate_root).expanduser().resolve(strict=False)
        promoted = Path(promoted_root).expanduser().resolve(strict=False)
        if candidate == promoted:
            raise ValidationError("candidate and promoted roots must be different")
        if cls._is_within(candidate, promoted) or cls._is_within(promoted, candidate):
            raise ValidationError("candidate and promoted roots must not overlap")

        criteria = gate_criteria or GateCriteria()
        policy = risk_policy or RiskPolicy()
        if not isinstance(criteria, GateCriteria):
            raise ValidationError("gate_criteria must be a GateCriteria instance")
        if not isinstance(policy, RiskPolicy):
            raise RiskPolicyError("risk_policy must be a RiskPolicy instance")

        database_path.parent.mkdir(parents=True, exist_ok=True)
        candidate.mkdir(parents=True, exist_ok=True)
        promoted.mkdir(parents=True, exist_ok=True)
        if not candidate.is_dir() or not promoted.is_dir():
            raise ValidationError("candidate and promoted roots must be directories")

        connection = sqlite3.connect(str(database_path))
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(_SCHEMA)
            values = {
                "schema_version": SCHEMA_VERSION,
                "candidate_root": str(candidate),
                "promoted_root": str(promoted),
                "gate_criteria": criteria.to_dict(),
                "risk_policy": policy.to_dict(),
                "created_at": _now(),
            }
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                ((key, _json_dump(value)) for key, value in values.items()),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return cls(database_path)

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            return os.path.commonpath((str(path), str(root))) == str(root)
        except ValueError:
            return False

    def _connect(self) -> _RegistryConnection:
        if not self.database.is_file():
            raise RegistryNotInitializedError(
                f"registry database does not exist: {self.database}"
            )
        try:
            connection = sqlite3.connect(
                str(self.database),
                timeout=5.0,
                isolation_level=None,
                factory=_RegistryConnection,
            )
            connection.gate_state = {"authorized": False}
            connection.create_function(
                "_local_trader_gate_authorized",
                0,
                lambda: int(connection.gate_state["authorized"]),
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            return connection
        except sqlite3.DatabaseError as exc:
            raise DatabaseIntegrityError(f"cannot open registry database: {exc}") from exc

    def _read_metadata(self) -> dict[str, Any]:
        if not self.database.is_file():
            raise RegistryNotInitializedError(
                f"registry database does not exist: {self.database}"
            )
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(self.database), timeout=5.0)
            rows = connection.execute("SELECT key, value FROM metadata").fetchall()
        except sqlite3.DatabaseError as exc:
            raise RegistryNotInitializedError(
                f"file is not an initialized local_trader registry: {self.database}"
            ) from exc
        finally:
            if connection is not None:
                connection.close()
        return {key: _json_load(value, label=f"metadata {key}") for key, value in rows}

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    @contextmanager
    def _promotion_event_write(
        connection: sqlite3.Connection,
    ) -> Iterator[None]:
        if not isinstance(connection, _RegistryConnection):
            raise DatabaseIntegrityError(
                "promotion events require a registry-managed SQLite connection"
            )
        previous = connection.gate_state["authorized"]
        connection.gate_state["authorized"] = True
        try:
            yield
        finally:
            connection.gate_state["authorized"] = previous

    def configuration(self) -> dict[str, Any]:
        return {
            "database": str(self.database),
            "schema_version": SCHEMA_VERSION,
            "candidate_root": str(self.candidate_root),
            "promoted_root": str(self.promoted_root),
            "gate_criteria": self.gate_criteria.to_dict(),
            "risk_policy": self.risk_policy.to_dict(),
        }

    def _classify_source(self, source: str | os.PathLike[str]) -> tuple[Path, str]:
        try:
            path = Path(source).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ArtifactVerificationError(f"artifact does not exist: {source}") from exc
        if not path.is_file():
            raise ArtifactVerificationError(f"artifact is not a regular file: {path}")
        if self._is_within(path, self.candidate_root):
            return path, "candidate"
        if self._is_within(path, self.promoted_root):
            return path, "promoted"
        raise ArtifactPathError(
            "artifact must resolve below the configured candidate or promoted root"
        )

    @staticmethod
    def _stable_hash(path: Path) -> tuple[str, int]:
        try:
            before_path = path.stat()
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                before_handle = os.fstat(stream.fileno())
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                after_handle = os.fstat(stream.fileno())
            after_path = path.stat()
        except OSError as exc:
            raise ArtifactVerificationError(f"cannot read artifact {path}: {exc}") from exc

        def identity(stat: os.stat_result) -> tuple[int, int, int, int]:
            return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

        if not (
            identity(before_path)
            == identity(before_handle)
            == identity(after_handle)
            == identity(after_path)
        ):
            raise ArtifactVerificationError(
                f"artifact changed while its SHA-256 was being calculated: {path}"
            )
        return digest.hexdigest(), int(after_path.st_size)

    def register(
        self,
        name: str,
        source_path: str | os.PathLike[str],
        *,
        description: str = "",
        parent_version: int | None = None,
        metadata: Mapping[str, Any] | None = None,
        risk_policy: RiskPolicy | None = None,
        required_source_root: str | None = None,
    ) -> dict[str, Any]:
        strategy_name = _clean_text("strategy name", name, max_length=128)
        description_value = _clean_text(
            "description", description, required=False, max_length=4096
        )
        if metadata is None:
            metadata_value: Mapping[str, Any] = {}
        elif not isinstance(metadata, Mapping):
            raise ValidationError("metadata must be a JSON object")
        else:
            metadata_value = metadata
        metadata_json = _json_dump(dict(metadata_value))
        policy = risk_policy or self.risk_policy
        if not isinstance(policy, RiskPolicy):
            raise RiskPolicyError("risk_policy must be a RiskPolicy instance")
        policy_json = _json_dump(policy.to_dict())

        if required_source_root not in {None, "candidate", "promoted"}:
            raise ValidationError(
                "required_source_root must be candidate, promoted, or None"
            )
        source, root_label = self._classify_source(source_path)
        if required_source_root is not None and root_label != required_source_root:
            raise ValidationError(
                f"registration requires source_root={required_source_root}; "
                f"resolved source_root={root_label}"
            )
        sha256, size = self._stable_hash(source)
        created_at = _now()

        try:
            with self._transaction() as connection:
                strategy = connection.execute(
                    "SELECT * FROM strategies WHERE name = ? COLLATE NOCASE",
                    (strategy_name,),
                ).fetchone()
                if strategy is None:
                    is_first_version = True
                    if root_label == "promoted":
                        raise ValidationError(
                            "a promoted artifact must be registered as an explicit "
                            "child of an existing candidate version"
                        )
                    if parent_version is not None:
                        raise ValidationError(
                            "parent_version cannot be used for a new strategy"
                        )
                    cursor = connection.execute(
                        "INSERT INTO strategies(name, description, created_at) VALUES (?, ?, ?)",
                        (strategy_name, description_value, created_at),
                    )
                    strategy_id = int(cursor.lastrowid)
                    version_number = 1
                    parent_id = None
                else:
                    is_first_version = False
                    strategy_id = int(strategy["id"])
                    version_number = int(
                        connection.execute(
                            """
                            SELECT COALESCE(MAX(version_number), 0) + 1
                            FROM versions WHERE strategy_id = ?
                            """,
                            (strategy_id,),
                        ).fetchone()[0]
                    )
                    if root_label == "promoted" and parent_version is None:
                        raise ValidationError(
                            "promoted registration requires explicit --parent-version"
                        )
                    if parent_version is None:
                        parent_id = strategy["active_version_id"]
                        parent = (
                            None
                            if parent_id is None
                            else connection.execute(
                                "SELECT * FROM versions WHERE id = ?", (parent_id,)
                            ).fetchone()
                        )
                    else:
                        if type(parent_version) is not int or parent_version < 1:
                            raise ValidationError(
                                "parent_version must be a positive integer"
                            )
                        parent = connection.execute(
                            "SELECT * FROM versions WHERE strategy_id = ? AND version_number = ?",
                            (strategy_id, parent_version),
                        ).fetchone()
                        if parent is None:
                            raise NotFoundError(
                                f"strategy {strategy_name!r} has no version {parent_version}"
                            )
                        parent_id = int(parent["id"])

                    if root_label == "promoted":
                        assert parent is not None
                        if parent["source_root"] != "candidate":
                            raise ValidationError(
                                "promoted registration parent must be a candidate version"
                            )
                        if parent["artifact_sha256"] != sha256:
                            raise ValidationError(
                                "promoted artifact SHA-256 must exactly match its "
                                "candidate parent"
                            )
                        manifest_failures = self._deployment_manifest_issues(
                            metadata_value
                        )
                        if manifest_failures:
                            raise ValidationError("; ".join(manifest_failures))
                    elif parent is not None and parent["source_root"] == "promoted":
                        raise ValidationError(
                            "candidate registration cannot descend from a promoted version"
                        )

                cursor = connection.execute(
                    """
                    INSERT INTO versions(
                        strategy_id, version_number, parent_version_id, lifecycle,
                        source_path, source_root, artifact_sha256, artifact_size,
                        risk_policy_json, metadata_json, created_at
                    ) VALUES (?, ?, ?, 'IDEA', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        strategy_id,
                        version_number,
                        parent_id,
                        str(source),
                        root_label,
                        sha256,
                        size,
                        policy_json,
                        metadata_json,
                        created_at,
                    ),
                )
                version_id = int(cursor.lastrowid)
                if is_first_version:
                    connection.execute(
                        "UPDATE strategies SET active_version_id = ? WHERE id = ?",
                        (version_id, strategy_id),
                    )
                row = self._fetch_version(connection, strategy_name, version_number)
                assert row is not None
                return self._version_dict(row)
        except sqlite3.IntegrityError as exc:
            message = str(exc)
            if "artifact_sha256" in message or "versions.strategy_id" in message:
                raise ValidationError(
                    "this exact artifact is already registered for the strategy"
                ) from exc
            raise DatabaseIntegrityError(f"registration failed: {message}") from exc

    @staticmethod
    def _fetch_version(
        connection: sqlite3.Connection,
        strategy_name: str,
        version: int | None = None,
    ) -> sqlite3.Row | None:
        if version is None:
            return connection.execute(
                """
                SELECT s.name AS strategy_name, s.description AS strategy_description,
                       s.active_version_id, v.*
                FROM strategies AS s
                JOIN versions AS v ON v.id = s.active_version_id
                WHERE s.name = ? COLLATE NOCASE
                """,
                (strategy_name,),
            ).fetchone()
        if type(version) is not int or version < 1:
            raise ValidationError("version must be a positive integer")
        return connection.execute(
            """
            SELECT s.name AS strategy_name, s.description AS strategy_description,
                   s.active_version_id, v.*
            FROM strategies AS s
            JOIN versions AS v ON v.strategy_id = s.id
            WHERE s.name = ? COLLATE NOCASE AND v.version_number = ?
            """,
            (strategy_name, version),
        ).fetchone()

    def _require_version(
        self,
        connection: sqlite3.Connection,
        strategy_name: str,
        version: int | None = None,
    ) -> sqlite3.Row:
        name = _clean_text("strategy name", strategy_name, max_length=128)
        row = self._fetch_version(connection, name, version)
        if row is None:
            suffix = "" if version is None else f" version {version}"
            raise NotFoundError(f"strategy {name!r}{suffix} was not found")
        return row

    @staticmethod
    def _version_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "strategy_id": int(row["strategy_id"]),
            "strategy": row["strategy_name"],
            "description": row["strategy_description"],
            "version_id": int(row["id"]),
            "version": int(row["version_number"]),
            "parent_version_id": (
                None if row["parent_version_id"] is None else int(row["parent_version_id"])
            ),
            "active": int(row["active_version_id"]) == int(row["id"]),
            "lifecycle": row["lifecycle"],
            "source_path": row["source_path"],
            "source_root": row["source_root"],
            "artifact_sha256": row["artifact_sha256"],
            "artifact_size": int(row["artifact_size"]),
            "risk_policy": _json_load(row["risk_policy_json"], label="risk policy"),
            "metadata": _json_load(row["metadata_json"], label="version metadata"),
            "created_at": row["created_at"],
        }

    def _verify_row(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            source, root_label = self._classify_source(row["source_path"])
        except ArtifactError:
            raise
        if root_label != row["source_root"]:
            raise ArtifactPathError(
                "artifact resolved under a different root than the immutable registry record"
            )
        actual_hash, actual_size = self._stable_hash(source)
        if actual_size != int(row["artifact_size"]):
            raise ArtifactVerificationError(
                f"artifact size mismatch for {source}: "
                f"expected {row['artifact_size']}, got {actual_size}"
            )
        if actual_hash != row["artifact_sha256"]:
            raise ArtifactVerificationError(
                f"artifact SHA-256 mismatch for {source}: "
                f"expected {row['artifact_sha256']}, got {actual_hash}"
            )
        return {
            "strategy": row["strategy_name"],
            "version": int(row["version_number"]),
            "source_path": str(source),
            "source_root": root_label,
            "artifact_sha256": actual_hash,
            "artifact_size": actual_size,
            "valid": True,
        }

    def verify_artifact(
        self, strategy: str, *, version: int | None = None
    ) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = self._require_version(connection, strategy, version)
            return self._verify_row(row)
        finally:
            connection.close()

    # A concise alias is useful to both API callers and the CLI vocabulary.
    verify = verify_artifact

    def verify_all(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT s.name AS strategy_name, s.description AS strategy_description,
                       s.active_version_id, v.*
                FROM strategies AS s JOIN versions AS v ON v.strategy_id = s.id
                ORDER BY lower(s.name), v.version_number
                """
            ).fetchall()
            results: list[dict[str, Any]] = []
            for row in rows:
                try:
                    results.append(self._verify_row(row))
                except ArtifactError as exc:
                    results.append(
                        {
                            "strategy": row["strategy_name"],
                            "version": int(row["version_number"]),
                            "source_path": row["source_path"],
                            "artifact_sha256": row["artifact_sha256"],
                            "valid": False,
                            "error": str(exc),
                        }
                    )
            return results
        finally:
            connection.close()

    @staticmethod
    def _normalize_sample_type(value: str) -> str:
        normalized = _clean_text("sample_type", value, max_length=32).upper()
        normalized = normalized.replace("-", "_").replace(" ", "_")
        if normalized not in SAMPLE_TYPES:
            raise ValidationError(
                "sample_type must be one of: " + ", ".join(sorted(SAMPLE_TYPES))
            )
        return normalized

    def evaluate(
        self,
        strategy: str,
        *,
        symbol: str,
        timeframe: str,
        sample_type: str,
        net_profit: float,
        profit_factor: float,
        max_drawdown: float,
        win_rate: float,
        trade_count: int,
        avg_trade: float,
        max_daily_loss_abs: float | None = None,
        version: int | None = None,
        trial_id: int | None = None,
        evidence_id: str | None = None,
        dataset_sha256: str | None = None,
        provenance: Mapping[str, Any] | None = None,
        notes: str = "",
        research_only: bool = False,
    ) -> dict[str, Any]:
        symbol_value = _clean_text("symbol", symbol, max_length=32).upper()
        timeframe_value = _clean_text("timeframe", timeframe, max_length=32).lower()
        sample_value = self._normalize_sample_type(sample_type)
        if type(research_only) is not bool:
            raise ValidationError("research_only must be a boolean")
        if research_only and sample_value in {"CANARY", "PRODUCTION"}:
            raise ValidationError(
                f"{sample_value} evidence is permanently blocked through MCP"
            )
        net_profit_value = _finite_metric("net_profit", net_profit)
        profit_factor_value = _finite_metric("profit_factor", profit_factor)
        drawdown_value = _finite_metric("max_drawdown", max_drawdown)
        win_rate_value = _finite_metric("win_rate", win_rate)
        avg_trade_value = _finite_metric("avg_trade", avg_trade)
        daily_loss_value = (
            None
            if max_daily_loss_abs is None
            else _finite_metric("max_daily_loss_abs", max_daily_loss_abs)
        )
        if profit_factor_value < 0:
            raise ValidationError("profit_factor must not be negative")
        if not 0 <= drawdown_value <= 100:
            raise ValidationError("max_drawdown must be a percentage from 0 to 100")
        if not 0 <= win_rate_value <= 100:
            raise ValidationError("win_rate must be a percentage from 0 to 100")
        if type(trade_count) is not int or trade_count < 0:
            raise ValidationError("trade_count must be a non-negative integer")
        if daily_loss_value is not None and daily_loss_value < 0:
            raise ValidationError("max_daily_loss_abs must not be negative")
        if trial_id is not None and (type(trial_id) is not int or trial_id < 1):
            raise ValidationError("trial_id must be a positive integer")
        if dataset_sha256 is None:
            dataset_hash_value = None
        else:
            dataset_hash_value = _clean_text(
                "dataset_sha256", dataset_sha256, max_length=64
            ).lower()
            if len(dataset_hash_value) != 64 or any(
                character not in "0123456789abcdef"
                for character in dataset_hash_value
            ):
                raise ValidationError(
                    "dataset_sha256 must be exactly 64 hexadecimal characters"
                )
        provenance_value = {} if provenance is None else provenance
        if not isinstance(provenance_value, Mapping):
            raise ValidationError("provenance must be a JSON object")
        provenance_json = _json_dump(dict(provenance_value))
        notes_value = _clean_text("notes", notes, required=False, max_length=4096)

        fingerprint_payload = {
            "symbol": symbol_value,
            "timeframe": timeframe_value,
            "sample_type": sample_value,
            "dataset_sha256": dataset_hash_value,
            "net_profit": net_profit_value,
            "profit_factor": profit_factor_value,
            "max_drawdown": drawdown_value,
            "win_rate": win_rate_value,
            "trade_count": trade_count,
            "avg_trade": avg_trade_value,
            "max_daily_loss_abs": daily_loss_value,
        }
        evidence_fingerprint = hashlib.sha256(
            _json_dump(fingerprint_payload).encode("utf-8")
        ).hexdigest()
        evidence_id_value = (
            f"sha256:{evidence_fingerprint}"
            if evidence_id is None
            else _clean_text("evidence_id", evidence_id, max_length=256)
        )

        with self._transaction() as connection:
            row = self._require_version(connection, strategy, version)
            self._verify_row(row)
            current = Lifecycle.coerce(row["lifecycle"])
            if research_only and current in LIVE_STATES:
                raise ValidationError(
                    f"MCP cannot record evidence for a version in {current.value}"
                )
            allowed_collection_states = SAMPLE_COLLECTION_STATES.get(sample_value)
            if (
                allowed_collection_states is not None
                and current not in allowed_collection_states
            ):
                expected = ", ".join(
                    sorted(state.value for state in allowed_collection_states)
                )
                raise ValidationError(
                    f"{sample_value} evidence can only be recorded while the "
                    f"version is in: {expected}; current lifecycle is {current.value}"
                )
            if trial_id is not None:
                trial = connection.execute(
                    "SELECT version_id FROM trials WHERE id = ?", (trial_id,)
                ).fetchone()
                if trial is None:
                    raise NotFoundError(f"trial {trial_id} was not found")
                if int(trial["version_id"]) != int(row["id"]):
                    raise ValidationError("trial belongs to a different strategy version")
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO evaluations(
                        version_id, trial_id, symbol, timeframe, sample_type,
                        evidence_id, dataset_sha256, provenance_json,
                        evidence_fingerprint, net_profit, profit_factor,
                        max_drawdown, win_rate, trade_count, avg_trade, notes,
                        max_daily_loss_abs, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(row["id"]),
                        trial_id,
                        symbol_value,
                        timeframe_value,
                        sample_value,
                        evidence_id_value,
                        dataset_hash_value,
                        provenance_json,
                        evidence_fingerprint,
                        net_profit_value,
                        profit_factor_value,
                        drawdown_value,
                        win_rate_value,
                        trade_count,
                        avg_trade_value,
                        notes_value,
                        daily_loss_value,
                        _now(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                message = str(exc)
                if "evidence_id" in message:
                    raise ValidationError(
                        f"evidence_id {evidence_id_value!r} is already registered "
                        "for this version"
                    ) from exc
                if "evidence_fingerprint" in message:
                    raise ValidationError(
                        "an exact duplicate of this evaluation already exists "
                        "for this version"
                    ) from exc
                raise DatabaseIntegrityError(
                    f"evaluation persistence failed: {message}"
                ) from exc
            evaluation_id = int(cursor.lastrowid)
            stored = connection.execute(
                "SELECT * FROM evaluations WHERE id = ?", (evaluation_id,)
            ).fetchone()
            assert stored is not None
            return self._evaluation_dict(stored, row["strategy_name"], row["version_number"])

    @staticmethod
    def _evaluation_dict(
        row: sqlite3.Row, strategy_name: str, version_number: int
    ) -> dict[str, Any]:
        return {
            "evaluation_id": int(row["id"]),
            "strategy": strategy_name,
            "version": int(version_number),
            "trial_id": None if row["trial_id"] is None else int(row["trial_id"]),
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "sample_type": row["sample_type"],
            "evidence_id": row["evidence_id"],
            "dataset_sha256": row["dataset_sha256"],
            "provenance": _json_load(row["provenance_json"], label="provenance"),
            "evidence_fingerprint": row["evidence_fingerprint"],
            "net_profit": float(row["net_profit"]),
            "profit_factor": float(row["profit_factor"]),
            "max_drawdown": float(row["max_drawdown"]),
            "win_rate": float(row["win_rate"]),
            "trade_count": int(row["trade_count"]),
            "avg_trade": float(row["avg_trade"]),
            "max_daily_loss_abs": (
                None
                if row["max_daily_loss_abs"] is None
                else float(row["max_daily_loss_abs"])
            ),
            "notes": row["notes"],
            "recorded_at": row["recorded_at"],
        }

    def record_trial(
        self,
        strategy: str,
        *,
        trial_type: str,
        status: str,
        version: int | None = None,
        hypothesis: str = "",
        parameters: Mapping[str, Any] | None = None,
        result: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        trial_type_value = _clean_text("trial_type", trial_type, max_length=64).upper()
        status_value = _clean_text("status", status, max_length=16).upper()
        if status_value not in TRIAL_STATUSES:
            raise ValidationError(
                "status must be one of: " + ", ".join(sorted(TRIAL_STATUSES))
            )
        hypothesis_value = _clean_text(
            "hypothesis", hypothesis, required=False, max_length=8192
        )
        parameters_value = {} if parameters is None else parameters
        result_value = {} if result is None else result
        if not isinstance(parameters_value, Mapping):
            raise ValidationError("parameters must be a JSON object")
        if not isinstance(result_value, Mapping):
            raise ValidationError("result must be a JSON object")
        parameters_json = _json_dump(dict(parameters_value))
        result_json = _json_dump(dict(result_value))

        with self._transaction() as connection:
            row = self._require_version(connection, strategy, version)
            self._verify_row(row)
            cursor = connection.execute(
                """
                INSERT INTO trials(
                    strategy_id, version_id, trial_type, status, hypothesis,
                    parameters_json, result_json, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["strategy_id"]),
                    int(row["id"]),
                    trial_type_value,
                    status_value,
                    hypothesis_value,
                    parameters_json,
                    result_json,
                    _now(),
                ),
            )
            trial_id = int(cursor.lastrowid)
            stored = connection.execute(
                "SELECT * FROM trials WHERE id = ?", (trial_id,)
            ).fetchone()
            assert stored is not None
            return self._trial_dict(stored, row["strategy_name"], row["version_number"])

    @staticmethod
    def _trial_dict(
        row: sqlite3.Row, strategy_name: str, version_number: int
    ) -> dict[str, Any]:
        return {
            "trial_id": int(row["id"]),
            "strategy": strategy_name,
            "version": int(version_number),
            "trial_type": row["trial_type"],
            "status": row["status"],
            "hypothesis": row["hypothesis"],
            "parameters": _json_load(row["parameters_json"], label="trial parameters"),
            "result": _json_load(row["result_json"], label="trial result"),
            "recorded_at": row["recorded_at"],
        }

    @staticmethod
    def _evaluation_summary(
        connection: sqlite3.Connection,
        version_id: int,
        *,
        sample_types: frozenset[str] | None = None,
        after_id: int = 0,
    ) -> dict[str, Any]:
        rows = connection.execute(
            """
            SELECT symbol, timeframe, sample_type, net_profit, profit_factor,
                   max_drawdown, win_rate, trade_count, avg_trade,
                   max_daily_loss_abs
            FROM evaluations WHERE version_id = ? AND id > ? ORDER BY id
            """,
            (version_id, after_id),
        ).fetchall()
        if sample_types is not None:
            rows = [row for row in rows if row["sample_type"] in sample_types]
        total_trades = sum(int(row["trade_count"]) for row in rows)
        weighted_win_rate = (
            sum(float(row["win_rate"]) * int(row["trade_count"]) for row in rows)
            / total_trades
            if total_trades
            else 0.0
        )
        weighted_avg_trade = (
            sum(float(row["avg_trade"]) * int(row["trade_count"]) for row in rows)
            / total_trades
            if total_trades
            else 0.0
        )
        traded_rows = [row for row in rows if int(row["trade_count"]) > 0]
        total_net_profit = sum(float(row["net_profit"]) for row in rows)
        return {
            "evaluation_count": len(rows),
            "trade_count": total_trades,
            "net_profit": total_net_profit,
            "min_profit_factor": (
                min(float(row["profit_factor"]) for row in traded_rows)
                if traded_rows
                else 0.0
            ),
            "max_drawdown": (
                max((float(row["max_drawdown"]) for row in rows), default=0.0)
            ),
            "max_daily_loss_abs": max(
                (
                    float(row["max_daily_loss_abs"])
                    for row in rows
                    if row["max_daily_loss_abs"] is not None
                ),
                default=0.0,
            ),
            "all_slices_have_daily_loss": bool(rows) and all(
                row["max_daily_loss_abs"] is not None for row in rows
            ),
            "win_rate": weighted_win_rate,
            "avg_trade": weighted_avg_trade,
            "symbol_count": len({row["symbol"] for row in traded_rows}),
            "symbols": sorted({row["symbol"] for row in traded_rows}),
            "timeframe_count": len({row["timeframe"] for row in traded_rows}),
            "timeframes": sorted({row["timeframe"] for row in traded_rows}),
            "all_slices_positive": bool(traded_rows) and all(
                float(row["net_profit"]) > 0 for row in traded_rows
            ),
            "all_slices_have_trades": bool(rows) and all(
                int(row["trade_count"]) > 0 for row in rows
            ),
            "sample_types": sorted({row["sample_type"] for row in rows}),
            "after_evaluation_id": after_id,
        }

    @staticmethod
    def _prior_evaluation_cutoff(
        connection: sqlite3.Connection,
        version_id: int,
        predecessor: Lifecycle,
    ) -> int:
        row = connection.execute(
            """
            SELECT evaluation_cutoff_id FROM promotion_events
            WHERE version_id = ? AND to_state = ?
            ORDER BY id DESC LIMIT 1
            """,
            (version_id, predecessor.value),
        ).fetchone()
        return 0 if row is None else int(row["evaluation_cutoff_id"])

    def _assess_with_connection(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        target: Lifecycle,
    ) -> GateDecision:
        current = Lifecycle.coerce(row["lifecycle"])
        version_id = int(row["id"])
        all_summary = self._evaluation_summary(connection, version_id)
        relevant_types = STAGE_EVIDENCE_TYPES.get(target)
        predecessor = EVIDENCE_PREDECESSOR_STATE.get(target)
        cutoff = (
            self._prior_evaluation_cutoff(connection, version_id, predecessor)
            if predecessor is not None
            else 0
        )
        stage_summary = self._evaluation_summary(
            connection,
            version_id,
            sample_types=relevant_types,
            after_id=cutoff,
        )
        evidence: dict[str, Any] = {
            "criteria": self.gate_criteria.to_dict(),
            "all_evaluations": all_summary,
            "required_sample_types": (
                [] if relevant_types is None else sorted(relevant_types)
            ),
            "stage_summary": stage_summary,
        }
        failures: list[str] = []
        if target not in ALLOWED_TRANSITIONS[current]:
            allowed = sorted(state.value for state in ALLOWED_TRANSITIONS[current])
            failures.append(
                f"transition {current.value} -> {target.value} is not allowed; "
                f"allowed: {', '.join(allowed)}"
            )
        elif target in METRICS_GATED_STATES:
            criteria = self.gate_criteria
            summary = stage_summary
            if summary["evaluation_count"] == 0:
                failures.append(
                    f"no new {target.value} stage evidence exists after cutoff {cutoff}"
                )
            if not summary["all_slices_have_trades"]:
                failures.append("every relevant evidence slice must contain trades")
            if not summary["all_slices_have_daily_loss"]:
                failures.append(
                    "every relevant evidence slice must report max_daily_loss_abs"
                )
            if summary["net_profit"] <= 0:
                failures.append("relevant stage aggregate net_profit must be positive")
            if not summary["all_slices_positive"]:
                failures.append("every relevant stage evidence slice must have net_profit > 0")
            if summary["min_profit_factor"] < criteria.min_profit_factor:
                failures.append(
                    f"minimum slice profit_factor {summary['min_profit_factor']:.6g} "
                    f"is below {criteria.min_profit_factor:.6g}"
                )
            if summary["max_drawdown"] > criteria.max_drawdown_pct:
                failures.append(
                    f"max_drawdown {summary['max_drawdown']:.6g}% exceeds "
                    f"{criteria.max_drawdown_pct:.6g}%"
                )
            if summary["max_drawdown"] > self.risk_policy.max_drawdown:
                failures.append(
                    f"max_drawdown {summary['max_drawdown']:.6g}% exceeds risk policy "
                    f"{self.risk_policy.max_drawdown:.6g}%"
                )
            if summary["max_daily_loss_abs"] > self.risk_policy.max_daily_loss:
                failures.append(
                    f"max_daily_loss_abs {summary['max_daily_loss_abs']:.6g} exceeds "
                    f"risk policy {self.risk_policy.max_daily_loss:.6g} USDT"
                )
            if summary["trade_count"] < criteria.min_trade_count:
                failures.append(
                    f"aggregated trade_count {summary['trade_count']} is below "
                    f"{criteria.min_trade_count}"
                )
            if summary["symbol_count"] < criteria.min_symbols:
                failures.append(
                    f"symbol_count {summary['symbol_count']} is below {criteria.min_symbols}"
                )
            if target is Lifecycle.VALIDATED and (
                summary["timeframe_count"] < criteria.min_timeframes
            ):
                failures.append(
                    f"timeframe_count {summary['timeframe_count']} is below "
                    f"{criteria.min_timeframes}"
                )
            if target is Lifecycle.VALIDATED:
                missing_sample_types = sorted(
                    RESEARCH_EVIDENCE_TYPES - set(summary["sample_types"])
                )
                if missing_sample_types:
                    failures.append(
                        "VALIDATED requires each research evidence type; missing: "
                        + ", ".join(missing_sample_types)
                    )
            if target in LIVE_STATES:
                failures.extend(self._deployment_issues(row))
        return GateDecision(
            eligible=not failures,
            from_state=current,
            to_state=target,
            failures=tuple(failures),
            evidence=evidence,
            manual_approval_required=target in MANUAL_APPROVAL_STATES,
        )

    def _deployment_issues(self, row: sqlite3.Row) -> list[str]:
        failures: list[str] = []
        source = Path(row["source_path"])
        if row["source_root"] != "promoted":
            failures.append("live deployment source_root must be promoted")
        if source.suffix.casefold() != ".py":
            failures.append("live deployment source must be a .py strategy file")
        sibling_parameter_file = source.with_suffix(".json")
        if sibling_parameter_file.exists():
            failures.append(
                f"Freqtrade sibling parameter file is forbidden: {sibling_parameter_file}"
            )
        try:
            metadata = _json_load(row["metadata_json"], label="version metadata")
        except DatabaseIntegrityError as exc:
            failures.append(str(exc))
            return failures
        if not isinstance(metadata, dict):
            failures.append("version metadata must be an object")
            return failures
        failures.extend(self._deployment_manifest_issues(metadata))
        return failures

    @staticmethod
    def _deployment_manifest_issues(metadata: Mapping[str, Any]) -> list[str]:
        failures: list[str] = []
        manifest = metadata.get("deployment_manifest")
        if not isinstance(manifest, dict):
            failures.append("metadata.deployment_manifest is required for live stages")
            return failures
        required = {
            "config_sha256",
            "lock_sha256",
            "imports_sha256",
            "freqtrade_version",
        }
        allowed = required
        if set(manifest) - allowed:
            failures.append("deployment_manifest contains unknown fields")
        if not required <= set(manifest):
            failures.append(
                "deployment_manifest requires config_sha256, lock_sha256, "
                "imports_sha256, and freqtrade_version"
            )
        for field in ("config_sha256", "lock_sha256", "imports_sha256"):
            value = manifest.get(field)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                failures.append(
                    f"deployment_manifest.{field} must be lowercase SHA-256"
                )
        if manifest.get("freqtrade_version") != "2026.7":
            failures.append(
                "deployment_manifest.freqtrade_version must be exactly 2026.7"
            )
        return failures

    def assess_promotion(
        self,
        strategy: str,
        to_state: Lifecycle | str,
        *,
        version: int | None = None,
    ) -> GateDecision:
        target = Lifecycle.coerce(to_state)
        connection = self._connect()
        try:
            row = self._require_version(connection, strategy, version)
            if target not in SAFETY_STATES:
                self._verify_row(row)
            return self._assess_with_connection(connection, row, target)
        finally:
            connection.close()

    @staticmethod
    def _valid_human_approver(value: str | None) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        cleaned = value.strip()
        if cleaned.casefold() in {"system", "auto", "automation", "bot"}:
            return None
        return cleaned

    @staticmethod
    def _parse_utc_timestamp(value: Any, *, label: str) -> datetime:
        text = _clean_text(label, value, max_length=64)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ApprovalArtifactError(
                f"{label} must be an ISO-8601 UTC timestamp"
            ) from exc
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ApprovalArtifactError(f"{label} must include the UTC timezone")
        return parsed.astimezone(UTC)

    def _consume_approval_file(
        self,
        approval_file: str | os.PathLike[str],
        row: sqlite3.Row,
        target: Lifecycle,
        approved_by: str | None,
    ) -> tuple[str, str, str, dict[str, Any]]:
        try:
            path = Path(approval_file).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ApprovalArtifactError(
                f"approval file does not exist: {approval_file}"
            ) from exc
        if not path.is_file():
            raise ApprovalArtifactError("approval artifact must be a regular file")
        if self._is_within(path, self.candidate_root) or self._is_within(
            path, self.promoted_root
        ):
            raise ApprovalArtifactError(
                "approval artifact must be outside candidate and promoted roots"
            )
        if path == self.database:
            raise ApprovalArtifactError("approval artifact cannot be the registry database")
        try:
            if path.stat().st_size > MAX_APPROVAL_BYTES:
                raise ApprovalArtifactError(
                    f"approval artifact exceeds {MAX_APPROVAL_BYTES} bytes"
                )
            raw = path.read_bytes()
        except OSError as exc:
            raise ApprovalArtifactError(f"cannot read approval artifact: {exc}") from exc
        digest, size = self._stable_hash(path)
        if size != len(raw) or hashlib.sha256(raw).hexdigest() != digest:
            raise ApprovalArtifactError("approval artifact changed while being read")
        try:
            approval = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApprovalArtifactError(
                "approval artifact must contain valid UTF-8 JSON"
            ) from exc
        if not isinstance(approval, dict) or set(approval) != APPROVAL_FIELDS:
            raise ApprovalArtifactError(
                "approval JSON must contain exactly: "
                + ", ".join(sorted(APPROVAL_FIELDS))
            )
        expected = {
            "strategy": row["strategy_name"],
            "version": int(row["version_number"]),
            "target": target.value,
            "artifact_sha256": row["artifact_sha256"],
        }
        for key, value in expected.items():
            if approval.get(key) != value:
                raise ApprovalArtifactError(
                    f"approval field {key!r} does not exactly match the registered version"
                )
        human = self._valid_human_approver(approval.get("approver"))
        supplied_human = self._valid_human_approver(approved_by)
        if human is None:
            raise ApprovalArtifactError("approval must name a human approver")
        if supplied_human is None or supplied_human != human:
            raise ApprovalArtifactError(
                "--approved-by must exactly match the approval artifact approver"
            )
        expiry = self._parse_utc_timestamp(
            approval.get("expires_at"), label="expires_at"
        )
        now = datetime.now(UTC)
        if expiry <= now:
            raise ApprovalArtifactError("approval artifact has expired")
        if expiry > now + timedelta(seconds=MAX_APPROVAL_LIFETIME_SECONDS):
            raise ApprovalArtifactError(
                "approval expiry is too far in the future; maximum lifetime is 15 minutes"
            )

        consumed = path.with_name(f"{path.name}.consumed.{digest}")
        try:
            os.link(path, consumed)
        except FileExistsError as exc:
            raise ApprovalArtifactError(
                "approval artifact was already consumed"
            ) from exc
        except OSError as exc:
            try:
                path.replace(consumed)
            except FileExistsError as replace_exc:
                raise ApprovalArtifactError(
                    "approval artifact was already consumed"
                ) from replace_exc
            except OSError as replace_exc:
                raise ApprovalArtifactError(
                    "cannot atomically reserve approval artifact through either "
                    f"hard-link or rename: {exc}; {replace_exc}"
                ) from replace_exc
        try:
            consumed_hash, consumed_size = self._stable_hash(consumed)
            if consumed_hash != digest or consumed_size != size:
                raise ApprovalArtifactError(
                    "approval artifact changed during atomic consumption"
                )
            if path.exists():
                path.unlink()
        except Exception:
            # Keep the consumed marker on every failure. Losing an approval is
            # safer than accidentally making it reusable.
            raise
        return human, str(consumed), digest, approval

    @staticmethod
    def _max_evaluation_id(
        connection: sqlite3.Connection, version_id: int
    ) -> int:
        return int(
            connection.execute(
                "SELECT COALESCE(MAX(id), 0) FROM evaluations WHERE version_id = ?",
                (version_id,),
            ).fetchone()[0]
        )

    def promote(
        self,
        strategy: str,
        to_state: Lifecycle | str,
        *,
        version: int | None = None,
        manual_approval: bool = False,
        approved_by: str | None = None,
        approval_file: str | os.PathLike[str] | None = None,
        interactive: bool = False,
        reason: str = "",
    ) -> dict[str, Any]:
        target = Lifecycle.coerce(to_state)
        if type(manual_approval) is not bool:
            raise ValidationError("manual_approval must be a boolean")
        reason_value = _clean_text("reason", reason, required=False, max_length=4096)

        approval_reservation: Path | None = None

        try:
            with self._transaction() as connection:
                row = self._require_version(connection, strategy, version)
                if target not in SAFETY_STATES:
                    self._verify_row(row)
                decision = self._assess_with_connection(connection, row, target)
                if not decision.eligible:
                    raise GateRejectedError(
                        "; ".join(decision.failures), decision=decision
                    )
                if target in MANUAL_APPROVAL_STATES:
                    if not manual_approval or not interactive or approval_file is None:
                        raise ManualApprovalRequired(
                            f"{target.value} requires an interactive terminal, "
                            "--manual-approval, --approved-by, and --approval-file"
                        )
                    actor, approval_path, approval_sha, approval = (
                        self._consume_approval_file(
                            approval_file, row, target, approved_by
                        )
                    )
                    approval_reservation = Path(approval_path)
                else:
                    actor = (
                        _clean_text(
                            "approved_by", approved_by, required=False, max_length=128
                        )
                        if approved_by is not None
                        else "automation"
                    )
                    if not actor:
                        actor = "automation"
                    approval_path = ""
                    approval_sha = None
                    approval = {}

                evaluation_cutoff_id = self._max_evaluation_id(
                    connection, int(row["id"])
                )

                with self._promotion_event_write(connection):
                    cursor = connection.execute(
                        """
                        INSERT INTO promotion_events(
                            strategy_id, version_id, from_state, to_state, approved_by,
                            manual_approval, approval_file_path, approval_sha256,
                            approval_json, evaluation_cutoff_id, reason,
                            gate_snapshot_json, recorded_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(row["strategy_id"]),
                            int(row["id"]),
                            decision.from_state.value,
                            target.value,
                            actor,
                            1 if manual_approval else 0,
                            approval_path,
                            approval_sha,
                            _json_dump(approval),
                            evaluation_cutoff_id,
                            reason_value,
                            _json_dump(decision.to_dict()),
                            _now(),
                        ),
                    )
                event_id = int(cursor.lastrowid)
                try:
                    connection.execute(
                        "UPDATE versions SET lifecycle = ? WHERE id = ?",
                        (target.value, int(row["id"])),
                    )
                except sqlite3.IntegrityError as exc:
                    raise TransitionError(str(exc)) from exc
                updated = self._fetch_version(
                    connection, row["strategy_name"], int(row["version_number"])
                )
                assert updated is not None
                if target is Lifecycle.PRODUCTION:
                    connection.execute(
                        "UPDATE strategies SET active_version_id = ? WHERE id = ?",
                        (int(row["id"]), int(row["strategy_id"])),
                    )
                    updated = self._fetch_version(
                        connection, row["strategy_name"], int(row["version_number"])
                    )
                    assert updated is not None
                result = {
                    "promotion_event_id": event_id,
                    "from_state": decision.from_state.value,
                    "to_state": target.value,
                    "approved_by": actor,
                    "manual_approval": manual_approval,
                    "approval_file_path": approval_path,
                    "approval_sha256": approval_sha,
                    "reason": reason_value,
                    "decision": decision.to_dict(),
                    "version": self._version_dict(updated),
                }
            return result
        except Exception:
            if approval_reservation is not None and approval_reservation.exists():
                with suppress(OSError):
                    approval_reservation.unlink()
            raise

    def list_strategies(
        self, *, lifecycle: Lifecycle | str | None = None
    ) -> list[dict[str, Any]]:
        state = Lifecycle.coerce(lifecycle) if lifecycle is not None else None
        connection = self._connect()
        try:
            sql = """
                SELECT s.name AS strategy_name, s.description AS strategy_description,
                       s.active_version_id, v.*,
                       (SELECT COUNT(*) FROM versions all_versions
                        WHERE all_versions.strategy_id = s.id) AS version_count,
                       (SELECT COUNT(*) FROM evaluations all_evaluations
                        WHERE all_evaluations.version_id = v.id) AS evaluation_count
                FROM strategies AS s JOIN versions AS v ON v.id = s.active_version_id
            """
            parameters: tuple[Any, ...] = ()
            if state is not None:
                sql += " WHERE v.lifecycle = ?"
                parameters = (state.value,)
            sql += " ORDER BY lower(s.name)"
            rows = connection.execute(sql, parameters).fetchall()
            output = []
            for row in rows:
                value = self._version_dict(row)
                value["version_count"] = int(row["version_count"])
                value["evaluation_count"] = int(row["evaluation_count"])
                output.append(value)
            return output
        finally:
            connection.close()

    def list_versions(self, strategy: str) -> list[dict[str, Any]]:
        name = _clean_text("strategy name", strategy, max_length=128)
        connection = self._connect()
        try:
            strategy_row = connection.execute(
                "SELECT * FROM strategies WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            if strategy_row is None:
                raise NotFoundError(f"strategy {name!r} was not found")
            rows = connection.execute(
                """
                SELECT s.name AS strategy_name, s.description AS strategy_description,
                       s.active_version_id, v.*
                FROM strategies AS s JOIN versions AS v ON v.strategy_id = s.id
                WHERE s.id = ? ORDER BY v.version_number
                """,
                (int(strategy_row["id"]),),
            ).fetchall()
            return [self._version_dict(row) for row in rows]
        finally:
            connection.close()

    def deployment_authorization(
        self,
        strategy: str,
        version: int,
        target: Lifecycle | str,
    ) -> dict[str, Any]:
        """Authorize one exact, already-promoted artifact for a launcher.

        This is deliberately read-only: it neither copies artifacts nor changes
        lifecycle state. The caller must independently compare the returned
        config/lock hashes with the files it will actually launch.
        """

        target_state = Lifecycle.coerce(target)
        if target_state not in LIVE_STATES:
            raise DeploymentAuthorizationError(
                "deployment target must be CANARY or PRODUCTION"
            )
        if type(version) is not int or version < 1:
            raise DeploymentAuthorizationError(
                "deployment authorization requires an explicit positive version"
            )
        connection = self._connect()
        try:
            database_integrity = self._database_integrity(connection)
            if not database_integrity["valid"]:
                raise DeploymentAuthorizationError(
                    "registry database integrity checks failed"
                )
            row = self._require_version(connection, strategy, version)
            if Lifecycle.coerce(row["lifecycle"]) is not target_state:
                raise DeploymentAuthorizationError(
                    f"version lifecycle is {row['lifecycle']}, not {target_state.value}"
                )
            self._verify_row(row)
            deployment_issues = self._deployment_issues(row)
            if deployment_issues:
                raise DeploymentAuthorizationError("; ".join(deployment_issues))
            self._verify_live_promotion_event(connection, row, target_state)
            if target_state is Lifecycle.PRODUCTION and not bool(
                int(row["active_version_id"]) == int(row["id"])
            ):
                raise DeploymentAuthorizationError(
                    "PRODUCTION version is not the strategy's active version"
                )
            metadata = _json_load(row["metadata_json"], label="version metadata")
            manifest = metadata["deployment_manifest"]
            return {
                "strategy": row["strategy_name"],
                "version": int(row["version_number"]),
                "version_id": int(row["id"]),
                "target": target_state.value,
                "lifecycle": row["lifecycle"],
                "source_path": row["source_path"],
                "source_root": row["source_root"],
                "artifact_sha256": row["artifact_sha256"],
                "artifact_size": int(row["artifact_size"]),
                "risk_policy": _json_load(
                    row["risk_policy_json"], label="risk policy"
                ),
                "metadata": metadata,
                "deployment_manifest": manifest,
            }
        finally:
            connection.close()

    def _verify_live_promotion_event(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        target: Lifecycle,
    ) -> None:
        event = connection.execute(
            """
            SELECT * FROM promotion_events
            WHERE version_id = ? AND to_state = ?
            ORDER BY id DESC LIMIT 1
            """,
            (int(row["id"]), target.value),
        ).fetchone()
        if event is None or not bool(event["manual_approval"]):
            raise DeploymentAuthorizationError(
                f"{target.value} has no manual promotion approval event"
            )
        approval_sha = event["approval_sha256"]
        if not isinstance(approval_sha, str):
            raise DeploymentAuthorizationError(
                "live promotion event has no approval artifact hash"
            )
        try:
            path = Path(event["approval_file_path"]).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise DeploymentAuthorizationError(
                "consumed approval artifact is missing"
            ) from exc
        if self._is_within(path, self.candidate_root) or self._is_within(
            path, self.promoted_root
        ):
            raise DeploymentAuthorizationError(
                "consumed approval artifact is inside a strategy source root"
            )
        try:
            actual_hash, _size = self._stable_hash(path)
        except ArtifactVerificationError as exc:
            raise DeploymentAuthorizationError(str(exc)) from exc
        if actual_hash != approval_sha:
            raise DeploymentAuthorizationError(
                "consumed approval artifact SHA-256 does not match the event"
            )
        approval = _json_load(event["approval_json"], label="approval")
        try:
            approval_file_bytes = path.read_bytes()
            approval_file = json.loads(approval_file_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DeploymentAuthorizationError(
                "consumed approval artifact is not readable valid JSON"
            ) from exc
        if hashlib.sha256(approval_file_bytes).hexdigest() != approval_sha:
            raise DeploymentAuthorizationError(
                "consumed approval artifact changed during authorization"
            )
        if approval_file != approval:
            raise DeploymentAuthorizationError(
                "consumed approval artifact differs from the event snapshot"
            )
        if not isinstance(approval, dict) or set(approval) != APPROVAL_FIELDS:
            raise DeploymentAuthorizationError(
                "stored live approval has invalid fields"
            )
        expected = {
            "strategy": row["strategy_name"],
            "version": int(row["version_number"]),
            "target": target.value,
            "artifact_sha256": row["artifact_sha256"],
            "approver": event["approved_by"],
        }
        if any(approval.get(key) != value for key, value in expected.items()):
            raise DeploymentAuthorizationError(
                "stored live approval does not match the exact deployment"
            )
        try:
            expiry = self._parse_utc_timestamp(
                approval["expires_at"], label="expires_at"
            )
            recorded = self._parse_utc_timestamp(
                event["recorded_at"], label="promotion recorded_at"
            )
        except ApprovalArtifactError as exc:
            raise DeploymentAuthorizationError(str(exc)) from exc
        if recorded > expiry:
            raise DeploymentAuthorizationError(
                "live promotion event was recorded after approval expiry"
            )

    def status(
        self, strategy: str, *, version: int | None = None
    ) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = self._require_version(connection, strategy, version)
            summary = self._evaluation_summary(connection, int(row["id"]))
            evaluation_rows = connection.execute(
                "SELECT * FROM evaluations WHERE version_id = ? ORDER BY id",
                (int(row["id"]),),
            ).fetchall()
            trial_rows = connection.execute(
                "SELECT * FROM trials WHERE version_id = ? ORDER BY id",
                (int(row["id"]),),
            ).fetchall()
            event_rows = connection.execute(
                "SELECT * FROM promotion_events WHERE version_id = ? ORDER BY id",
                (int(row["id"]),),
            ).fetchall()
            try:
                artifact = self._verify_row(row)
            except ArtifactError as exc:
                artifact = {
                    "valid": False,
                    "source_path": row["source_path"],
                    "artifact_sha256": row["artifact_sha256"],
                    "error": str(exc),
                }
            current = Lifecycle.coerce(row["lifecycle"])
            gates = {}
            for target in sorted(ALLOWED_TRANSITIONS[current], key=lambda item: item.value):
                gates[target.value] = self._assess_with_connection(
                    connection, row, target
                ).to_dict()
            return {
                "version": self._version_dict(row),
                "artifact": artifact,
                "evaluation_summary": summary,
                "evaluations": [
                    self._evaluation_dict(
                        item, row["strategy_name"], row["version_number"]
                    )
                    for item in evaluation_rows
                ],
                "trials": [
                    self._trial_dict(item, row["strategy_name"], row["version_number"])
                    for item in trial_rows
                ],
                "promotion_events": [self._event_dict(item) for item in event_rows],
                "next_gates": gates,
            }
        finally:
            connection.close()

    @staticmethod
    def _event_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "promotion_event_id": int(row["id"]),
            "strategy_id": int(row["strategy_id"]),
            "version_id": int(row["version_id"]),
            "from_state": row["from_state"],
            "to_state": row["to_state"],
            "approved_by": row["approved_by"],
            "manual_approval": bool(row["manual_approval"]),
            "approval_file_path": row["approval_file_path"],
            "approval_sha256": row["approval_sha256"],
            "approval": _json_load(row["approval_json"], label="approval"),
            "evaluation_cutoff_id": int(row["evaluation_cutoff_id"]),
            "reason": row["reason"],
            "decision": _json_load(row["gate_snapshot_json"], label="gate snapshot"),
            "recorded_at": row["recorded_at"],
        }

    def database_integrity(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            return self._database_integrity(connection)
        finally:
            connection.close()

    @staticmethod
    def _database_integrity(connection: sqlite3.Connection) -> dict[str, Any]:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        trigger_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger'"
            )
        }
        missing_triggers = sorted(REQUIRED_TRIGGERS - trigger_names)
        valid = (
            integrity == "ok"
            and not foreign_keys
            and application_id == SQLITE_APPLICATION_ID
            and user_version == SCHEMA_VERSION
            and not missing_triggers
        )
        return {
            "valid": valid,
            "integrity_check": integrity,
            "foreign_key_violations": [list(row) for row in foreign_keys],
            "application_id": application_id,
            "user_version": user_version,
            "missing_triggers": missing_triggers,
        }


def initialize_registry(
    database: str | os.PathLike[str],
    candidate_root: str | os.PathLike[str],
    promoted_root: str | os.PathLike[str],
    *,
    gate_criteria: GateCriteria | None = None,
    risk_policy: RiskPolicy | None = None,
) -> StrategyRegistry:
    """Functional convenience wrapper around :meth:`StrategyRegistry.initialize`."""

    return StrategyRegistry.initialize(
        database,
        candidate_root,
        promoted_root,
        gate_criteria=gate_criteria,
        risk_policy=risk_policy,
    )
