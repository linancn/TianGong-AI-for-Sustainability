"""
Adapters for sustainability reporting standards landing pages.

These sources provide downloadable artefacts (e.g., XBRL taxonomies,
workbooks). Verification focuses on confirming that the public landing pages
are reachable so operators receive deterministic guidance before attempting
the heavier ingestion steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient


class StandardsLandingClient(BaseAPIClient):
    """Generic client that issues lightweight GET requests for standards landing pages."""

    def fetch_page(self, path: str = "/") -> str:
        response = self._request("GET", path)
        return response.text


@dataclass(slots=True)
class GriTaxonomyAdapter(DataSourceAdapter):
    """Verify availability of the GRI taxonomy landing page."""

    source_id: str = "gri_taxonomy"
    client: StandardsLandingClient = field(default_factory=lambda: StandardsLandingClient(base_url="https://www.globalreporting.org"))
    verification_path: str = "/how-to-use-the-gri-standards/gri-standards-english-language/"

    def verify(self) -> VerificationResult:
        try:
            content = self.client.fetch_page(self.verification_path)
        except APIError as exc:
            return VerificationResult(
                success=False,
                message=f"GRI taxonomy verification failed: {exc}",
            )

        snippet: Optional[str] = None
        marker = "GRI Standards"
        if marker in content:
            snippet = marker

        details = {"marker": snippet} if snippet else None
        return VerificationResult(
            success=True,
            message="GRI taxonomy landing page reachable.",
            details=details,
        )


@dataclass(slots=True)
class GhgProtocolWorkbooksAdapter(DataSourceAdapter):
    """Verify availability of the GHG protocol calculation tools page."""

    source_id: str = "ghg_protocol_workbooks"
    client: StandardsLandingClient = field(default_factory=lambda: StandardsLandingClient(base_url="https://ghgprotocol.org"))
    verification_path: str = "/calculation-tools"

    def verify(self) -> VerificationResult:
        try:
            content = self.client.fetch_page(self.verification_path)
        except APIError as exc:
            return VerificationResult(
                success=False,
                message=f"GHG protocol workbooks verification failed: {exc}",
            )

        snippet: Optional[str] = None
        marker = "Calculation Tools"
        if marker in content:
            snippet = marker

        details = {"marker": snippet} if snippet else None
        return VerificationResult(
            success=True,
            message="GHG protocol calculation tools page reachable.",
            details=details,
        )
