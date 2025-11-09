"""
Web of Science Starter API adapter.

This module integrates the Clarivate `wosstarter_python_client` package to
perform deterministic verification calls against the Web of Science Starter API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..base import AdapterError, DataSourceAdapter, VerificationResult

DEFAULT_BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1"


class WebOfScienceClient:
    """Thin wrapper around the Clarivate Web of Science Starter client."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        sample_query: str = "PY=2023",
        sample_limit: int = 1,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.sample_query = sample_query
        self.sample_limit = sample_limit

    def _load_sdk(self):
        try:
            from clarivate.wos_starter.client import ApiClient, Configuration
            from clarivate.wos_starter.client.api.documents_api import DocumentsApi
            from clarivate.wos_starter.client.rest import ApiException
        except ImportError as exc:  # pragma: no cover - defensive guard
            raise AdapterError("Missing dependency `clarivate-wos-starter-python-client`. Run `uv sync` to install the SDK.") from exc
        return ApiClient, Configuration, DocumentsApi, ApiException

    def sample_search(self) -> Dict[str, Any]:
        """Execute a minimal search to confirm API connectivity."""
        if not self.api_key:
            raise AdapterError("Web of Science API key is not configured.")

        ApiClient, Configuration, DocumentsApi, ApiException = self._load_sdk()

        try:
            configuration = Configuration(host=self.base_url)
        except Exception as exc:  # pragma: no cover - defensive guard
            raise AdapterError(f"Failed to initialise Web of Science client configuration: {exc}") from exc

        configuration.api_key["ClarivateApiKeyAuth"] = self.api_key

        try:
            with ApiClient(configuration) as api_client:
                documents_api = DocumentsApi(api_client)
                response = documents_api.documents_get(q=self.sample_query, limit=self.sample_limit)
        except ApiException as exc:
            raise AdapterError(f"Web of Science API returned an error: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise AdapterError(f"Unexpected error during Web of Science API request: {exc}") from exc

        data = response.to_dict() if hasattr(response, "to_dict") else response
        if not isinstance(data, dict):
            raise AdapterError("Unexpected payload type from Web of Science API.")
        if "error" in data:
            raise AdapterError(f"Web of Science API error: {data['error']}")
        return data


@dataclass(slots=True)
class WebOfScienceAdapter(DataSourceAdapter):
    """Adapter for registry verification of Web of Science."""

    source_id: str = "web_of_science"
    client: WebOfScienceClient = field(default_factory=WebOfScienceClient)

    def verify(self) -> VerificationResult:
        if not getattr(self.client, "api_key", None):
            return VerificationResult(
                success=False,
                message=("Web of Science API credentials are not configured. Add a [web_of_science] api_key entry " "to .secrets/secrets.toml or set TIANGONG_WOS_API_KEY."),
            )

        try:
            payload = self.client.sample_search()
        except AdapterError as exc:
            return VerificationResult(success=False, message=f"Web of Science Starter API verification failed: {exc}")

        hits = payload.get("hits") if isinstance(payload, dict) else None
        metadata = payload.get("metadata") if isinstance(payload, dict) else None

        details: Dict[str, Any] = {}
        if isinstance(metadata, dict):
            total = metadata.get("total")
            page = metadata.get("page")
            if isinstance(total, int):
                details["total_results"] = total
            if isinstance(page, int):
                details["page"] = page

        if isinstance(hits, list) and hits:
            first = hits[0]
            if isinstance(first, dict):
                title = first.get("title")
                uid = first.get("uid")
                identifiers = first.get("identifiers")
                if isinstance(title, str) and title:
                    details["sample_title"] = title
                if isinstance(uid, str) and uid:
                    details["sample_uid"] = uid
                if isinstance(identifiers, dict):
                    doi = identifiers.get("doi")
                    if isinstance(doi, str) and doi:
                        details["sample_doi"] = doi

        return VerificationResult(
            success=True,
            message="Web of Science Starter API reachable.",
            details=details or None,
        )
