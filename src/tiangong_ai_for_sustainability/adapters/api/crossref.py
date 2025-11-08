"""
Crossref REST API client and verification adapter.

Reference: https://api.crossref.org/swagger-ui/index.html
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://api.crossref.org"
_VERIFICATION_DOI = "10.1038/nphys1170"


class CrossrefClient(BaseAPIClient):
    """Minimal Crossref client for deterministic metadata retrieval."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        default_headers: Optional[MutableMapping[str, str]] = None,
        mailto: Optional[str] = None,
    ) -> None:
        headers: MutableMapping[str, str] = {"User-Agent": "tiangong-ai-sustainability-cli"}
        if default_headers:
            headers.update(default_headers)
        if mailto:
            headers["User-Agent"] = f"{headers['User-Agent']} (mailto:{mailto})"
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)
        self.mailto = mailto

    def _augment_params(self, params: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        merged: Dict[str, Any] = dict(params or {})
        if self.mailto and "mailto" not in merged:
            merged["mailto"] = self.mailto
        return merged

    def search_works(
        self,
        *,
        query: Optional[str] = None,
        filters: Optional[Mapping[str, Any]] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        rows: int = 20,
        select: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"rows": max(1, min(rows, 1000))}
        if query:
            params["query"] = query
        if filters:
            filter_expr = self._serialise_filters(filters)
            if filter_expr:
                params["filter"] = filter_expr
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if select:
            params["select"] = ",".join(select)
        payload = self._get_json("/works", params=self._augment_params(params))
        if not isinstance(payload, dict):
            raise APIError("Unexpected payload from Crossref works search.")
        return payload

    def get_work(self, doi: str, *, select: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        # Note: Crossref's works/{doi} route does not accept the `select` parameter.
        payload = self._get_json(f"/works/{doi}", params=self._augment_params({}))
        if not isinstance(payload, dict):
            raise APIError("Unexpected payload from Crossref work lookup.")
        message = payload.get("message")
        if not isinstance(message, dict):
            raise APIError("Crossref work payload missing 'message' object.")
        return message

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
class CrossrefAdapter(DataSourceAdapter):
    """Adapter used for registry verification."""

    source_id: str = "crossref"
    client: CrossrefClient = field(default_factory=CrossrefClient)

    def verify(self) -> VerificationResult:
        if not getattr(self.client, "mailto", None):
            return VerificationResult(
                success=False,
                message="Crossref API requires a contact email. Configure crossref.mailto or TIANGONG_CROSSREF_MAILTO.",
                details={"reason": "missing-mailto"},
            )
        try:
            payload = self.client.get_work(_VERIFICATION_DOI, select=["title", "issued"])
        except APIError as exc:
            return VerificationResult(success=False, message=f"Crossref API verification failed: {exc}")

        title = _coerce_title(payload.get("title"))
        issued_year = _extract_year(payload.get("issued"))
        details = {"sample_title": title}
        if issued_year is not None:
            details["issued_year"] = issued_year
        return VerificationResult(
            success=True,
            message="Crossref API reachable.",
            details=details,
        )


def _coerce_title(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and value:
        head = value[0]
        if isinstance(head, str):
            return head
    return None


def _extract_year(value: Any) -> Optional[int]:
    if not isinstance(value, dict):
        return None
    parts = value.get("date-parts")
    if not isinstance(parts, list) or not parts:
        return None
    first = parts[0]
    if not isinstance(first, (list, tuple)) or not first:
        return None
    year = first[0]
    if isinstance(year, int):
        return year
    try:
        return int(year)
    except (TypeError, ValueError):
        return None
