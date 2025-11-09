"""
Open Supply Hub facility registry client and adapter.

The API exposes supply-chain facility metadata with optional authenticated
access for higher paging limits. Verification performs a lightweight facility
query so the CLI can surface install or credential guidance deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://api.opensupplyhub.org"


class OpenSupplyHubClient(BaseAPIClient):
    """HTTP client for the Open Supply Hub facilities API."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        api_key: Optional[str] = None,
    ) -> None:
        headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        if api_key:
            headers["Authorization"] = f"Token {api_key}"
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)
        self.api_key = api_key

    def list_facilities(self, *, limit: int = 5) -> Dict[str, Any]:
        params = {"limit": max(1, min(limit, 50))}
        payload = self._get_json("/api/facilities/", params=params)
        if not isinstance(payload, Mapping):
            raise APIError("Unexpected payload type from Open Supply Hub facilities endpoint.")
        return dict(payload)


@dataclass(slots=True)
class OpenSupplyHubAdapter(DataSourceAdapter):
    """Adapter used for registry verification of Open Supply Hub."""

    source_id: str = "open_supply_hub"
    client: OpenSupplyHubClient = field(default_factory=OpenSupplyHubClient)

    def verify(self) -> VerificationResult:
        try:
            payload = self.client.list_facilities(limit=1)
        except APIError as exc:
            return VerificationResult(
                success=False,
                message=f"Open Supply Hub verification failed: {exc}",
            )

        features = payload.get("results") or payload.get("features")
        facility_name: Optional[str] = None
        if isinstance(features, list) and features:
            entry = features[0]
            if isinstance(entry, Mapping):
                properties = entry.get("properties") if isinstance(entry.get("properties"), Mapping) else entry
                if isinstance(properties, Mapping):
                    raw_name = properties.get("name") or properties.get("facility_name")
                    if isinstance(raw_name, str):
                        facility_name = raw_name

        details = {"facility": facility_name} if facility_name else None
        return VerificationResult(
            success=True,
            message="Open Supply Hub facility registry reachable.",
            details=details,
        )
