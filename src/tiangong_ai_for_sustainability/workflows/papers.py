"""Deterministic literature aggregation workflow."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from logging import LoggerAdapter
from pathlib import Path
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
    arxiv: List[Dict[str, Any]]
    scopus: List[Dict[str, Any]]
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
    include_arxiv: bool = False,
    include_scopus: bool = False,
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
        "Match SDG goals using UNSDG catalogue.",
        "Query Semantic Scholar for representative papers.",
    ]
    if include_arxiv:
        plan_steps.append("Load local arXiv dump (TIANGONG_ARXIV_INDEX or cache/arxiv/index.jsonl).")
    if include_openalex:
        plan_steps.append("Query OpenAlex works API for complementary records.")
    else:
        plan_steps.append("Skip OpenAlex enrichment (disabled).")
    if include_scopus:
        plan_steps.append("Load Scopus export (TIANGONG_SCOPUS_INDEX or cache/scopus/index.jsonl).")
    if include_citations:
        plan_steps.append("Build citation edge list from OpenAlex references.")

    if is_dry_run:
        logger.info("Dry-run plan generated", extra={"steps": plan_steps})
        return PaperSearchArtifacts(
            query=query,
            sdg_matches=[],
            semantic_scholar=[],
            arxiv=[],
            scopus=[],
            openalex=[],
            notes=[],
            citation_edges=None,
            plan=plan_steps,
        )

    notes: List[str] = []
    sdg_matches: List[Dict[str, Any]] = []
    semantic_results: List[Dict[str, Any]] = []
    arxiv_results: List[Dict[str, Any]] = []
    scopus_results: List[Dict[str, Any]] = []

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

    if include_arxiv:
        arxiv_index = _resolve_local_index(context, "TIANGONG_ARXIV_INDEX", ("arxiv", "index.jsonl"))
        if not arxiv_index:
            notes.append("ArXiv enrichment skipped: local index not found. Set TIANGONG_ARXIV_INDEX or cache under .cache/tiangong/arxiv/index.jsonl.")
        else:
            try:
                arxiv_results = _load_local_jsonl(arxiv_index, limit, source="arxiv")
            except ValueError as exc:
                notes.append(f"Failed to read arXiv index: {exc}")

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

    if include_scopus:
        scopus_index = _resolve_local_index(context, "TIANGONG_SCOPUS_INDEX", ("scopus", "index.jsonl"))
        if not scopus_index:
            notes.append("Scopus enrichment skipped: local export not configured. Set TIANGONG_SCOPUS_INDEX or place index.jsonl under cache/scopus/.")
        elif context and not context.is_enabled("scopus"):
            notes.append("Scopus enrichment skipped: data source disabled in execution context.")
        else:
            try:
                scopus_results = _load_local_jsonl(scopus_index, limit, source="scopus")
            except ValueError as exc:
                notes.append(f"Failed to read Scopus export: {exc}")

    return PaperSearchArtifacts(
        query=query,
        sdg_matches=sdg_matches,
        semantic_scholar=semantic_results,
        arxiv=arxiv_results,
        scopus=scopus_results,
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


def _resolve_local_index(
    context: Optional[Any],
    env_var: str,
    default_parts: tuple[str, str],
) -> Optional[Path]:
    env_path = os.getenv(env_var)
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.is_file():
            return candidate
    cache_base: Optional[Path] = getattr(context, "cache_dir", None)
    if cache_base:
        candidate = cache_base / default_parts[0] / default_parts[1]
        if candidate.is_file():
            return candidate
    return None


def _load_local_jsonl(path: Path, limit: int, *, source: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if len(records) >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{source} index contains invalid JSON: {exc}") from exc
                records.append(_normalise_local_record(payload, source))
    except FileNotFoundError as exc:
        raise ValueError(f"{source} index not found at {path}") from exc
    return records


def _normalise_local_record(payload: Dict[str, Any], source: str) -> Dict[str, Any]:
    if source == "arxiv":
        return {
            "id": payload.get("id") or payload.get("arxiv_id"),
            "title": payload.get("title"),
            "year": payload.get("year") or payload.get("published") or payload.get("update_year"),
            "authors": payload.get("authors") or payload.get("author_names") or [],
            "url": payload.get("url") or payload.get("landing_url"),
            "summary": payload.get("summary") or payload.get("abstract"),
        }
    if source == "scopus":
        return {
            "id": payload.get("eid") or payload.get("id"),
            "title": payload.get("title"),
            "year": payload.get("coverDate", "")[:4] or payload.get("year"),
            "authors": payload.get("author_names") or payload.get("authors") or [],
            "doi": payload.get("doi"),
            "cited_by_count": payload.get("citedby_count"),
            "link": payload.get("link"),
        }
    return payload
