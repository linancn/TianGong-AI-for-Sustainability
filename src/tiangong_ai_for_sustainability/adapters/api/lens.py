"""
Lens.org scholarly API client and adapter.

Lens provides scholarly and patent metadata over a REST API that requires an API
token. The client issues a minimal search query for verification so the CLI can
surface actionable guidance when credentials are missing or invalid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://api.lens.org"


class LensOrgClient(BaseAPIClient):
    """Minimalistic Lens.org client for verification purposes."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        api_key: Optional[str] = None,
    ) -> None:
        headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        if api_key:
            headers["Authorization"] = api_key
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)
        self.api_key = api_key

    def sample_search(self) -> Dict[str, Any]:
        if not self.api_key:
            raise APIError("Lens API key is not configured.")

        payload = self._post_json(
            "/scholarly/search",
            json_body={
                "query": {"match_all": {}},
                "size": 1,
                "include": ["lens_id", "title"],
            },
        )
        if not isinstance(payload, dict):
            raise APIError("Unexpected payload type from Lens.org scholarly search.")
        if payload.get("errors"):
            raise APIError(f"Lens.org API reported errors: {payload['errors']}")
        return payload


@dataclass(slots=True)
class LensOrgAdapter(DataSourceAdapter):
    """Adapter used for registry verification of Lens.org."""

    source_id: str = "lens_org_api"
    client: LensOrgClient = field(default_factory=LensOrgClient)

    def verify(self) -> VerificationResult:
        if not getattr(self.client, "api_key", None):
            return VerificationResult(
                success=False,
                message=("Lens API key is not configured. Add [lens_org_api] credentials with api_key " "in .secrets/secrets.toml or set TIANGONG_LENS_API_KEY."),
            )

        try:
            payload = self.client.sample_search()
        except APIError as exc:
            return VerificationResult(success=False, message=f"Lens.org API verification failed: {exc}")

        data = payload.get("data")
        if isinstance(data, list) and data:
            entry = data[0]
            lens_id = entry.get("lens_id") if isinstance(entry, dict) else None
            title = entry.get("title") if isinstance(entry, dict) else None
        else:
            lens_id = None
            title = None

        details = {}
        if lens_id:
            details["lens_id"] = lens_id
        if title:
            details["title"] = title

        return VerificationResult(
            success=True,
            message="Lens.org scholarly API reachable.",
            details=details or None,
        )
