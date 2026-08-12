"""Local, stdlib-only strategy registry for the Binance trading agent."""

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
    RegistryError,
    RegistryNotInitializedError,
    RiskPolicyError,
    TransitionError,
    ValidationError,
)
from .models import (
    ALLOWED_TRANSITIONS,
    GateCriteria,
    GateDecision,
    Lifecycle,
    RiskPolicy,
)
from .registry import SCHEMA_VERSION, StrategyRegistry, initialize_registry

__all__ = [
    "ALLOWED_TRANSITIONS",
    "SCHEMA_VERSION",
    "AlreadyInitializedError",
    "ApprovalArtifactError",
    "ArtifactError",
    "ArtifactPathError",
    "ArtifactVerificationError",
    "DatabaseIntegrityError",
    "DeploymentAuthorizationError",
    "GateCriteria",
    "GateDecision",
    "GateRejectedError",
    "Lifecycle",
    "ManualApprovalRequired",
    "NotFoundError",
    "RegistryError",
    "RegistryNotInitializedError",
    "RiskPolicy",
    "RiskPolicyError",
    "StrategyRegistry",
    "TransitionError",
    "ValidationError",
    "initialize_registry",
]
