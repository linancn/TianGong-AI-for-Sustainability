"""
Dify Knowledge Base REST client and adapter.

This adapter targets the `/datasets/{dataset_id}/retrieve` endpoint for retrieving
curated chunks from a Dify knowledge base.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://api.dify.ai/v1"
DEFAULT_TEST_QUERY = "sustainability research evidence"


class DifyKnowledgeBaseClient(BaseAPIClient):
    """Minimal client for the Dify knowledge base retrieve endpoint."""

    DEFAULT_BASE_URL = DEFAULT_BASE_URL

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ) -> None:
        headers: MutableMapping[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)
        self.api_key = api_key

    def retrieve(
        self,
        dataset_id: str,
        *,
        query: str,
        retrieval_model: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        if not dataset_id:
            raise APIError("dataset_id is required for retrieval.")
        body: MutableMapping[str, Any] = {"query": query}
        if retrieval_model:
            body["retrieval_model"] = retrieval_model
        data = self._post_json(f"/datasets/{dataset_id}/retrieve", json_body=body)
        if not isinstance(data, Mapping):
            raise APIError("Unexpected payload from Dify retrieve endpoint.")
        return data


def _looks_like_placeholder(value: str) -> bool:
    trimmed = value.strip()
    return not trimmed or (trimmed.startswith("<") and trimmed.endswith(">"))


@dataclass(slots=True)
class DifyKnowledgeBaseAdapter(DataSourceAdapter):
    """Adapter to verify Dify knowledge base REST connectivity."""

    source_id: str = "dify_knowledge"
    client: DifyKnowledgeBaseClient = field(default_factory=lambda: DifyKnowledgeBaseClient(api_key=None))
    dataset_id: Optional[str] = None
    test_query: str = DEFAULT_TEST_QUERY
    retrieval_model: Optional[Mapping[str, Any]] = None

    def verify(self) -> VerificationResult:
        if not self.client.api_key or _looks_like_placeholder(self.client.api_key):
            return VerificationResult(
                success=False,
                message=("Dify knowledge base API key missing. " "Set [dify_knowledge].api_key or TIANGONG_DIFY_API_KEY."),
            )

        if not self.dataset_id or _looks_like_placeholder(self.dataset_id):
            return VerificationResult(
                success=False,
                message=("Dify knowledge base dataset_id is not configured. " "Set [dify_knowledge].dataset_id or TIANGONG_DIFY_DATASET_ID."),
            )

        try:
            response = self.client.retrieve(
                dataset_id=self.dataset_id,
                query=self.test_query,
                retrieval_model=self.retrieval_model,
            )
        except APIError as exc:
            return VerificationResult(
                success=False,
                message=f"Dify knowledge base API verification failed: {exc}",
                details={"dataset_id": self.dataset_id},
            )

        records = response.get("records") if isinstance(response, Mapping) else None
        record_count = len(records) if isinstance(records, list) else 0
        sample_content = None
        sample_document = None
        if record_count:
            first = records[0]
            if isinstance(first, Mapping):
                segment = first.get("segment")
                if isinstance(segment, Mapping):
                    content = segment.get("content")
                    if isinstance(content, str):
                        sample_content = content[:200]
                    document = segment.get("document")
                    if isinstance(document, Mapping):
                        doc_name = document.get("name")
                        if isinstance(doc_name, str):
                            sample_document = doc_name

        details = {"record_count": record_count, "dataset_id": self.dataset_id}
        if sample_content:
            details["sample_content"] = sample_content
        if sample_document:
            details["sample_document"] = sample_document

        return VerificationResult(
            success=True,
            message="Dify knowledge base retrieval endpoint reachable.",
            details=details,
        )


__all__ = ["DifyKnowledgeBaseAdapter", "DifyKnowledgeBaseClient"]
