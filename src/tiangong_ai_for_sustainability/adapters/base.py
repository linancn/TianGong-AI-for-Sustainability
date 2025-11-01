"""
Base protocols for data source adapters.

Adapters are intentionally narrow in scope: they provide deterministic methods
for verifying connectivity and performing well-defined fetch operations. Higher
level orchestration (retry logic, caching, LLM prompting) is handled by service
modules to keep adapters reusable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Protocol


class AdapterError(RuntimeError):
    """Raised when an adapter encounters a non-recoverable error."""


@dataclass(slots=True)
class VerificationResult:
    """
    Structured response returned by adapter verification routines.

    Attributes
    ----------
    success:
        Indicates whether the verification succeeded.
    message:
        Human-readable summary.
    details:
        Optional structured metadata. Useful for surfacing rate limits, API
        versions, or feature flags.
    """

    success: bool
    message: str
    details: Optional[Mapping[str, object]] = None


class DataSourceAdapter(Protocol):
    """Protocol implemented by all data source adapters."""

    def verify(self) -> VerificationResult:
        """Perform a lightweight connectivity check."""

    @property
    def source_id(self) -> str:
        """Identifier matching the registry descriptor."""
