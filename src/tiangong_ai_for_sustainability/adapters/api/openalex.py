"""
OpenAlex Works API client.

Reference: https://docs.openalex.org/api-entities/works
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, Mapping, MutableMapping, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://api.openalex.org"


class OpenAlexClient(BaseAPIClient):
    """Minimal OpenAlex client for deterministic literature retrieval."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        default_headers: Optional[MutableMapping[str, str]] = None,
        mailto: Optional[str] = None,
    ) -> None:
        headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        if default_headers:
            headers.update(default_headers)
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)
        self.mailto = mailto

    def search_works(
        self,
        *,
        search: Optional[str] = None,
        filters: Optional[Mapping[str, Any]] = None,
        sort: Optional[str] = None,
        select: Optional[Iterable[str]] = None,
        cursor: str = "*",
        per_page: int = 200,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"cursor": cursor, "per-page": max(1, min(per_page, 200))}
        if search:
            params["search"] = search
        if filters:
            params["filter"] = self._serialise_filters(filters)
        if sort:
            params["sort"] = sort
        if select:
            params["select"] = ",".join(select)
        if self.mailto:
            params.setdefault("mailto", self.mailto)
        payload = self._get_json("/works", params=params)
        if not isinstance(payload, dict):
            raise APIError("Unexpected payload from OpenAlex works search.")
        return payload

    def iterate_works(
        self,
        *,
        search: Optional[str] = None,
        filters: Optional[Mapping[str, Any]] = None,
        sort: Optional[str] = None,
        select: Optional[Iterable[str]] = None,
        per_page: int = 200,
        max_pages: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        cursor = "*"
        pages = 0
        while True:
            payload = self.search_works(
                search=search,
                filters=filters,
                sort=sort,
                select=select,
                cursor=cursor,
                per_page=per_page,
            )
            results = payload.get("results") or []
            if not isinstance(results, list):
                raise APIError("OpenAlex works payload missing 'results' list.")
            for item in results:
                if isinstance(item, dict):
                    yield item

            meta = payload.get("meta") or {}
            if not isinstance(meta, dict):
                raise APIError("OpenAlex works payload missing 'meta' dictionary.")
            next_cursor = meta.get("next_cursor")
            pages += 1

            if not next_cursor:
                break
            if max_pages is not None and pages >= max_pages:
                break

            cursor = str(next_cursor)

    def get_work(self, work_id: str, *, select: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        params = {"select": ",".join(select)} if select else {}
        if self.mailto:
            params.setdefault("mailto", self.mailto)
        payload = self._get_json(f"/works/{work_id}", params=params)
        if not isinstance(payload, dict):
            raise APIError("Unexpected payload from OpenAlex work lookup.")
        return payload

    @staticmethod
    def _serialise_filters(filters: Mapping[str, Any]) -> str:
        entries: list[str] = []
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, (set, list, tuple)):
                for item in value:
                    entries.append(f"{key}:{item}")
            else:
                entries.append(f"{key}:{value}")
        return ",".join(entries)


@dataclass(slots=True)
class OpenAlexAdapter(DataSourceAdapter):
    """Adapter used for registry verification."""

    source_id: str = "openalex"
    client: OpenAlexClient = field(default_factory=OpenAlexClient)

    def verify(self) -> VerificationResult:
        try:
            payload = self.client.get_work("W3186199070", select=["id", "display_name", "cited_by_count"])
        except APIError as exc:
            return VerificationResult(success=False, message=f"OpenAlex API verification failed: {exc}")

        return VerificationResult(
            success=True,
            message="OpenAlex API reachable.",
            details={
                "sample_work": payload.get("display_name"),
                "cited_by_count": payload.get("cited_by_count"),
            },
        )
