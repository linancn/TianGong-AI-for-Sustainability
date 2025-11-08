"""
Adapter for the IMF Climate Change Dashboard.

The public dashboard is served as a static site; we verify availability by
retrieving the landing page and confirming the expected title string.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://climatedata.imf.org"
EXPECTED_TITLE = "Macroeconomic Climate Indicators Dashboard"


class IMFClimateClient(BaseAPIClient):
    """HTTP client for the IMF climate dashboard front-end."""

    def __init__(self, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 20.0) -> None:
        headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def fetch_homepage_title(self) -> str:
        response = self._request("GET", "/")
        text = response.text
        if EXPECTED_TITLE not in text:
            raise APIError("IMF climate dashboard response did not include the expected title.")
        return EXPECTED_TITLE


@dataclass(slots=True)
class IMFClimateAdapter(DataSourceAdapter):
    """Registry adapter for the IMF climate dashboard."""

    source_id: str = "imf_climate_dashboard"
    client: IMFClimateClient = field(default_factory=IMFClimateClient)

    def verify(self) -> VerificationResult:
        try:
            title = self.client.fetch_homepage_title()
        except APIError as exc:
            return VerificationResult(success=False, message=f"IMF climate dashboard verification failed: {exc}")

        return VerificationResult(
            success=True,
            message="IMF climate dashboard homepage reachable.",
            details={"title": title},
        )
