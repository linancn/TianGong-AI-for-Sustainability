"""
arXiv client and adapter built on top of https://github.com/lukasschwab/arxiv.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import arxiv

from ..base import AdapterError, DataSourceAdapter, VerificationResult

_VERIFICATION_ID = "1707.08567"


class ArxivAPIError(AdapterError):
    """Raised when arXiv operations fail."""


def _format_datetime(value: Optional[datetime]) -> Optional[str]:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return None


def _extract_year(value: Optional[datetime]) -> Optional[int]:
    if isinstance(value, datetime):
        return value.year
    return None


def _format_authors(authors: Iterable[object]) -> List[str]:
    names: List[str] = []
    for author in authors:
        name = getattr(author, "name", None)
        if isinstance(name, str) and name:
            names.append(name)
    return names


def _serialise_result(result: arxiv.Result) -> Dict[str, object]:
    short_id = result.get_short_id() if hasattr(result, "get_short_id") else None
    return {
        "id": short_id or result.entry_id,
        "entry_id": result.entry_id,
        "arxiv_id": short_id,
        "title": result.title.strip(),
        "summary": result.summary.strip(),
        "published": _format_datetime(result.published),
        "updated": _format_datetime(result.updated),
        "year": _extract_year(result.published),
        "doi": result.doi,
        "primary_category": result.primary_category,
        "categories": list(result.categories),
        "pdf_url": result.pdf_url,
        "links": [link.href for link in result.links if getattr(link, "href", None)],
        "authors": _format_authors(result.authors),
    }


@dataclass(slots=True)
class ArxivClient:
    """Thin wrapper around :mod:`arxiv` providing structured dictionaries."""

    client: arxiv.Client = field(default_factory=arxiv.Client)

    def search_papers(
        self,
        query: str,
        *,
        max_results: int = 10,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
    ) -> List[Dict[str, object]]:
        try:
            search = arxiv.Search(query=query, max_results=max_results, sort_by=sort_by)
            results = list(self.client.results(search))
        except Exception as exc:  # pragma: no cover - depends on upstream
            raise ArxivAPIError(f"Failed to query arXiv: {exc}") from exc
        return [_serialise_result(result) for result in results]

    def fetch_by_id(self, arxiv_id: str) -> Dict[str, object]:
        try:
            search = arxiv.Search(id_list=[arxiv_id], max_results=1)
            iterator = self.client.results(search)
            result = next(iterator, None)
        except StopIteration:  # pragma: no cover - defensive
            result = None
        except Exception as exc:  # pragma: no cover - depends on upstream
            raise ArxivAPIError(f"Failed to retrieve arXiv record {arxiv_id}: {exc}") from exc
        if result is None:
            raise ArxivAPIError(f"arXiv record '{arxiv_id}' not found.")
        return _serialise_result(result)


@dataclass(slots=True)
class ArxivAdapter(DataSourceAdapter):
    """Adapter used for registry verification."""

    source_id: str = "arxiv"
    client: ArxivClient = field(default_factory=ArxivClient)

    def verify(self) -> VerificationResult:
        try:
            payload = self.client.fetch_by_id(_VERIFICATION_ID)
        except AdapterError as exc:
            return VerificationResult(success=False, message=f"arXiv API verification failed: {exc}")

        return VerificationResult(
            success=True,
            message="arXiv API reachable.",
            details={
                "sample_id": payload.get("arxiv_id") or payload.get("id"),
                "sample_title": payload.get("title"),
                "published": payload.get("published"),
            },
        )
