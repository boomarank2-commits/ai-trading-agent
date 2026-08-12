"""Research-only MCP facade for the local strategy registry.

The server intentionally exposes no exchange, order, credential, runtime, or
live-capital operation. Registration is candidate-only, and every mutating
research tool is limited to the path ending at ``PAPER``. ``CANARY`` and
``PRODUCTION`` lifecycle changes and evidence are unavailable.
"""

from __future__ import annotations

import argparse
import os
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .errors import ValidationError
from .models import Lifecycle
from .registry import StrategyRegistry

DATABASE_ENVIRONMENT_VARIABLE = "LOCAL_TRADER_REGISTRY_DB"
BLOCKED_LIVE_STATES = frozenset({Lifecycle.CANARY, Lifecycle.PRODUCTION})
MCP_PROMOTION_STATES = frozenset(
    {
        Lifecycle.RESEARCH,
        Lifecycle.VALIDATED,
        Lifecycle.HOLDOUT_PASSED,
        Lifecycle.SHADOW,
        Lifecycle.PAPER,
    }
)
MCP_EVIDENCE_TYPES = frozenset(
    {
        "BACKTEST",
        "HOLDOUT",
        "IN_SAMPLE",
        "OUT_OF_SAMPLE",
        "PAPER",
        "SHADOW",
        "VALIDATION",
        "WALK_FORWARD",
    }
)

_SENSITIVE_KEY_PARTS = frozenset(
    {
        "api_key",
        "apikey",
        "credential",
        "password",
        "private_key",
        "secret",
        "token",
    }
)
_SENSITIVE_TEXT = re.compile(
    r"(?:api[ _-]?key|password|private[ _-]?key|secret|token)\s*[:=]"
    r"|bearer\s+[a-z0-9._~-]"
    r"|-----begin [^-]*private key-----",
    flags=re.IGNORECASE,
)


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")


def _is_sensitive_key(value: Any) -> bool:
    normalized = _normalized_key(value)
    return any(
        normalized == part
        or normalized.startswith(f"{part}_")
        or normalized.endswith(f"_{part}")
        for part in _SENSITIVE_KEY_PARTS
    )


def _reject_sensitive_mapping(value: Mapping[str, Any], *, label: str) -> None:
    """Prevent accidental credential persistence in free-form registry JSON."""

    for key, item in value.items():
        if _is_sensitive_key(key):
            raise ValidationError(f"{label} must not contain credential or secret fields")
        if isinstance(item, Mapping):
            _reject_sensitive_mapping(item, label=label)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                if isinstance(nested, Mapping):
                    _reject_sensitive_mapping(nested, label=label)


def _reject_sensitive_text(value: str, *, label: str) -> None:
    if _SENSITIVE_TEXT.search(value):
        raise ValidationError(f"{label} must not contain credentials or secrets")


def _redact_sensitive(value: Any) -> Any:
    """Return a JSON-compatible copy with credential-like keyed values removed."""

    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _is_sensitive_key(key) else _redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_sensitive(item) for item in value]
    return value


def _research_target(value: Lifecycle | str) -> Lifecycle:
    target = Lifecycle.coerce(value)
    if target in BLOCKED_LIVE_STATES:
        raise ValidationError(
            f"{target.value} is permanently blocked through MCP; "
            "live-stage decisions require an explicit human CLI workflow"
        )
    if target not in MCP_PROMOTION_STATES:
        allowed = ", ".join(sorted(state.value for state in MCP_PROMOTION_STATES))
        raise ValidationError(
            f"MCP only accepts research promotion targets through PAPER: {allowed}"
        )
    return target


