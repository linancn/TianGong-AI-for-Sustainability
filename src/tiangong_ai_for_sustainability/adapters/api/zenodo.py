"""
Helpers for interacting with Zenodo communities.

Both IPCC and IPBES publish open datasets via dedicated Zenodo communities. The
client defined here keeps the interaction deterministic and reusable across
adapters that rely on those feeds.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional

from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://zenodo.org/api"


class ZenodoCommunityClient(BaseAPIClient):
    """Minimal wrapper around the Zenodo records search endpoint."""

    def __init__(self, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 20.0) -> None:
        headers = {"Accept": "application/json", "User-Agent": "tiangong-ai-sustainability-cli"}
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def list_recent_records(self, community_id: str, *, size: int = 1) -> List[Mapping[str, Any]]:
        params = {
            "communities": community_id,
            "size": max(1, min(size, 100)),
            "sort": "mostrecent",
        }
        payload = self._get_json("/records", params=params)
        if not isinstance(payload, Mapping):
            raise APIError("Unexpected payload from Zenodo API.")

        hits = payload.get("hits")
        if not isinstance(hits, Mapping):
            raise APIError("Zenodo payload missing 'hits' section.")

        records = hits.get("hits")
        if not isinstance(records, list):
            raise APIError("Zenodo payload missing records list.")

        normalised: List[Mapping[str, Any]] = []
        for entry in records:
            if isinstance(entry, Mapping):
                normalised.append(entry)

        return normalised

    def fetch_latest_title(self, community_id: str) -> Optional[str]:
        records = self.list_recent_records(community_id=community_id, size=1)
        if not records:
            return None
        record = records[0]
        metadata = record.get("metadata")
        if isinstance(metadata, Mapping):
            title = metadata.get("title")
            if isinstance(title, str):
                return title
        title = record.get("title")
        return title if isinstance(title, str) else None


def extract_record_doi(record: Mapping[str, Any]) -> Optional[str]:
    """Best-effort extraction of a DOI string from a Zenodo record."""

    metadata = record.get("metadata")
    if isinstance(metadata, Mapping):
        doi = metadata.get("doi")
        if isinstance(doi, str) and doi:
            return doi

    doi = record.get("doi")
    if isinstance(doi, str) and doi:
        return doi
    doi_url = record.get("doi_url")
    if isinstance(doi_url, str) and doi_url:
        return doi_url
    return None
