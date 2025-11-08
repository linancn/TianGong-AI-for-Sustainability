"""
World Bank Open Data API client.

The World Bank exposes sustainability-relevant indicators through the v2
REST API. Responses are deterministic when ``format=json`` and ``per_page``
parameters are supplied, which keeps verification predictable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Optional, Tuple

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://api.worldbank.org/v2"
_VERIFICATION_INDICATOR = "EN.ATM.CO2E.PC"


class WorldBankClient(BaseAPIClient):
    """Minimal client for the World Bank v2 REST API."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        default_headers: Optional[MutableMapping[str, str]] = None,
    ) -> None:
        headers: MutableMapping[str, str] = {"Accept": "application/json"}
        if default_headers:
            headers.update(default_headers)
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def fetch_indicator(
        self,
        indicator_id: str,
        *,
        per_page: int = 1,
    ) -> Tuple[Mapping[str, Any], Mapping[str, Any]]:
        """
        Retrieve metadata and the first result row for a specific indicator.

        Returns a tuple of ``(metadata, entry)`` where ``metadata`` is the API
        paging descriptor and ``entry`` contains the indicator description.
        """

        params = {
            "format": "json",
            "per_page": max(1, min(per_page, 100)),
        }
        payload = self._get_json(f"/indicator/{indicator_id}", params=params)

        if not isinstance(payload, list) or len(payload) < 2:
            raise APIError("Unexpected payload structure from World Bank indicator endpoint.")

        metadata, entries = payload[0], payload[1]
        if not isinstance(metadata, dict):
            raise APIError("World Bank indicator metadata missing.")
        if not isinstance(entries, list):
            raise APIError("World Bank indicator data list missing.")
        if not entries:
            raise APIError(f"World Bank indicator {indicator_id} returned no entries.")

        first_entry = entries[0]
        if not isinstance(first_entry, dict):
            raise APIError("World Bank indicator entry is not a dictionary.")

        return metadata, first_entry


@dataclass(slots=True)
class WorldBankAdapter(DataSourceAdapter):
    """Adapter used for registry verification."""

    source_id: str = "world_bank_sustainability"
    client: WorldBankClient = field(default_factory=WorldBankClient)
    verification_indicator: str = _VERIFICATION_INDICATOR

    def verify(self) -> VerificationResult:
        try:
            metadata, indicator = self.client.fetch_indicator(self.verification_indicator, per_page=1)
        except APIError as exc:
            return VerificationResult(success=False, message=f"World Bank API verification failed: {exc}")

        indicator_id = indicator.get("id", self.verification_indicator)
        indicator_name = indicator.get("name", "Unknown indicator")

        source = indicator.get("source")
        if isinstance(source, dict):
            source_name = source.get("value")
        else:
            source_name = None

        message = "World Bank API reachable." if metadata.get("total") else "World Bank API reachable but no metadata entries were reported."

        return VerificationResult(
            success=True,
            message=message,
            details={
                "indicator_id": indicator_id,
                "indicator_name": indicator_name,
                "source": source_name,
            },
        )
