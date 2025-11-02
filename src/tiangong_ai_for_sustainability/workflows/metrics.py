"""
Workflow for collecting scarcity and biodiversity metrics from deterministic sources.

This module focuses on OpenAlex-based retrieval because it offers a reliable,
rate-limited API that maps well onto the trending indicators surfaced in the
latest literature review (resource scarcity footprints and biodiversity loss
factors). The workflow intentionally keeps payloads compact so they can be
consumed both by the CLI and downstream automation steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..core.logging import get_logger
from ..services import ResearchServices


@dataclass(slots=True)
class MetricSummary:
    """Aggregate statistics for a single sustainability metric."""

    metric_id: str
    label: str
    total_works: int
    total_citations: int
    citation_trend: Dict[int, int]
    work_count_by_year: Dict[int, int]
    top_works: List[Dict[str, Any]]
    top_concepts: List[Dict[str, Any]]


@dataclass(slots=True)
class TrendingMetricsArtifacts:
    """Artifacts returned by :func:`run_trending_metrics_workflow`."""

    metrics: List[MetricSummary]
    raw_records: Dict[str, List[Dict[str, Any]]]
    output_path: Optional[Path] = None
    plan: Optional[List[str]] = None


TRENDING_METRIC_CONFIGS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "resource_scarcity",
        "label": "Resource Scarcity Footprint",
        "search": '"resource scarcity" AND ("life cycle assessment" OR LCA)',
    },
    {
        "id": "planetary_footprint",
        "label": "Planetary Footprint Indicators",
        "search": '"planetary boundaries" AND footprint AND ("life cycle assessment" OR LCA)',
    },
    {
        "id": "biodiversity_loss",
        "label": "Biodiversity Loss Factors",
        "search": '"biodiversity" AND ("life cycle assessment" OR LCA) AND (loss OR impact)',
    },
    {
        "id": "sustainable_nanotechnology",
        "label": "Sustainable Nanotechnology Footprints",
        "search": '"nanotechnology" AND sustainability AND ("life cycle assessment" OR LCA)',
    },
)


def run_trending_metrics_workflow(
    services: ResearchServices,
    *,
    start_year: int = 2020,
    end_year: Optional[int] = None,
    max_records_per_metric: int = 120,
    output_path: Optional[Path] = None,
) -> TrendingMetricsArtifacts:
    """
    Retrieve footprint and biodiversity indicators from OpenAlex.

    Parameters
    ----------
    services:
        Shared :class:`ResearchServices` instance.
    start_year:
        Lower bound for publication year filters (inclusive). Defaults to 2020 to
        match the five-year window used in the latest analysis.
    end_year:
        Upper bound for publication year filters (inclusive). When ``None`` the
        current calendar year is used.
    max_records_per_metric:
        Safety cap for the number of OpenAlex works fetched per metric.
    output_path:
        Optional JSON file to persist the aggregated metrics plus a trimmed raw
        sample.
    """

    context = getattr(services, "context", None)
    options = getattr(context, "options", None)
    is_dry_run = bool(getattr(options, "dry_run", False))

    if end_year is None:
        end_year = datetime.now(UTC).year

    logger = getattr(context, "get_logger", None)
    if callable(logger):
        workflow_logger = context.get_logger("workflow.metrics")
    else:  # pragma: no cover - fallback for limited contexts
        workflow_logger = get_logger("workflow.metrics")

    workflow_logger.info(
        "Starting trending metrics workflow",
        extra={
            "start_year": start_year,
            "end_year": end_year,
            "max_records_per_metric": max_records_per_metric,
            "output_path": output_path.as_posix() if output_path else None,
            "dry_run": is_dry_run,
        },
    )

    if is_dry_run:
        plan = [
            "Load OpenAlex client and confirm connectivity.",
            "For each metric (resource scarcity, planetary footprint, biodiversity loss, sustainable nanotechnology):",
            f"  - Query OpenAlex for works published between {start_year} and {end_year}.",
            "  - Aggregate citation totals and counts by publication year.",
            "  - Extract top works and high-signal concepts.",
            "Persist results as JSON when --output is supplied.",
        ]
        workflow_logger.info("Dry-run mode enabled; returning plan only.", extra={"plan_steps": len(plan)})
        return TrendingMetricsArtifacts(metrics=[], raw_records={}, plan=plan, output_path=output_path)

    metrics: List[MetricSummary] = []
    raw_records: Dict[str, List[Dict[str, Any]]] = {}

    client = services.openalex_client()
    select_fields = [
        "id",
        "display_name",
        "publication_year",
        "cited_by_count",
        "doi",
        "ids",
        "concepts",
        "authorships",
        "primary_location",
        "sustainable_development_goals",
    ]

    for config in TRENDING_METRIC_CONFIGS:
        metric_id = config["id"]
        label = config["label"]
        search_query = config["search"]

        workflow_logger.info(
            "Querying OpenAlex for metric",
            extra={"metric_id": metric_id, "label": label, "search": search_query},
        )

        filters = {
            "from_publication_date": f"{start_year}-01-01",
            "to_publication_date": f"{end_year}-12-31",
            "primary_location.source.type": "journal",
        }

        records: List[Dict[str, Any]] = []
        for work in client.iterate_works(
            search=search_query,
            filters=filters,
            sort="cited_by_count:desc",
            select=select_fields,
            per_page=100,
            max_pages=5,
        ):
            records.append(work)
            if len(records) >= max_records_per_metric:
                break

        if not records:
            workflow_logger.warning("No OpenAlex records returned for metric", extra={"metric_id": metric_id})
            metrics.append(
                MetricSummary(
                    metric_id=metric_id,
                    label=label,
                    total_works=0,
                    total_citations=0,
                    citation_trend={},
                    work_count_by_year={},
                    top_works=[],
                    top_concepts=[],
                )
            )
            raw_records[metric_id] = []
            continue

        summary = _summarise_records(metric_id, label, records, workflow_logger)
        metrics.append(summary)
        # Keep only the top 20 raw entries to avoid huge payloads
        raw_records[metric_id] = records[:20]

    artifacts = TrendingMetricsArtifacts(metrics=metrics, raw_records=raw_records)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "start_year": start_year,
            "end_year": end_year,
            "metrics": [_serialise_summary(summary) for summary in metrics],
            "raw_records": raw_records,
        }
        output_path.write_text(_json_dumps(payload), encoding="utf-8")
        artifacts.output_path = output_path
        workflow_logger.info("Metrics written to output file", extra={"output_path": output_path.as_posix()})

    workflow_logger.info("Trending metrics workflow complete", extra={"metric_count": len(metrics)})
    return artifacts


def _summarise_records(
    metric_id: str,
    label: str,
    records: Iterable[Mapping[str, Any]],
    logger,
) -> MetricSummary:
    citation_trend: Dict[int, int] = {}
    work_count_by_year: Dict[int, int] = {}
    concept_scores: Dict[str, float] = {}

    def _coerce_int(value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return 0

    for work in records:
        year = work.get("publication_year")
        citations = _coerce_int(work.get("cited_by_count"))
        if isinstance(year, int):
            citation_trend[year] = citation_trend.get(year, 0) + citations
            work_count_by_year[year] = work_count_by_year.get(year, 0) + 1

        concepts = work.get("concepts") or []
        if isinstance(concepts, list):
            for concept in concepts:
                if not isinstance(concept, Mapping):
                    continue
                name = concept.get("display_name")
                score = concept.get("score") if isinstance(concept.get("score"), (int, float)) else 0.0
                level = concept.get("level")
                if not name or not isinstance(name, str):
                    continue
                if level is not None and level > 2:
                    continue
                if score < 0.35:
                    continue
                concept_scores[name] = concept_scores.get(name, 0.0) + float(citations or 1)

    total_citations = sum(citation_trend.values())
    total_works = sum(work_count_by_year.values())

    top_works = sorted(
        (
            {
                "title": work.get("display_name"),
                "year": work.get("publication_year"),
                "cited_by_count": _coerce_int(work.get("cited_by_count")),
                "doi": _extract_doi(work),
            }
            for work in records
        ),
        key=lambda entry: entry["cited_by_count"],
        reverse=True,
    )[:5]

    top_concepts = sorted(
        ({"name": name, "weighted_citations": round(score, 2)} for name, score in concept_scores.items()),
        key=lambda entry: entry["weighted_citations"],
        reverse=True,
    )[:6]

    logger.debug(
        "Summarised metric records",
        extra={
            "metric_id": metric_id,
            "total_works": total_works,
            "total_citations": total_citations,
            "top_concepts": [concept["name"] for concept in top_concepts],
        },
    )

    return MetricSummary(
        metric_id=metric_id,
        label=label,
        total_works=total_works,
        total_citations=total_citations,
        citation_trend=dict(sorted(citation_trend.items())),
        work_count_by_year=dict(sorted(work_count_by_year.items())),
        top_works=top_works,
        top_concepts=top_concepts,
    )


def _extract_doi(work: Mapping[str, Any]) -> Optional[str]:
    doi = work.get("doi")
    if isinstance(doi, str) and doi:
        return doi
    ids = work.get("ids")
    if isinstance(ids, Mapping):
        doi_val = ids.get("doi")
        if isinstance(doi_val, str) and doi_val:
            return doi_val
    return None


def _serialise_summary(summary: MetricSummary) -> Dict[str, Any]:
    return {
        "metric_id": summary.metric_id,
        "label": summary.label,
        "total_works": summary.total_works,
        "total_citations": summary.total_citations,
        "citation_trend": summary.citation_trend,
        "work_count_by_year": summary.work_count_by_year,
        "top_works": summary.top_works,
        "top_concepts": summary.top_concepts,
    }


def _json_dumps(payload: Any) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)
