"""Deterministic literature aggregation workflow."""

from __future__ import annotations

from dataclasses import dataclass
from logging import LoggerAdapter
from typing import Any, Dict, Iterable, List, Optional

from ..adapters.api.base import APIError
from ..core.logging import get_logger
from ..services import ResearchServices
from .steps import discover_papers, match_sdg_goals


@dataclass(slots=True)
class PaperSearchArtifacts:
    """Outputs produced by :func:`run_paper_search`."""

    query: str
    sdg_matches: List[Dict[str, Any]]
    semantic_scholar: List[Dict[str, Any]]
    openalex: List[Dict[str, Any]]
    notes: List[str]
    citation_edges: Optional[List[Dict[str, str]]]
    plan: Optional[List[str]] = None


def run_paper_search(
    services: ResearchServices,
    *,
    query: str,
    sdg_context: Optional[str] = None,
    limit: int = 10,
    include_openalex: bool = False,
    include_citations: bool = False,
) -> PaperSearchArtifacts:
    """
    Aggregate literature evidence across Semantic Scholar and (optionally) OpenAlex.
    """

    context = getattr(services, "context", None)
    options = getattr(context, "options", None)
    is_dry_run = bool(getattr(options, "dry_run", False))

    logger = _resolve_logger(services, "workflow.find_papers")
    logger.info(
        "Starting paper search",
        extra={
            "query": query,
            "limit": limit,
            "include_openalex": include_openalex,
            "include_citations": include_citations,
            "dry_run": is_dry_run,
        },
    )

    plan_steps = [
        "Match SDG goals using UNSDG catalogue.",
        "Query Semantic Scholar for representative papers.",
    ]
    if include_openalex:
        plan_steps.append("Query OpenAlex works API for complementary records.")
    else:
        plan_steps.append("Skip OpenAlex enrichment (disabled).")
    if include_citations:
        plan_steps.append("Build citation edge list from OpenAlex references.")

    if is_dry_run:
        logger.info("Dry-run plan generated", extra={"steps": plan_steps})
        return PaperSearchArtifacts(
            query=query,
            sdg_matches=[],
            semantic_scholar=[],
            openalex=[],
            notes=[],
            citation_edges=None,
            plan=plan_steps,
        )

    notes: List[str] = []
    sdg_matches: List[Dict[str, Any]] = []
    semantic_results: List[Dict[str, Any]] = []

    sdg_basis = (sdg_context or query).strip()

    if context and not context.is_enabled("un_sdg_api"):
        notes.append("UN SDG API disabled; skipping SDG alignment.")
    else:
        sdg_matches = match_sdg_goals(services, sdg_basis, logger)

    if context and not context.is_enabled("semantic_scholar"):
        notes.append("Semantic Scholar source disabled in the current execution context.")
    else:
        try:
            semantic_results = discover_papers(services, query, limit, logger=logger)
        except APIError as exc:
            notes.append(f"Semantic Scholar lookup failed: {exc}")

    openalex_results: List[Dict[str, Any]] = []
    citation_edges: Optional[List[Dict[str, str]]] = None

    use_openalex = include_openalex and (context is None or context.is_enabled("openalex"))
    if include_openalex and not use_openalex:
        notes.append("OpenAlex enrichment skipped: data source disabled.")
    elif use_openalex:
        try:
            openalex_results = _collect_openalex_records(services, query, limit, logger)
        except APIError as exc:
            notes.append(f"OpenAlex lookup failed: {exc}")
        else:
            if include_citations:
                citation_edges = _build_citation_edges(openalex_results, limit=limit * 5)

    return PaperSearchArtifacts(
        query=query,
        sdg_matches=sdg_matches,
        semantic_scholar=semantic_results,
        openalex=openalex_results,
        notes=notes,
        citation_edges=citation_edges,
        plan=None,
    )


def _resolve_logger(services: ResearchServices, name: str) -> LoggerAdapter:
    if hasattr(services, "context") and hasattr(services.context, "get_logger"):
        return services.context.get_logger(name)
    return get_logger(name)


def _collect_openalex_records(
    services: ResearchServices,
    query: str,
    limit: int,
    logger: LoggerAdapter,
) -> List[Dict[str, Any]]:
    client = services.openalex_client()
    records: List[Dict[str, Any]] = []
    per_page = min(max(limit, 1), 50)
    for item in client.iterate_works(
        search=query,
        select=[
            "id",
            "display_name",
            "publication_year",
            "doi",
            "cited_by_count",
            "referenced_works",
            "authorships",
        ],
        per_page=per_page,
        max_pages=1,
    ):
        if not isinstance(item, dict):
            continue
        authors = _extract_openalex_authors(item.get("authorships"))
        records.append(
            {
                "id": item.get("id"),
                "title": item.get("display_name"),
                "year": item.get("publication_year"),
                "doi": item.get("doi"),
                "cited_by_count": item.get("cited_by_count"),
                "authors": authors,
                "referenced_works": item.get("referenced_works") or [],
            }
        )
        if len(records) >= limit:
            break

    logger.debug("Collected OpenAlex records", extra={"count": len(records)})
    return records


def _extract_openalex_authors(authorships: Any) -> List[str]:
    authors: List[str] = []
    if isinstance(authorships, Iterable):
        for entry in authorships:
            if isinstance(entry, dict):
                author = entry.get("author")
                if isinstance(author, dict):
                    name = author.get("display_name")
                    if isinstance(name, str) and name:
                        authors.append(name)
    return authors


def _build_citation_edges(records: Iterable[Dict[str, Any]], *, limit: int) -> List[Dict[str, str]]:
    edges: List[Dict[str, str]] = []
    for record in records:
        source = record.get("id")
        if not isinstance(source, str) or not source:
            continue
        refs = record.get("referenced_works") or []
        if not isinstance(refs, list):
            continue
        for target in refs:
            if not isinstance(target, str):
                continue
            edges.append({"source": source, "target": target})
            if len(edges) >= limit:
                return edges
    return edges
