"""Simple end-to-end workflow for producing a sustainability snapshot report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import httpx
import shutil
import subprocess
import time

from ..adapters import AdapterError
from ..adapters.api.base import APIError
from ..services import ResearchServices


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

    sdg_matches = _match_sdgs(services, topic)
    repositories = _fetch_repositories(services, topic, github_limit)
    papers = _fetch_papers(services, topic, paper_limit)
    carbon_snapshot = _fetch_carbon_intensity(services, carbon_location)

    chart_generated = False
    if repositories:
        chart_generated = _render_repository_chart(services, repositories, topic, chart_path)

    if not chart_generated:
        chart_path = None

    _write_report(
        topic=topic,
        report_path=report_path,
        sdg_matches=sdg_matches,
        repositories=repositories,
        papers=papers,
        carbon_snapshot=carbon_snapshot,
        chart_path=chart_path,
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


def _match_sdgs(services: ResearchServices, topic: str) -> List[Dict[str, Any]]:
    keywords = _tokenise(topic)
    try:
        goals = services.un_sdg_client().list_goals()
    except APIError as exc:
        return [
            {
                "code": None,
                "title": "Unable to load SDG catalogue",
                "description": str(exc),
                "score": 0,
            }
        ]

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


def _fetch_repositories(services: ResearchServices, topic: str, limit: int) -> List[Dict[str, Any]]:
    try:
        payload = services.github_topics_client().search_repositories(topic, per_page=limit)
    except APIError as exc:
        return [
            {
                "full_name": "(error)",
                "stargazers_count": 0,
                "html_url": None,
                "description": str(exc),
            }
        ]

    items = payload.get("items") or []
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


def _fetch_papers(services: ResearchServices, topic: str, limit: int) -> List[Dict[str, Any]]:
    try:
        payload = services.semantic_scholar_client().search_papers(
            topic,
            limit=limit,
            fields=["title", "year", "url", "abstract", "authors"],
        )
    except APIError as exc:
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


def _fetch_carbon_intensity(services: ResearchServices, location: str) -> Dict[str, Any]:
    try:
        snapshot = services.get_carbon_intensity(location)
        return snapshot
    except AdapterError as exc:
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
) -> bool:
    chart_data = []
    for repo in repositories:
        name = repo.get("full_name")
        stars = repo.get("stargazers_count", 0)
        if not name:
            continue
        chart_data.append({"category": name, "value": int(stars)})

    if not chart_data:
        return False

    endpoint = services.chart_mcp_endpoint()
    launcher_proc: Optional[subprocess.Popen[str]] = None
    try:
        image_url = _call_chart_tool(endpoint, chart_data, topic)
    except (httpx.HTTPError, ValueError) as exc:
        if "Connection refused" in str(exc) or isinstance(exc, httpx.ConnectError):
            launcher_proc = _launch_chart_server()
            if launcher_proc is not None:
                time.sleep(5)
                try:
                    image_url = _call_chart_tool(endpoint, chart_data, topic)
                except Exception:
                    chart_path.write_text(f"Chart generation failed: {exc}\n", encoding="utf-8")
                    return False
            else:
                chart_path.write_text(f"Chart generation failed: {exc}\n", encoding="utf-8")
                return False
        else:
            chart_path.write_text(f"Chart generation failed: {exc}\n", encoding="utf-8")
            return False

    if image_url is None:
        chart_path.write_text("Chart generation returned no image URL.\n", encoding="utf-8")
        return False

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(image_url)
            response.raise_for_status()
            chart_path.write_bytes(response.content)
    except httpx.HTTPError as exc:
        chart_path.write_text(f"Failed to download chart image: {exc}\n", encoding="utf-8")
        return False
    finally:
        if launcher_proc is not None:
            launcher_proc.terminate()
            try:
                launcher_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                launcher_proc.kill()

    return True


def _call_chart_tool(endpoint: str, chart_data: List[Dict[str, Any]], topic: str) -> Optional[str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    with httpx.Client(timeout=30.0) as client:
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "clientInfo": {"name": "tiangong-workflow", "version": "0.1.0"},
                "capabilities": {},
            },
        }
        client.post(endpoint, headers=headers, json=init_payload)

        call_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "generate_bar_chart",
                "arguments": {
                    "data": chart_data,
                    "title": f"Top repositories for {topic}",
                    "width": 800,
                    "height": 500,
                    "format": "png",
                },
            },
        }
        response = client.post(endpoint, headers=headers, json=call_payload)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("result", {})
        content = result.get("content", [])
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "image" and "data" in item:
                data = item["data"]
                if isinstance(data, str) and data.startswith("http"):
                    return data
            if item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text.startswith("http"):
                    return text
        return None


def _launch_chart_server() -> Optional[subprocess.Popen[str]]:
    if shutil.which("npx") is None:
        return None
    try:
        proc = subprocess.Popen(
            ["npx", "-y", "@antv/mcp-server-chart", "--transport", "streamable"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return proc
    except OSError:
        return None


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
) -> None:
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
