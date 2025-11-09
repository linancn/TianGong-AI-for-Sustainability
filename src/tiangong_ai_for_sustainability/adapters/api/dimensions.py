"""
Dimensions.ai DSL API client and adapter.

The Dimensions platform exposes a DSL endpoint that requires an API token. This
module wraps the minimal functionality needed for verification while keeping
queries deterministic and low volume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://app.dimensions.ai/api/dsl/v2"
SAMPLE_QUERY = "search publications return publications[id + title] limit 1"


class DimensionsAIClient(BaseAPIClient):
    """Minimal client for the Dimensions DSL endpoint."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        api_key: Optional[str] = None,
    ) -> None:
        headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)
        self.api_key = api_key

    def sample_publications(self) -> Dict[str, Any]:
        if not self.api_key:
            raise APIError("Dimensions API key is not configured.")

        response = self._request(
            "POST",
            "",
            content=SAMPLE_QUERY.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
        )
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - depends on upstream
            raise APIError(f"Failed to decode Dimensions DSL response: {exc}") from exc

        if not isinstance(payload, dict):
            raise APIError("Unexpected payload type from Dimensions DSL endpoint.")

        if payload.get("errors"):
            raise APIError(f"Dimensions DSL returned errors: {payload['errors']}")
        return payload


@dataclass(slots=True)
class DimensionsAIAdapter(DataSourceAdapter):
    """Adapter used for registry verification of Dimensions.ai."""

    source_id: str = "dimensions_ai"
    client: DimensionsAIClient = field(default_factory=DimensionsAIClient)

    def verify(self) -> VerificationResult:
        if not getattr(self.client, "api_key", None):
            return VerificationResult(
                success=False,
                message=("Dimensions API key is not configured. Add [dimensions_ai] credentials with api_key " "in .secrets/secrets.toml or set TIANGONG_DIMENSIONS_API_KEY."),
            )

        try:
            payload = self.client.sample_publications()
        except APIError as exc:
            return VerificationResult(success=False, message=f"Dimensions API verification failed: {exc}")

        publications = payload.get("publications")
        if isinstance(publications, list) and publications:
            entry = publications[0]
            title = entry.get("title") if isinstance(entry, dict) else None
        else:
            title = None

        details = {}
        if title:
            details["sample_publication"] = title

        return VerificationResult(
            success=True,
            message="Dimensions DSL endpoint reachable.",
            details=details or None,
        )
