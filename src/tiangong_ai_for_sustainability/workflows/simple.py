"""Simple end-to-end workflow for producing a sustainability snapshot report."""

from __future__ import annotations

from dataclasses import dataclass
from logging import LoggerAdapter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..adapters import AdapterError
from ..adapters.api.base import APIError
from ..services import ResearchServices
from ..core.logging import get_logger
from .charting import ensure_chart_image


@dataclass(slots=True)
class WorkflowArtifacts:
    """Container capturing workflow outputs."""

    report_path: Path
    chart_path: Optional[Path]
    sdg_matches: List[Dict[str, Any]]
    repositories: List[Dict[str, Any]]
    papers: List[Dict[str, Any]]
    carbon_snapshot: Dict[str, Any]


def run_simple_workflow(
    services: ResearchServices,
    *,
    topic: str,
    report_path: Path,
    chart_path: Path,
    github_limit: int = 5,
    paper_limit: int = 5,
    carbon_location: str = "CAISO_NORTH",
) -> WorkflowArtifacts:
    """Execute a lightweight research workflow end-to-end.

    The workflow:
      1. Identifies SDG goals whose titles/descriptions match the topic keywords.
      2. Fetches sustainability repositories via GitHub Topics.
      3. Fetches representative papers via Semantic Scholar.
      4. Queries grid carbon intensity (when the CLI is available).
      5. Renders a bar chart using the AntV MCP chart server.
      6. Writes a Markdown report summarising findings.

    Parameters
    ----------
    services:
        Shared :class:`ResearchServices` instance.
    topic:
        Research topic or query phrase.
    report_path:
        Destination path for the Markdown report. Its parent directories will be created automatically.
    chart_path:
        Destination path for the generated PNG chart.
    github_limit / paper_limit:
        Maximum number of repositories/papers to include.
    carbon_location:
        Grid intensity location identifier forwarded to the `grid-intensity` CLI.
    """

    report_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.parent.mkdir(parents=True, exist_ok=True)

    if hasattr(services, "context") and hasattr(services.context, "get_logger"):
        workflow_logger = services.context.get_logger("workflow.simple")
    else:  # pragma: no cover - defensive when services.context missing
        workflow_logger = get_logger("workflow.simple")

    workflow_logger.info("Starting simple workflow", extra={"topic": topic})

    sdg_matches = _match_sdgs(services, topic, workflow_logger)
    workflow_logger.debug("Matched SDG goals", extra={"count": len(sdg_matches)})

    repositories = _fetch_repositories(services, topic, github_limit, workflow_logger)
    workflow_logger.debug("Fetched repositories", extra={"count": len(repositories)})

    papers = _fetch_papers(services, topic, paper_limit, workflow_logger)
    workflow_logger.debug("Fetched representative papers", extra={"count": len(papers)})

    carbon_snapshot = _fetch_carbon_intensity(services, carbon_location, workflow_logger)

    chart_generated = False
    if repositories:
        chart_generated = _render_repository_chart(services, repositories, topic, chart_path, workflow_logger)

    if not chart_generated:
        chart_path = None
        workflow_logger.warning("Repository chart not generated", extra={"reason": "insufficient data"})
    else:
        workflow_logger.info("Repository chart generated", extra={"chart_path": chart_path.as_posix()})

    _write_report(
        topic=topic,
        report_path=report_path,
        sdg_matches=sdg_matches,
        repositories=repositories,
        papers=papers,
        carbon_snapshot=carbon_snapshot,
        chart_path=chart_path,
        logger=workflow_logger,
    )

    workflow_logger.info(
        "Simple workflow completed",
        extra={
            "topic": topic,
            "report_path": report_path.as_posix(),
            "chart_generated": chart_generated,
        },
    )

    return WorkflowArtifacts(
        report_path=report_path,
        chart_path=chart_path,
        sdg_matches=sdg_matches,
        repositories=repositories,
        papers=papers,
        carbon_snapshot=carbon_snapshot,
    )


# ---------------------------------------------------------------------------
# SDG matching


def _match_sdgs(services: ResearchServices, topic: str, logger: Optional[LoggerAdapter] = None) -> List[Dict[str, Any]]:
    keywords = _tokenise(topic)

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
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:3]


def _tokenise(text: str) -> List[str]:
    raw = text.lower().replace("/", " ").replace("-", " ")
    return [token for token in raw.split() if len(token) > 2]


# ---------------------------------------------------------------------------
# GitHub repositories


def _fetch_repositories(
    services: ResearchServices,
    topic: str,
    limit: int,
    logger: Optional[LoggerAdapter] = None,
) -> List[Dict[str, Any]]:
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


# ---------------------------------------------------------------------------
# Semantic Scholar papers


