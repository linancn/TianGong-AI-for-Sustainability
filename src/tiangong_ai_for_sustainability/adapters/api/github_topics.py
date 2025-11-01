"""
GitHub Topics API client.

Uses the repository search endpoint with topic qualifiers. Authenticated tokens
increase rate limits but are optional for basic usage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://api.github.com"


class GitHubTopicsClient(BaseAPIClient):
    """Wrapper around GitHub's search API for topic discovery."""

    def __init__(
        self,
        *,
        token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "tiangong-ai-sustainability-cli",
        }
        resolved_token = token or os.getenv("GITHUB_TOKEN")
        if resolved_token:
            headers["Authorization"] = f"Bearer {resolved_token}"
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def search_repositories(
        self,
        topic: str,
        *,
        per_page: int = 10,
        sort: str = "stars",
        order: str = "desc",
    ) -> Dict[str, Any]:
        params = {
            "q": f"topic:{topic}",
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
        }
        data = self._get_json("/search/repositories", params=params)
        if not isinstance(data, dict):
            raise APIError("Unexpected payload for GitHub repository search.")
        return data


@dataclass(slots=True)
class GitHubTopicsAdapter(DataSourceAdapter):
    """Adapter for verifying GitHub API access."""

    source_id: str = "github_topics"
    client: GitHubTopicsClient = field(default_factory=GitHubTopicsClient)

    def verify(self) -> VerificationResult:
        try:
            payload = self.client.search_repositories("sustainability", per_page=1)
        except APIError as exc:
            return VerificationResult(success=False, message=f"GitHub API verification failed: {exc}")

        total = payload.get("total_count", 0)
        items: List[Dict[str, Any]] = payload.get("items") or []
        if not items:
            return VerificationResult(success=False, message="GitHub topic search returned no repositories.")

        repo = items[0]
        name = repo.get("full_name", "unknown")
        return VerificationResult(
            success=True,
            message="GitHub Topics API reachable.",
            details={"total_count": total, "sample_repo": name},
        )