def _research_sample_type(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("sample_type must be a non-empty string")
    sample_type = value.strip().upper().replace("-", "_").replace(" ", "_")
    if sample_type in {"CANARY", "PRODUCTION"}:
        raise ValidationError(
            f"{sample_type} evidence is permanently blocked through MCP"
        )
    if sample_type not in MCP_EVIDENCE_TYPES:
        allowed = ", ".join(sorted(MCP_EVIDENCE_TYPES))
        raise ValidationError(
            f"MCP only accepts research evidence types through PAPER: {allowed}"
        )
    return sample_type


class ResearchRegistryTools:
    """Separately testable implementation behind the FastMCP tool bindings."""

    def __init__(
        self,
        database: str | os.PathLike[str],
        *,
        registry_factory: Callable[[str | os.PathLike[str]], StrategyRegistry]
        = StrategyRegistry,
    ) -> None:
        self.database = Path(database).expanduser().resolve(strict=False)
        self._registry_factory = registry_factory

    def _registry(self) -> StrategyRegistry:
        return self._registry_factory(self.database)

    def configuration(self) -> dict[str, Any]:
        """Show registry policy, roots, integrity, and the fixed MCP safety boundary."""

        registry = self._registry()
        return _redact_sensitive(
            {
                "mode": "research_only",
                "live_stages_blocked": sorted(
                    state.value for state in BLOCKED_LIVE_STATES
                ),
                "maximum_mcp_stage": Lifecycle.PAPER.value,
                "registry": registry.configuration(),
                "database_integrity": registry.database_integrity(),
            }
        )

    def strategy_status(
        self, strategy: str, version: int | None = None
    ) -> dict[str, Any]:
        """Read one immutable version, evidence summary, trials, and next gates."""

        return _redact_sensitive(self._registry().status(strategy, version=version))

    def list_strategies(self, lifecycle: str | None = None) -> dict[str, Any]:
        """List active strategy versions, optionally filtered by lifecycle."""

        strategies = self._registry().list_strategies(lifecycle=lifecycle)
        return _redact_sensitive({"count": len(strategies), "strategies": strategies})

    def verify_artifacts(
        self, strategy: str | None = None, version: int | None = None
    ) -> dict[str, Any]:
        """Recalculate immutable artifact hashes for one version or the registry."""

        registry = self._registry()
        if strategy is None:
            if version is not None:
                raise ValidationError("version requires a strategy")
            artifacts = registry.verify_all()
        else:
            artifacts = [registry.verify_artifact(strategy, version=version)]
        return _redact_sensitive(
            {
                "valid": all(bool(item.get("valid")) for item in artifacts),
                "artifacts": artifacts,
            }
        )

    def register_strategy(
        self,
        name: str,
        source_path: str,
        description: str = "",
        parent_version: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a hash-pinned artifact below the candidate source root."""

        metadata_value = {} if metadata is None else metadata
        _reject_sensitive_mapping(metadata_value, label="metadata")
        _reject_sensitive_text(description, label="description")
        version = self._registry().register(
            name,
            source_path,
            description=description,
            parent_version=parent_version,
            metadata=metadata_value,
            required_source_root="candidate",
        )
        return _redact_sensitive({"registered": version})

    def record_evaluation(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        sample_type: str,
        net_profit: float,
        profit_factor: float,
        max_drawdown: float,
        win_rate: float,
        trade_count: int,
        avg_trade: float,
        max_daily_loss_abs: float,
        version: int | None = None,
        trial_id: int | None = None,
        evidence_id: str | None = None,
        dataset_sha256: str | None = None,
        provenance: dict[str, Any] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        """Append deterministic backtest, validation, holdout, shadow, or paper metrics."""

        research_sample_type = _research_sample_type(sample_type)
        _reject_sensitive_text(notes, label="notes")
        provenance_value = {} if provenance is None else provenance
        _reject_sensitive_mapping(provenance_value, label="provenance")
        evaluation = self._registry().evaluate(
            strategy,
            symbol=symbol,
            timeframe=timeframe,
            sample_type=research_sample_type,
            net_profit=net_profit,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trade_count=trade_count,
            avg_trade=avg_trade,
            max_daily_loss_abs=max_daily_loss_abs,
            version=version,
            trial_id=trial_id,
            evidence_id=evidence_id,
            dataset_sha256=dataset_sha256,
            provenance=provenance_value,
            notes=notes,
            research_only=True,
        )
        return _redact_sensitive({"evaluation": evaluation})

    def assess_research_promotion(
        self,
        strategy: str,
        to_state: str,
        version: int | None = None,
    ) -> dict[str, Any]:
        """Assess one permitted research transition without changing lifecycle state."""

        target = _research_target(to_state)
        decision = self._registry().assess_promotion(
            strategy, target, version=version
        )
        return _redact_sensitive({"decision": decision.to_dict()})

    def promote_research_stage(
        self,
        strategy: str,
        to_state: str,
        version: int | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Advance one gated research step, never beyond PAPER."""

        target = _research_target(to_state)
        _reject_sensitive_text(reason, label="reason")
        promotion = self._registry().promote(
            strategy,
            target,
            version=version,
            reason=reason,
        )
        return _redact_sensitive({"promotion": promotion})


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
APPEND_ONLY = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)
LIFECYCLE_CHANGE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=False,
)


def create_server(
    database: str | os.PathLike[str],
    *,
    registry_factory: Callable[[str | os.PathLike[str]], StrategyRegistry]
    = StrategyRegistry,
) -> FastMCP:
    """Build a stdio-capable FastMCP server bound to exactly one registry."""

    tools = ResearchRegistryTools(database, registry_factory=registry_factory)
    server = FastMCP(
        "local-trader-research",
        instructions=(
            "Research registry only. Never request, accept, or expose credentials; "
            "never place orders or control a trading runtime. Registration is "
            "candidate-only. CANARY and PRODUCTION lifecycle changes and evidence "
            "are unavailable. Promotion ends at PAPER."
        ),
    )
    server.tool(
        name="registry_configuration",
        annotations=READ_ONLY,
        structured_output=True,
    )(tools.configuration)
    server.tool(
        name="strategy_status", annotations=READ_ONLY, structured_output=True
    )(tools.strategy_status)
    server.tool(
        name="list_strategies", annotations=READ_ONLY, structured_output=True
    )(tools.list_strategies)
    server.tool(
        name="verify_artifacts", annotations=READ_ONLY, structured_output=True
    )(tools.verify_artifacts)
    server.tool(
        name="register_strategy", annotations=APPEND_ONLY, structured_output=True
    )(tools.register_strategy)
    server.tool(
        name="record_evaluation", annotations=APPEND_ONLY, structured_output=True
    )(tools.record_evaluation)
    server.tool(
        name="assess_research_promotion",
        annotations=READ_ONLY,
        structured_output=True,
    )(tools.assess_research_promotion)
    server.tool(
        name="promote_research_stage",
        annotations=LIFECYCLE_CHANGE,
        structured_output=True,
    )(tools.promote_research_stage)
    return server


def resolve_database_path(
    cli_database: str | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve ``--db`` first and then the dedicated environment variable."""

    environment = os.environ if environ is None else environ
    value = cli_database or environment.get(DATABASE_ENVIRONMENT_VARIABLE)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            "registry database is required via --db or "
            f"{DATABASE_ENVIRONMENT_VARIABLE}"
        )
    return Path(value.strip()).expanduser().resolve(strict=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-trader-mcp",
        description="Run the order-free local strategy registry MCP over stdio.",
    )
    parser.add_argument(
        "--db",
        help=f"registry SQLite path (fallback: {DATABASE_ENVIRONMENT_VARIABLE})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        database = resolve_database_path(args.db)
    except ValidationError as exc:
        parser.error(str(exc))
    create_server(database).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