def _fetch_papers(
    services: ResearchServices,
    topic: str,
    limit: int,
    logger: Optional[LoggerAdapter] = None,
) -> List[Dict[str, Any]]:
    try:
        payload = services.semantic_scholar_client().search_papers(
            topic,
            limit=limit,
            fields=["title", "year", "url", "abstract", "authors"],
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
        authors = item.get("authors") or []
        if isinstance(authors, list):
            names = [author.get("name") for author in authors if isinstance(author, dict) and author.get("name")]
        else:
            names = []
        papers.append(
            {
                "title": item.get("title", "unknown"),
                "year": item.get("year"),
                "url": item.get("url"),
                "abstract": item.get("abstract"),
                "authors": names,
            }
        )
    return papers


# ---------------------------------------------------------------------------
# Carbon intensity


def _fetch_carbon_intensity(
    services: ResearchServices,
    location: str,
    logger: Optional[LoggerAdapter] = None,
) -> Dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Chart rendering


def _render_repository_chart(
    services: ResearchServices,
    repositories: Iterable[Dict[str, Any]],
    topic: str,
    chart_path: Path,
    logger: Optional[LoggerAdapter] = None,
) -> bool:
    chart_data = []
    for repo in repositories:
        name = repo.get("full_name")
        stars = repo.get("stargazers_count", 0)
        if not name:
            continue
        chart_data.append({"category": name, "value": int(stars)})

    if not chart_data:
        if logger:
            logger.warning("Skipping chart rendering due to empty repository list", extra={"topic": topic})
        return False

    endpoint = services.chart_mcp_endpoint()
    arguments = {
        "data": chart_data,
        "title": f"Top repositories for {topic}",
        "width": 800,
        "height": 500,
        "format": "png",
    }
    if logger:
        logger.info(
            "Rendering repository chart",
            extra={"endpoint": endpoint, "chart_path": chart_path.as_posix(), "repository_count": len(chart_data)},
        )
    return ensure_chart_image(endpoint, tool_name="generate_bar_chart", arguments=arguments, destination=chart_path)


# ---------------------------------------------------------------------------
# Report generation


def _write_report(
    *,
    topic: str,
    report_path: Path,
    sdg_matches: List[Dict[str, Any]],
    repositories: List[Dict[str, Any]],
    papers: List[Dict[str, Any]],
    carbon_snapshot: Dict[str, Any],
    chart_path: Optional[Path],
    logger: Optional[LoggerAdapter] = None,
) -> None:
    if logger:
        logger.info("Writing workflow report", extra={"report_path": report_path.as_posix()})

    lines: List[str] = []
    lines.append(f"# Sustainability Snapshot: {topic}\n")

    lines.append("## SDG Alignment\n")
    if sdg_matches:
        for match in sdg_matches:
            code = match.get("code", "?")
            title = match.get("title", "Unknown goal")
            score = match.get("score", 0)
            lines.append(f"- **SDG {code}** — {title} (score: {score})")
        lines.append("")
    else:
        lines.append("- No SDG matches identified.\n")

    lines.append("## Key Repositories\n")
    if repositories:
        lines.append("| Repository | Stars | Description |")
        lines.append("|------------|-------|-------------|")
        for repo in repositories:
            name = repo.get("full_name", "unknown")
            stars = repo.get("stargazers_count", 0)
            desc = (repo.get("description") or "").replace("\n", " ")
            url = repo.get("html_url")
            label = f"[{name}]({url})" if url else name
            lines.append(f"| {label} | {stars} | {desc or '—'} |")
        lines.append("")
    else:
        lines.append("No repositories found.\n")

    lines.append("## Representative Papers\n")
    if papers:
        for paper in papers:
            title = paper.get("title", "unknown")
            year = paper.get("year") or "?"
            url = paper.get("url")
            authors = ", ".join(paper.get("authors", [])) or "N/A"
            abstract = (paper.get("abstract") or "").strip()
            entry = f"- **{title}** ({year}) — {authors}"
            if url:
                entry += f" — [{url}]({url})"
            lines.append(entry)
            if abstract:
                lines.append(f"  - _Abstract_: {abstract[:500]}{'…' if len(abstract) > 500 else ''}")
        lines.append("")
    else:
        lines.append("No papers retrieved.\n")

    lines.append("## Carbon Intensity\n")
    if carbon_snapshot.get("note") == "Grid intensity unavailable":
        lines.append(f"- {carbon_snapshot.get('note')}: {carbon_snapshot.get('error')}\n")
    else:
        lines.append(f"- Provider: {carbon_snapshot.get('provider', 'unknown')}\n")
        lines.append(f"- Location: {carbon_snapshot.get('location', 'unknown')}\n")
        if "carbon_intensity" in carbon_snapshot:
            units = carbon_snapshot.get("units") or carbon_snapshot.get("unit") or "gCO2e/kWh"
            lines.append(f"- Carbon intensity: {carbon_snapshot['carbon_intensity']} {units}\n")
        if "datetime" in carbon_snapshot:
            lines.append(f"- Timestamp: {carbon_snapshot['datetime']}\n")

    lines.append("## Visualization\n")
    if chart_path and chart_path.exists():
        rel_path = chart_path.as_posix()
        lines.append(f"![Top repositories chart]({rel_path})\n")
    else:
        lines.append("Chart generation unavailable.\n")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    if logger:
        logger.debug("Report written", extra={"report_path": report_path.as_posix(), "line_count": len(lines)})
