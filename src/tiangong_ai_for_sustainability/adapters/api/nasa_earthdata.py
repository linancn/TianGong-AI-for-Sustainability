"""
NASA Earthdata Common Metadata Repository (CMR) client and adapter.

The CMR search API is publicly accessible for metadata queries, which lets us
verify connectivity and basic functionality without requiring download
credentials. Higher-level workflows can layer authenticated requests when
Earthdata Login credentials are configured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://cmr.earthdata.nasa.gov"


class NasaEarthdataClient(BaseAPIClient):
    """Thin client for NASA Earthdata CMR metadata search."""

    def __init__(self, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 20.0) -> None:
        headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def search_collections(self, *, keyword: str, page_size: int = 5) -> Dict[str, Any]:
        """
        Perform a simple keyword search against the collections endpoint.

        Parameters
        ----------
        keyword:
            Free-text keyword used to scope the query.
        page_size:
            Number of results to fetch (defaults to 5 and capped at 200 to match
            the API contract).
        """

        params = {
            "keyword": keyword,
            "page_size": max(1, min(page_size, 200)),
        }
        payload = self._get_json("/search/collections.json", params=params)
        if not isinstance(payload, dict):
            raise APIError("Unexpected response type from NASA Earthdata collections search.")
        return payload


def _extract_first_entry(payload: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """Return the first collection entry from a CMR payload, if present."""

    feed = payload.get("feed")
    if not isinstance(feed, Mapping):
        return None
    entries = feed.get("entry")
    if isinstance(entries, Iterable):
        for entry in entries:
            if isinstance(entry, Mapping):
                return entry
    return None


@dataclass(slots=True)
class NasaEarthdataAdapter(DataSourceAdapter):
    """Adapter used for registry verification."""

    source_id: str = "nasa_earthdata"
    client: NasaEarthdataClient = field(default_factory=NasaEarthdataClient)
    verification_keyword: str = "MODIS"

    def verify(self) -> VerificationResult:
        try:
            payload = self.client.search_collections(keyword=self.verification_keyword, page_size=1)
        except APIError as exc:
            return VerificationResult(
                success=False,
                message=f"NASA Earthdata verification failed: {exc}",
            )

        entry = _extract_first_entry(payload)
        if entry is None:
            return VerificationResult(
                success=False,
                message="NASA Earthdata verification failed: collections search returned no entries.",
            )

        details: Dict[str, Any] = {}
        concept_id = entry.get("id") or entry.get("concept_id")
        short_name = entry.get("short_name")
        title = entry.get("title")
        if isinstance(concept_id, str):
            details["concept_id"] = concept_id
        if isinstance(short_name, str):
            details["short_name"] = short_name
        if isinstance(title, str):
            details["title"] = title

        return VerificationResult(
            success=True,
            message="NASA Earthdata CMR metadata search reachable.",
            details=details or None,
        )
