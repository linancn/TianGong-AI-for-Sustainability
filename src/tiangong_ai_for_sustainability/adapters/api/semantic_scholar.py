"""
Semantic Scholar Graph API client.

API reference: https://api.semanticscholar.org/api-docs/graph
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarClient(BaseAPIClient):
    """Minimal Semantic Scholar client covering search and metadata retrieval."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
    ) -> None:
        default_headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        if api_key:
            default_headers["x-api-key"] = api_key
        super().__init__(base_url=base_url, timeout=timeout, default_headers=default_headers)

    def search_papers(
        self,
        query: str,
        *,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "query": query,
            "limit": min(limit, 100),
            "offset": offset,
        }
        if fields:
            params["fields"] = ",".join(fields)
        data = self._get_json("/paper/search", params=params)
        if not isinstance(data, dict):
            raise APIError("Unexpected payload for Semantic Scholar search.")
        return data

    def get_paper(self, paper_id: str, *, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        params = {"fields": ",".join(fields)} if fields else None
        data = self._get_json(f"/paper/{paper_id}", params=params)
        if not isinstance(data, dict):
            raise APIError("Unexpected payload for Semantic Scholar paper lookup.")
        return data


@dataclass(slots=True)
class SemanticScholarAdapter(DataSourceAdapter):
    """Adapter for registry verification."""

    source_id: str = "semantic_scholar"
    client: SemanticScholarClient = field(default_factory=SemanticScholarClient)

    def verify(self) -> VerificationResult:
        try:
            payload = self.client.get_paper("arXiv:1708.08021", fields=["title", "year"])
        except APIError as exc:
            return VerificationResult(success=False, message=f"Semantic Scholar API verification failed: {exc}")

        title = payload.get("title", "N/A")
        year = payload.get("year")
        return VerificationResult(
            success=True,
            message="Semantic Scholar API reachable.",
            details={"sample_title": title, "year": year},
        )
