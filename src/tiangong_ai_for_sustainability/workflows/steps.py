"""
Common deterministic research steps shared across workflows.

The helpers here encapsulate SDG matching, repository discovery, literature
queries, and carbon intensity lookups so multiple workflows (simple snapshots,
synthesis, deep LCA, etc.) can reuse the same logic while staying spec-first.
"""

from __future__ import annotations

from logging import LoggerAdapter
from typing import Any, Dict, List, Optional, Sequence

from ..adapters import AdapterError
from ..adapters.api.base import APIError
from ..services import ResearchServices


def tokenise_keywords(text: str) -> List[str]:
    """Return lowercase keyword tokens for simple matching heuristics."""

    raw = text.lower().replace("/", " ").replace("-", " ")
    return [token for token in raw.split() if len(token) > 2]


def match_sdg_goals(
    services: ResearchServices,
    topic: str,
    logger: Optional[LoggerAdapter] = None,
) -> List[Dict[str, Any]]:
    """
    Score SDG goals against the provided topic using keyword overlap.

    Falls back to a descriptive error payload when the UNSDG catalogue is
    unavailable.
    """

    keywords = tokenise_keywords(topic)

    try:
        goals = services.un_sdg_client().list_goals()
    except APIError as exc:
        if logger:
            logger.error("Unable to load SDG catalogue", extra={"error": str(exc)})
        return [
            {
                "code": None,
                "title": "Unable to load SDG catalogue",
                "description": str(exc),
                "score": 0,
            }
        ]

    if logger:
        logger.debug("Scoring SDG goals", extra={"keyword_count": len(keywords), "goal_count": len(goals)})

    ranked: List[Dict[str, Any]] = []
    for goal in goals:
        title = str(goal.get("title", ""))
        description = str(goal.get("description", ""))
        text = f"{title} {description}".lower()
        score = sum(text.count(keyword) for keyword in keywords)
        if score > 0:
            ranked.append(
                {
                    "code": goal.get("code"),
                    "title": title,
                    "description": description,
                    "score": score,
                }
            )

    ranked.sort(key=lambda item: item.get("score", 0), reverse=True)
    return ranked[:10]


def discover_repositories(
    services: ResearchServices,
    topic: str,
    limit: int,
    logger: Optional[LoggerAdapter] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve repositories from GitHub Topics for the supplied topic keyword.
    """

    try:
        payload = services.github_topics_client().search_repositories(topic, per_page=limit)
    except APIError as exc:
        if logger:
            logger.error("Repository discovery failed", extra={"error": str(exc), "topic": topic})
        return [
            {
                "full_name": "(error)",
                "stargazers_count": 0,
                "html_url": None,
                "description": str(exc),
            }
        ]

    items = payload.get("items") or []
    if logger:
        logger.debug("Processing repository payload", extra={"item_count": len(items)})
    repositories: List[Dict[str, Any]] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        repositories.append(
            {
                "full_name": item.get("full_name", "unknown"),
                "stargazers_count": item.get("stargazers_count", 0),
                "html_url": item.get("html_url"),
                "description": item.get("description"),
            }
        )
    return repositories


def discover_papers(
    services: ResearchServices,
    topic: str,
    limit: int,
    *,
    fields: Optional[Sequence[str]] = None,
    logger: Optional[LoggerAdapter] = None,
) -> List[Dict[str, Any]]:
    """
    Query Semantic Scholar for representative papers related to the topic.
    """

    desired_fields = list(fields) if fields else ["title", "year", "url", "abstract", "authors"]
    try:
        payload = services.semantic_scholar_client().search_papers(
            topic,
            limit=limit,
            fields=desired_fields,
        )
    except APIError as exc:
        if logger:
            logger.error("Semantic Scholar query failed", extra={"error": str(exc), "topic": topic})
        return [
            {
                "title": "Unable to query Semantic Scholar",
                "year": None,
                "url": None,
                "abstract": str(exc),
                "authors": [],
            }
        ]

    data = payload.get("data") or []
    if logger:
        logger.debug("Processing Semantic Scholar payload", extra={"item_count": len(data)})
    papers: List[Dict[str, Any]] = []
    for item in data[:limit]:
        if not isinstance(item, dict):
            continue
        authors_raw = item.get("authors") or []
        if isinstance(authors_raw, list):
            names = [author.get("name") for author in authors_raw if isinstance(author, dict) and author.get("name")]
        else:
            names = []
        papers.append(
            {
                "paper_id": item.get("paperId"),
                "title": item.get("title", "unknown"),
                "year": item.get("year"),
                "url": item.get("url"),
                "abstract": item.get("abstract"),
                "authors": names,
            }
        )
    return papers


def retrieve_carbon_intensity(
    services: ResearchServices,
    location: str,
    logger: Optional[LoggerAdapter] = None,
) -> Dict[str, Any]:
    """
    Query the grid-intensity CLI for the specified location.
    """

    try:
        snapshot = services.get_carbon_intensity(location)
        if logger:
            logger.info("Retrieved carbon intensity snapshot", extra={"location": location})
        return snapshot
    except AdapterError as exc:
        if logger:
            logger.error("Carbon intensity lookup failed", extra={"error": str(exc), "location": location})
        return {
            "note": "Grid intensity unavailable",
            "error": str(exc),
            "location": location,
        }
