"""
OSDG SDG classification API client.

The upstream service occasionally introduces captchas or web challenges. The
client keeps the surface tiny so the CLI can swap in alternative endpoints (for
example, self-hosted deployments) by configuring the base URL and API token via
secrets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://osdg.ai/api"


class OSDGClient(BaseAPIClient):
    """Minimal client for the public OSDG classification endpoint."""

    def __init__(
        self,
        *,
        api_token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        headers = {"Accept": "application/json", "User-Agent": "tiangong-ai-sustainability-cli"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def classify_text(self, text: str, *, language: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"text": text}
        if language:
            payload["language"] = language
        data = self._post_json("/classify/text", json_body=payload)
        if not isinstance(data, dict):
            raise APIError("Unexpected payload for OSDG text classification.")
        return data


@dataclass(slots=True)
class OSDGAdapter(DataSourceAdapter):
    """Adapter used for registry verification."""

    source_id: str = "osdg_api"
    client: OSDGClient = field(default_factory=OSDGClient)

    SAMPLE_TEXT: str = (
        "Sustainable development requires coordinated economic, social, and environmental policies to " "tackle climate change while protecting vulnerable populations and biodiversity."
    )

    def verify(self) -> VerificationResult:
        try:
            response = self.client.classify_text(self.SAMPLE_TEXT)
        except APIError as exc:
            return VerificationResult(
                success=False,
                message="OSDG API verification failed. Configure a working endpoint or API token.",
                details={"error": str(exc)},
            )

        return VerificationResult(
            success=True,
            message="OSDG API reachable.",
            details={"keys": list(response.keys())},
        )
