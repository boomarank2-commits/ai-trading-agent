"""Domain errors for the local strategy registry.

The registry deliberately exposes a small, typed error hierarchy so callers and
the JSON CLI can fail closed without having to interpret SQLite error strings.
"""

from __future__ import annotations

from typing import Any


class RegistryError(Exception):
    """Base class for all expected registry failures."""


class RegistryNotInitializedError(RegistryError):
    """Raised when a database is missing or does not contain our schema."""


class AlreadyInitializedError(RegistryError):
    """Raised when initialization would overwrite an existing registry."""


class ValidationError(RegistryError):
    """Raised when caller-provided data is invalid."""


class RiskPolicyError(ValidationError):
    """Raised when a risk policy exceeds a hard safety boundary."""


class NotFoundError(RegistryError):
    """Raised when a strategy or version cannot be found."""


class ArtifactError(RegistryError):
    """Base class for artifact confinement and integrity failures."""


class ArtifactPathError(ArtifactError):
    """Raised when an artifact is outside the configured safe roots."""


class ArtifactVerificationError(ArtifactError):
    """Raised when an artifact is missing, unstable, or hash-mismatched."""


class TransitionError(RegistryError):
    """Raised for a lifecycle transition that is not explicitly allowed."""


class ManualApprovalRequired(TransitionError):
    """Raised when a live-capital stage lacks explicit human approval."""


class ApprovalArtifactError(ManualApprovalRequired):
    """Raised when a one-time human approval artifact is invalid or unusable."""


class GateRejectedError(TransitionError):
    """Raised when deterministic promotion criteria are not met."""

    def __init__(self, message: str, *, decision: Any | None = None) -> None:
        super().__init__(message)
        self.decision = decision


class DatabaseIntegrityError(RegistryError):
    """Raised when SQLite state violates an invariant or cannot be trusted."""


class DeploymentAuthorizationError(RegistryError):
    """Raised when a launcher cannot prove an exact deployable version."""
