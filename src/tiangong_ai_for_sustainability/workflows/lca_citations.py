"""
Workflow that performs deep literature analysis on life cycle assessment (LCA)
papers intersecting planetary boundaries and the Sustainable Development Goals.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from logging import LoggerAdapter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..adapters.api.base import APIError
from ..core.logging import get_logger
from ..services import ResearchServices
from .charting import ensure_chart_image

LCA_CONCEPT_ID = "C2778706760"
DEFAULT_KEYWORDS = [
    "life cycle assessment",
    "lca",
    "sustainability",
    "planetary boundaries",
    "sustainable development goals",
    "sdg",
]

logger = get_logger(__name__)


@dataclass(slots=True)
class PaperRecord:
    """Normalized representation of a scholarly article."""

    source_id: str
    work_id: str
    title: str
    year: int
    citation_count: int
    doi: Optional[str]
    url: Optional[str]
    journal: Optional[str]
    authors: List[str]
    abstract: str
    concepts: List[Dict[str, Any]]
    keyword_hits: Dict[str, int]
    extra: Dict[str, Any]


@dataclass(slots=True)
class CitationQuestion:
    """High-impact research questions derived from highly cited papers."""

    question: str
    citation_count: int
    publication_year: int
    paper_title: str
    journal: Optional[str]
    doi: Optional[str]
    url: Optional[str]
    authors: List[str]
    keyword_hits: Dict[str, int]


@dataclass(slots=True)
class TrendingTopic:
    """Topics attracting increasing citation momentum."""

    topic: str
    trend_score: float
    citation_growth: float
    recent_share: float
    coverage_years: Tuple[int, int]
    top_papers: List[str]


@dataclass(slots=True)
class ResearchGap:
    """Topics with limited publications but strong citation potential."""

    topic: str
    paper_count: int
    avg_citations: float
    recent_papers: int
    representative_title: str
    supporting_doi: Optional[str]
    rationale: str


@dataclass(slots=True)
class LCACitationWorkflowArtifacts:
    """Workflow outputs returned to the caller."""

    report_path: Path
    chart_path: Optional[Path]
    chart_caption: Optional[str]
    raw_data_path: Optional[Path]
    questions: List[CitationQuestion]
    trending_topics: List[TrendingTopic]
    research_gaps: List[ResearchGap]
    papers: List[PaperRecord]


def run_lca_citation_workflow(
    services: ResearchServices,
    *,
    report_path: Path,
    chart_path: Path,
    raw_data_path: Optional[Path] = None,
    years: int = 5,
    keyword_overrides: Optional[Iterable[str]] = None,
    max_records: int = 300,
) -> LCACitationWorkflowArtifacts:
    """
    Execute an end-to-end analysis of LCA literature focused on planetary boundaries and SDGs.
    """

    context = getattr(services, "context", None)
    options = getattr(context, "options", None)
    is_dry_run = bool(getattr(options, "dry_run", False))

    if hasattr(services, "context") and hasattr(services.context, "get_logger"):
        workflow_logger = services.context.get_logger("workflow.lca_citations")
    else:  # pragma: no cover - defensive fallback
        workflow_logger = get_logger("workflow.lca_citations")

    workflow_logger.info(
        "Starting LCA citation workflow",
        extra={
            "report_path": report_path.as_posix(),
            "chart_path": chart_path.as_posix(),
            "years": years,
            "max_records": max_records,
            "keywords_override": list(keyword_overrides) if keyword_overrides else None,
            "dry_run": is_dry_run,
        },
    )

    if is_dry_run:
        planned_keywords = list(keyword_overrides) if keyword_overrides else None
        plan_steps = [
            f"Query OpenAlex for LCA works between the last {years} years using default keywords.",
            "Aggregate citation metrics and derive top questions, trending topics, and gaps.",
            "Persist raw dataset and Markdown report summarising findings.",
            "Render trend chart via AntV MCP chart server.",
        ]
        workflow_logger.info(
            "Dry-run plan generated",
            extra={
                "steps": plan_steps,
                "keywords": planned_keywords,
            },
        )
        return LCACitationWorkflowArtifacts(
            report_path=report_path,
            chart_path=None,
            chart_caption=None,
            raw_data_path=None,
            questions=[],
            trending_topics=[],
            research_gaps=[],
            papers=[],
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_data_path:
        raw_data_path.parent.mkdir(parents=True, exist_ok=True)

    keywords = _prepare_keywords(keyword_overrides)
    start_year, end_year = _derive_year_window(years)
    workflow_logger.info("Collecting OpenAlex papers")
    try:
        papers = _collect_openalex_papers(
            services,
            keywords=keywords,
            start_year=start_year,
            end_year=end_year,
            max_records=max_records,
            logger=workflow_logger,
        )
    except APIError as exc:
        _write_failure_report(report_path, start_year, end_year, str(exc))
        workflow_logger.error("OpenAlex collection failed", extra={"error": str(exc)})
        return LCACitationWorkflowArtifacts(
            report_path=report_path,
            chart_path=None,
            raw_data_path=None,
            questions=[],
            trending_topics=[],
            research_gaps=[],
            papers=[],
        )

    if not papers:
        _write_empty_report(report_path, start_year, end_year)
        workflow_logger.warning("No papers returned from OpenAlex", extra={"start_year": start_year, "end_year": end_year})
        return LCACitationWorkflowArtifacts(
            report_path=report_path,
            chart_path=None,
            raw_data_path=None,
            questions=[],
            trending_topics=[],
            research_gaps=[],
            papers=[],
        )

    workflow_logger.debug("Collected OpenAlex papers", extra={"paper_count": len(papers)})

    _enrich_with_semantic_scholar(services, papers)

    questions = _derive_top_questions(papers, limit=8)
    trending_topics, concept_series = _summarise_trending_topics(papers, start_year, end_year)
    research_gaps = _identify_research_gaps(papers, concept_series, start_year, end_year, keywords)

    if raw_data_path:
        workflow_logger.info("Serialising raw dataset", extra={"raw_data_path": raw_data_path.as_posix()})
        _serialise_raw_dataset(raw_data_path, papers, questions, trending_topics, research_gaps)

    chart_caption: Optional[str] = None
    chart_generated = False
    if trending_topics:
        chart_caption = "Emerging LCA topics by citation momentum"
        chart_generated = _render_trend_chart(services, trending_topics, chart_path)
    elif questions:
        chart_caption = "Top LCA questions by citation count"
        chart_generated = _render_question_chart(services, questions, chart_path)

    if not chart_generated:
        workflow_logger.warning(
            "Chart generation skipped or failed",
            extra={"trending_topic_count": len(trending_topics), "question_count": len(questions)},
        )
        chart_path = None

    _write_report(
        report_path=report_path,
        questions=questions,
        trending_topics=trending_topics,
        research_gaps=research_gaps,
        papers=papers,
        keywords=keywords,
        start_year=start_year,
        end_year=end_year,
        chart_path=chart_path,
        chart_caption=chart_caption,
        raw_data_path=raw_data_path,
    )
    workflow_logger.info(
        "LCA citation workflow completed",
        extra={
            "report_path": report_path.as_posix(),
            "chart_path": chart_path.as_posix() if chart_path else None,
            "question_count": len(questions),
            "trending_topic_count": len(trending_topics),
            "research_gap_count": len(research_gaps),
        },
    )

    return LCACitationWorkflowArtifacts(
        report_path=report_path,
        chart_path=chart_path,
        chart_caption=chart_caption,
        raw_data_path=raw_data_path,
        questions=questions,
        trending_topics=trending_topics,
        research_gaps=research_gaps,
        papers=papers,
    )


# ---------------------------------------------------------------------------
# Data collection


def _prepare_keywords(keyword_overrides: Optional[Iterable[str]]) -> List[str]:
    base = [kw.strip().lower() for kw in DEFAULT_KEYWORDS]
    if keyword_overrides:
        for kw in keyword_overrides:
            normalised = kw.strip().lower()
            if normalised and normalised not in base:
                base.append(normalised)
    return base


def _derive_year_window(years: int) -> Tuple[int, int]:
    today = date.today()
    end_year = today.year
    start_year = max(1900, end_year - max(1, years) + 1)
    return start_year, end_year


def _collect_openalex_papers(
    services: ResearchServices,
    *,
    keywords: List[str],
    start_year: int,
    end_year: int,
    max_records: int,
    logger: Optional[LoggerAdapter] = None,
) -> List[PaperRecord]:
    client = services.openalex_client()

    filters = {
        "concepts.id": f"https://openalex.org/{LCA_CONCEPT_ID}",
        "from_publication_date": f"{start_year}-01-01",
        "to_publication_date": f"{end_year}-12-31",
        "type": "article",
    }

    select_fields = [
        "id",
        "display_name",
        "title",
        "publication_year",
        "publication_date",
        "cited_by_count",
        "doi",
        "ids",
        "authorships",
        "concepts",
        "abstract_inverted_index",
        "primary_location",
        "sources",
    ]

    records: List[PaperRecord] = []
    seen_ids: set[str] = set()

    for item in client.iterate_works(
        search="life cycle assessment sustainability",
        filters=filters,
        sort="cited_by_count:desc",
        select=select_fields,
        per_page=200,
        max_pages=10,
    ):
        paper = _paper_from_openalex(item, keywords)
        if paper is None or paper.work_id in seen_ids:
            continue
        seen_ids.add(paper.work_id)
        records.append(paper)
        if logger and len(records) % 20 == 0:
            logger.debug("Collected OpenAlex papers batch", extra={"record_count": len(records)})
        if len(records) >= max_records:
            break

    if logger:
        logger.debug(
            "Completed OpenAlex collection",
            extra={"record_count": len(records), "max_records": max_records},
        )
    return records


def _paper_from_openalex(payload: Mapping[str, Any], keywords: List[str]) -> Optional[PaperRecord]:
    work_id = str(payload.get("id") or "").strip()
    title = str(payload.get("display_name") or payload.get("title") or "").strip()
    year = payload.get("publication_year")
    citation_count = payload.get("cited_by_count", 0)

    if not work_id or not title or not isinstance(year, int):
        return None

    abstract = _decode_abstract(payload.get("abstract_inverted_index"))
    keyword_hits = _count_keyword_hits(title, abstract, keywords)
    if keyword_hits.get("life cycle assessment", 0) == 0:
        return None

    total_hits = sum(keyword_hits.values())
    if total_hits < 2:
        return None

    doi = None
    ids_field = payload.get("ids")
    if isinstance(ids_field, Mapping):
        doi = ids_field.get("doi")
    if not doi:
        doi_val = payload.get("doi")
        if isinstance(doi_val, str):
            doi = doi_val

    primary_location = payload.get("primary_location") or {}
    url = None
    journal = None
    if isinstance(primary_location, Mapping):
        url_candidate = primary_location.get("landing_page_url") or primary_location.get("pdf_url")
        if isinstance(url_candidate, str):
            url = url_candidate
        source = primary_location.get("source")
        if isinstance(source, Mapping):
            display_name = source.get("display_name")
            if isinstance(display_name, str):
                journal = display_name

    if not journal:
        sources_field = payload.get("sources")
        if isinstance(sources_field, list) and sources_field:
            first_source = sources_field[0]
            if isinstance(first_source, Mapping):
                display_name = first_source.get("display_name")
                if isinstance(display_name, str):
                    journal = display_name

    authors = []
    authorships = payload.get("authorships") or []
    if isinstance(authorships, list):
        for entry in authorships:
            if isinstance(entry, Mapping):
                author = entry.get("author")
                if isinstance(author, Mapping):
                    name = author.get("display_name")
                    if isinstance(name, str) and name:
                        authors.append(name)
                elif isinstance(entry.get("raw_author_name"), str):
                    authors.append(entry["raw_author_name"])

    concepts = []
    raw_concepts = payload.get("concepts") or []
    if isinstance(raw_concepts, list):
        for concept in raw_concepts:
            if isinstance(concept, Mapping):
                name = concept.get("display_name")
                if isinstance(name, str):
                    concepts.append(
                        {
                            "id": concept.get("id"),
                            "display_name": name,
                            "level": concept.get("level"),
                            "score": concept.get("score"),
                        }
                    )

    extra = {
        "publication_date": payload.get("publication_date"),
        "raw_payload": payload,
    }

    return PaperRecord(
        source_id="openalex",
        work_id=work_id,
        title=title,
        year=year,
        citation_count=int(citation_count or 0),
        doi=_normalise_doi(doi),
        url=url,
        journal=journal,
        authors=authors,
        abstract=abstract,
        concepts=concepts,
        keyword_hits=keyword_hits,
        extra=extra,
    )


def _decode_abstract(data: Any) -> str:
    if not isinstance(data, Mapping):
        return ""
    positions: Dict[int, str] = {}
    for word, indices in data.items():
        if not isinstance(word, str):
            continue
        if isinstance(indices, int):
            indices = [indices]
        if not isinstance(indices, Iterable):
            continue
        for pos in indices:
            if isinstance(pos, int):
                positions[pos] = word
    if not positions:
        return ""
    length = max(positions.keys()) + 1
    words = [positions.get(i, "") for i in range(length)]
    return " ".join(filter(None, words))


def _count_keyword_hits(title: str, abstract: str, keywords: Iterable[str]) -> Dict[str, int]:
    text = f"{title.lower()} {abstract.lower()}"
    counter: Dict[str, int] = {}
    for keyword in keywords:
        if not keyword:
            continue
        counter[keyword] = text.count(keyword.lower())
    return counter


def _normalise_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    cleaned = doi.strip()
    if cleaned.startswith("https://doi.org/"):
        cleaned = cleaned[len("https://doi.org/") :]
    if cleaned.startswith("doi:"):
        cleaned = cleaned[4:]
    return cleaned or None


def _enrich_with_semantic_scholar(services: ResearchServices, papers: List[PaperRecord]) -> None:
    if not papers:
        return

    client = services.semantic_scholar_client()
    fields = ["title", "year", "citationCount", "url", "tldr"]

    for paper in papers[: min(15, len(papers))]:
        paper_id = None
        if paper.doi:
            paper_id = f"DOI:{paper.doi}"
        elif paper.work_id.startswith("https://openalex.org/"):
            paper_id = paper.work_id.split("/")[-1]

        if not paper_id:
            continue

        try:
            payload = client.get_paper(paper_id, fields=fields)
        except APIError:
            continue

        if isinstance(payload, Mapping):
            citation_override = payload.get("citationCount")
            if isinstance(citation_override, int) and citation_override > paper.citation_count:
                paper.citation_count = citation_override
            url = payload.get("url")
            if isinstance(url, str):
                paper.url = url
            tldr = payload.get("tldr")
            if isinstance(tldr, Mapping):
                text = tldr.get("text")
                if isinstance(text, str) and len(text) > len(paper.abstract):
                    paper.abstract = text


# ---------------------------------------------------------------------------
# Analysis


def _derive_top_questions(papers: List[PaperRecord], *, limit: int) -> List[CitationQuestion]:
    ranked = sorted(papers, key=lambda item: item.citation_count, reverse=True)
    questions: List[CitationQuestion] = []

    for paper in ranked[:limit]:
        question = _title_to_question(paper.title)
        questions.append(
            CitationQuestion(
                question=question,
                citation_count=paper.citation_count,
                publication_year=paper.year,
                paper_title=paper.title,
                journal=paper.journal,
                doi=paper.doi,
                url=paper.url,
                authors=paper.authors,
                keyword_hits=paper.keyword_hits,
            )
        )
    return questions


def _title_to_question(title: str) -> str:
    clean = title.strip().rstrip(".")
    if clean.endswith("?"):
        return clean

    lower = clean.lower()
    if ":" in clean:
        lead, tail = [part.strip() for part in clean.split(":", 1)]
        if lead and tail:
            return f"How does {lead.lower()} relate to {tail.lower()} within life cycle assessment?"

    patterns = [
        ("integrat", "How can {phrase} be integrated into mainstream life cycle assessment practice?"),
        ("impact", "What is the impact of {phrase} on sustainability outcomes?"),
        ("framework", "Which frameworks enable {phrase} in LCA studies?"),
        ("method", "Which methodological advances address {phrase}?"),
        ("policy", "How does policy guidance influence {phrase}?"),
    ]

    for marker, template in patterns:
        if marker in lower:
            phrase = _phrase_from_title(clean, marker)
            return template.format(phrase=phrase)

    return f'What does "{clean}" reveal about advancing life cycle assessment?'


def _phrase_from_title(title: str, marker: str) -> str:
    lower = title.lower()
    idx = lower.find(marker)
    if idx == -1:
        return title.lower()
    start = max(0, idx - 40)
    end = min(len(title), idx + 60)
    snippet = title[start:end].strip()
    return snippet.lower()


def _summarise_trending_topics(
    papers: List[PaperRecord],
    start_year: int,
    end_year: int,
) -> Tuple[List[TrendingTopic], Dict[str, Dict[int, float]]]:
    concept_series: Dict[str, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
    concept_papers: Dict[str, List[PaperRecord]] = defaultdict(list)

    for paper in papers:
        for concept in paper.concepts:
            name = concept.get("display_name")
            score = concept.get("score") or 0.0
            if not isinstance(name, str) or score < 0.2:
                continue
            concept_series[name][paper.year] += paper.citation_count * float(score)
            concept_papers[name].append(paper)

    topics: List[TrendingTopic] = []
    for topic, yearly in concept_series.items():
        years = list(range(start_year, end_year + 1))
        values = [yearly.get(year, 0.0) for year in years]
        if sum(values) == 0:
            continue
        slope = _linear_slope(years, values)
        if slope <= 0:
            continue
        growth = values[-1] - values[0]
        recent = sum(values[-2:]) if len(values) >= 2 else values[-1]
        recent_share = recent / max(sum(values), 1.0)
        top_titles = [paper.title for paper in sorted(concept_papers[topic], key=lambda x: x.citation_count, reverse=True)[:3]]
        topics.append(
            TrendingTopic(
                topic=topic,
                trend_score=round(slope, 2),
                citation_growth=round(growth, 2),
                recent_share=round(recent_share, 3),
                coverage_years=(start_year, end_year),
                top_papers=top_titles,
            )
        )

    topics.sort(key=lambda item: (item.trend_score, item.citation_growth), reverse=True)
    return topics[:10], concept_series


def _linear_slope(xs: List[int], ys: List[float]) -> float:
    n = len(xs)
    if n == 0 or n != len(ys):
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _identify_research_gaps(
    papers: List[PaperRecord],
    concept_series: Dict[str, Dict[int, float]],
    start_year: int,
    end_year: int,
    keywords: List[str],
) -> List[ResearchGap]:
    concept_groups: Dict[str, List[PaperRecord]] = defaultdict(list)
    keyword_groups: Dict[str, List[PaperRecord]] = defaultdict(list)

    for paper in papers:
        for concept in paper.concepts:
            name = concept.get("display_name")
            score = concept.get("score") or 0.0
            if isinstance(name, str) and score >= 0.2:
                concept_groups[name].append(paper)
        for keyword, count in paper.keyword_hits.items():
            if keyword in keywords and count > 0:
                keyword_groups[keyword].append(paper)

    candidates: List[ResearchGap] = []

    for topic, group in concept_groups.items():
        if len(group) < 2:
            continue
        total_citations = sum(p.citation_count for p in group)
        avg_citations = total_citations / len(group)
        recent_papers = [p for p in group if p.year >= end_year - 1]
        if len(group) <= 5 and avg_citations >= 25:
            representative = max(group, key=lambda p: p.citation_count)
            series = concept_series.get(topic, {})
            rationale = (
                f"Only {len(group)} journal articles since {start_year}, "
                f"yet they accumulated {total_citations} citations "
                f"({avg_citations:.1f} per paper). "
                f"{len(recent_papers)} appeared in the last 24 months."
            )
            if series:
                total_recent = sum(v for year, v in series.items() if year >= end_year - 1)
                if total_recent > 0:
                    rationale += f" Recent citation energy: {total_recent:.1f} weighted references."
            candidates.append(
                ResearchGap(
                    topic=topic,
                    paper_count=len(group),
                    avg_citations=round(avg_citations, 2),
                    recent_papers=len(recent_papers),
                    representative_title=representative.title,
                    supporting_doi=representative.doi,
                    rationale=rationale,
                )
            )

    for keyword, group in keyword_groups.items():
        if len(group) <= 3:
            total_citations = sum(p.citation_count for p in group)
            if total_citations >= 40:
                representative = max(group, key=lambda p: p.citation_count)
                rationale = (
                    f"Keyword '{keyword}' appears in {len(group)} papers but collects "
                    f"{total_citations} citations (avg {total_citations/len(group):.1f}). "
                    "This suggests demand for deeper investigation with LCA framing."
                )
                candidates.append(
                    ResearchGap(
                        topic=f"Keyword focus: {keyword}",
                        paper_count=len(group),
                        avg_citations=round(total_citations / len(group), 2),
                        recent_papers=len([p for p in group if p.year >= end_year - 1]),
                        representative_title=representative.title,
                        supporting_doi=representative.doi,
                        rationale=rationale,
                    )
                )

    candidates.sort(key=lambda gap: (gap.avg_citations, gap.paper_count * -1), reverse=True)
    return candidates[:8]


# ---------------------------------------------------------------------------
# Output rendering


def _render_trend_chart(services: ResearchServices, topics: List[TrendingTopic], chart_path: Path) -> bool:
    endpoint = services.chart_mcp_endpoint()
    verification = services.verify_chart_mcp()
    if not verification.success:
        logger.warning("Chart MCP verification failed", extra={"details": verification.details})
        return False
    data = [{"category": topic.topic[:60], "value": round(topic.trend_score, 2)} for topic in topics[:8]]
    arguments = {
        "data": data,
        "title": "Emerging LCA topics by citation momentum",
        "width": 900,
        "height": 520,
        "format": "png",
    }
    return ensure_chart_image(endpoint, tool_name="generate_bar_chart", arguments=arguments, destination=chart_path)


def _render_question_chart(services: ResearchServices, questions: List[CitationQuestion], chart_path: Path) -> bool:
    endpoint = services.chart_mcp_endpoint()
    verification = services.verify_chart_mcp()
    if not verification.success:
        logger.warning("Chart MCP verification failed", extra={"details": verification.details})
        return False
    data = [{"category": item.question[:60], "value": int(item.citation_count)} for item in sorted(questions, key=lambda x: x.citation_count, reverse=True)[:8]]
    arguments = {
        "data": data,
        "title": "Top LCA questions by citation count",
        "width": 900,
        "height": 520,
        "format": "png",
    }
    return ensure_chart_image(endpoint, tool_name="generate_bar_chart", arguments=arguments, destination=chart_path)


def _serialise_raw_dataset(
    path: Path,
    papers: List[PaperRecord],
    questions: List[CitationQuestion],
    trending_topics: List[TrendingTopic],
    research_gaps: List[ResearchGap],
) -> None:
    payload = {
        "papers": [asdict(paper) for paper in papers],
        "questions": [asdict(question) for question in questions],
        "trending_topics": [asdict(topic) for topic in trending_topics],
        "research_gaps": [asdict(gap) for gap in research_gaps],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_report(
    *,
    report_path: Path,
    questions: List[CitationQuestion],
    trending_topics: List[TrendingTopic],
    research_gaps: List[ResearchGap],
    papers: List[PaperRecord],
    keywords: List[str],
    start_year: int,
    end_year: int,
    chart_path: Optional[Path],
    chart_caption: Optional[str],
    raw_data_path: Optional[Path],
) -> None:
    lines: List[str] = []
    lines.append(f"# LCA Citation Intelligence ({start_year}–{end_year})\n")

    lines.append("## Why it matters\n")
    lines.append("- Focus: peer-reviewed LCA journals intersecting planetary boundaries and SDGs, filtered via OpenAlex (concept-driven) with Semantic Scholar enrichment when available.")
    lines.append(f"- Query keywords: {', '.join(sorted(set(keywords)))}.")
    lines.append(f"- Corpus size: {len(papers)} papers within the last {end_year - start_year + 1} years.\n")

    if questions:
        top_question = questions[0]
        lines.append("## Quick insight\n")
        lines.append(f"- Highest cited question: **{top_question.question}** " f"({top_question.citation_count} citations, {top_question.publication_year}).")
        if trending_topics:
            lines.append(
                f"- Fastest growing topic: **{trending_topics[0].topic}** "
                f"(trend score {trending_topics[0].trend_score:+.2f}, "
                f"{trending_topics[0].recent_share*100:.1f}% of weighted citations from the last two years).\n"
            )

    lines.append("## Top citation questions\n")
    if questions:
        lines.append("| Question | Citations | Year | Journal | Key authors | DOI |")
        lines.append("|----------|-----------|------|---------|-------------|-----|")
        for item in questions:
            authors = ", ".join(item.authors[:3]) or "N/A"
            doi = f"[{item.doi}](https://doi.org/{item.doi})" if item.doi else "—"
            journal = item.journal or "—"
            lines.append(f"| {item.question} | {item.citation_count} | {item.publication_year} | {journal} | {authors} | {doi} |")
        lines.append("")
    else:
        lines.append("Not enough citation metadata to surface leading questions.\n")

    lines.append("## Emerging topics\n")
    if trending_topics:
        lines.append("| Topic | Trend score | Citation growth | Recent share | Representative papers |")
        lines.append("|-------|-------------|-----------------|--------------|------------------------|")
        for topic in trending_topics:
            papers_label = "; ".join(topic.top_papers[:2]) or "—"
            lines.append(f"| {topic.topic} | {topic.trend_score:+.2f} | {topic.citation_growth:+.1f} | {topic.recent_share*100:.1f}% | {papers_label} |")
        lines.append("")
    else:
        lines.append("No accelerating topic clusters detected; consider widening the query window.\n")

    lines.append("## Research gaps worth exploring\n")
    if research_gaps:
        for gap in research_gaps:
            doi = f" (DOI: https://doi.org/{gap.supporting_doi})" if gap.supporting_doi else ""
            lines.append(f"- **{gap.topic}** — {gap.rationale} Representative study: *{gap.representative_title}*{doi}.")
        lines.append("")
    else:
        lines.append("- No high-impact gaps detected under current filters.\n")

    lines.append("## Visualization\n")
    if chart_path and chart_path.exists():
        rel_path = chart_path.as_posix()
        caption = chart_caption or "LCA citation chart"
        lines.append(f"![{caption}]({rel_path})\n")
    else:
        lines.append("- Chart generation unavailable. Ensure the AntV MCP chart server is reachable.\n")

    lines.append("## Appendix — Sampled papers\n")
    for paper in sorted(papers, key=lambda item: item.citation_count, reverse=True)[:15]:
        doi = f"https://doi.org/{paper.doi}" if paper.doi else paper.url or "N/A"
        lines.append(f"- **{paper.title}** ({paper.year}) — {paper.journal or 'Unknown venue'} — {paper.citation_count} citations — {doi}")
    lines.append("")

    if raw_data_path:
        lines.append(f"Raw dataset cached at `{raw_data_path.as_posix()}` for further exploration.\n")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def _write_empty_report(report_path: Path, start_year: int, end_year: int) -> None:
    report_path.write_text(
        "\n".join(
            [
                f"# LCA Citation Intelligence ({start_year}–{end_year})",
                "",
                "No qualifying papers were retrieved. Verify that OpenAlex is reachable and that the query window contains relevant publications.",
            ]
        ),
        encoding="utf-8",
    )


def _write_failure_report(report_path: Path, start_year: int, end_year: int, message: str) -> None:
    report_path.write_text(
        "\n".join(
            [
                f"# LCA Citation Intelligence ({start_year}–{end_year})",
                "",
                "The workflow failed to collect literature from OpenAlex.",
                f"Error detail: {message}",
            ]
        ),
        encoding="utf-8",
    )
