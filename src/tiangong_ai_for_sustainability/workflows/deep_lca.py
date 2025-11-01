"""
Composite workflow that combines deterministic citation analysis with optional
OpenAI Deep Research synthesis to produce a rich Markdown report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

from ..deep_research import DeepResearchClient, DeepResearchResult, ResearchPrompt
from ..services import ResearchServices
from .lca_citations import (
    LCACitationWorkflowArtifacts,
    CitationQuestion,
    ResearchGap,
    TrendingTopic,
    run_lca_citation_workflow,
)


@dataclass(slots=True)
class DeepLCAWorkflowArtifacts:
    """Bundle of outputs produced by the deep LCA workflow."""

    final_report_path: Path
    citation_report_path: Path
    chart_path: Optional[Path]
    chart_caption: Optional[str]
    raw_data_path: Optional[Path]
    deep_research_summary: Optional[str]
    deep_research_response_path: Optional[Path]
    lca_artifacts: LCACitationWorkflowArtifacts


def run_deep_lca_report(
    services: ResearchServices,
    *,
    output_dir: Path,
    years: int = 5,
    max_records: int = 200,
    keywords: Optional[Sequence[str]] = None,
    deep_research: bool = True,
    deep_research_prompt: Optional[str] = None,
    deep_research_instructions: Optional[str] = None,
    lca_runner: Optional[
        Callable[..., LCACitationWorkflowArtifacts]
    ] = None,
) -> DeepLCAWorkflowArtifacts:
    """
    Run the end-to-end deep LCA workflow.

    Parameters
    ----------
    services:
        Shared :class:`ResearchServices` instance.
    output_dir:
        Directory where all artefacts (reports, charts, datasets) will be stored.
    years:
        Rolling window (inclusive) for the citation scan.
    max_records:
        Maximum OpenAlex records to ingest.
    keywords:
        Optional keyword overrides for the citation workflow.
    deep_research:
        Toggle for invoking the OpenAI Deep Research client. When ``False`` the
        workflow produces deterministic outputs only.
    deep_research_prompt / deep_research_instructions:
        Overrides for the Deep Research request. Helpful for user customisation.
    lca_runner:
        Dependency injection hook used by tests; defaults to
        :func:`run_lca_citation_workflow`.
    """

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    lca_report_path = output_dir / "lca_citations.md"
    chart_path = output_dir / "lca_trends.png"
    raw_data_path = output_dir / "lca_citations.json"

    lca_runner = lca_runner or run_lca_citation_workflow
    lca_artifacts = lca_runner(
        services,
        report_path=lca_report_path,
        chart_path=chart_path,
        raw_data_path=raw_data_path,
        years=years,
        max_records=max_records,
        keyword_overrides=keywords,
    )

    deep_summary: Optional[str] = None
    deep_response_path: Optional[Path] = None

    if deep_research:
        try:
            result = _run_deep_research(
                lca_artifacts=lca_artifacts,
                years=years,
                prompt_override=deep_research_prompt,
                instructions_override=deep_research_instructions,
            )
        except Exception as exc:  # pragma: no cover - depends on runtime credentials
            deep_summary = f"Deep Research unavailable: {exc}"
        else:
            deep_summary = result.output_text.strip() or None
            deep_response_path = output_dir / "deep_research.json"
            deep_response_path.write_text(
                json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    final_report_path = output_dir / "deep_lca_report.md"
    final_report_path.write_text(
        _render_final_report(
            lca_artifacts=lca_artifacts,
            deep_summary=deep_summary,
            start_year=_derive_start_year(years),
            end_year=date.today().year,
            keywords=keywords,
        ),
        encoding="utf-8",
    )

    return DeepLCAWorkflowArtifacts(
        final_report_path=final_report_path,
        citation_report_path=lca_artifacts.report_path,
        chart_path=lca_artifacts.chart_path,
        chart_caption=lca_artifacts.chart_caption,
        raw_data_path=lca_artifacts.raw_data_path,
        deep_research_summary=deep_summary,
        deep_research_response_path=deep_response_path,
        lca_artifacts=lca_artifacts,
    )


def _run_deep_research(
    *,
    lca_artifacts: LCACitationWorkflowArtifacts,
    years: int,
    prompt_override: Optional[str],
    instructions_override: Optional[str],
) -> DeepResearchResult:
    prompt = (
        ResearchPrompt(question=prompt_override.strip())
        if prompt_override
        else _build_default_prompt(years)
    )
    context = _build_prompt_context(lca_artifacts)
    if context:
        prompt.context = context
    client = DeepResearchClient()
    return client.run(
        prompt,
        instructions=instructions_override
        or "Synthesize the findings into concise sections that complement the deterministic citation scan provided in the context. Highlight citation leaders, accelerating themes, and unanswered questions.",
        max_tool_calls=30,
    )


def _build_default_prompt(years: int) -> ResearchPrompt:
    return ResearchPrompt(
        question=(
            "Investigate how recent peer-reviewed life cycle assessment (LCA) research "
            "connects planetary boundaries with the Sustainable Development Goals."
        ),
        follow_up_questions=[
            "Which research questions attract the highest citation energy and why?",
            "Which LCA sub-topics show accelerating citation trends in the last few years?",
            "Where do clear research gaps remain that could yield high impact if addressed?",
        ],
        context=(
            f"Time horizon: last {years} years. Assume the deterministic citation scan has already "
            "filtered relevant journals and returns structured summaries."
        ),
    )


def _build_prompt_context(lca_artifacts: LCACitationWorkflowArtifacts) -> str:
    lines: List[str] = []
    if lca_artifacts.questions:
        lines.append("Top citation questions:")
        for item in lca_artifacts.questions[:5]:
            lines.append(
                f"- {item.paper_title} ({item.citation_count} citations, {item.publication_year}); DOI: {item.doi or 'N/A'}"
            )
    if lca_artifacts.trending_topics:
        lines.append("\nTrending concepts with positive citation slopes:")
        for topic in lca_artifacts.trending_topics[:5]:
            lines.append(
                f"- {topic.topic} (trend score {topic.trend_score:+.2f}, recent share {topic.recent_share*100:.1f}%)"
            )
    if lca_artifacts.research_gaps:
        lines.append("\nSparse but high-impact gaps:")
        for gap in lca_artifacts.research_gaps[:5]:
            lines.append(
                f"- {gap.topic} ({gap.paper_count} papers, {gap.avg_citations:.1f} average citations) — {gap.rationale}"
            )
    return "\n".join(lines).strip()


def _derive_start_year(years: int) -> int:
    today = date.today()
    return max(1900, today.year - max(years, 1) + 1)


def _render_final_report(
    *,
    lca_artifacts: LCACitationWorkflowArtifacts,
    deep_summary: Optional[str],
    start_year: int,
    end_year: int,
    keywords: Optional[Sequence[str]],
) -> str:
    lines: List[str] = []
    lines.append(f"# LCA × Planetary Boundaries Deep Research ({start_year}–{end_year})\n")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"_Generated {generated} by TianGong Sustainability CLI_\n")

    lines.append("## Executive Summary\n")
    if deep_summary:
        lines.append(deep_summary.strip() + "\n")
    else:
        lines.append(
            "Deep Research synthesis was unavailable. See the deterministic citation scan and raw data sections below.\n"
        )

    lines.append("## Citation Highlights\n")
    keyword_label = ", ".join(keywords) if keywords else "life cycle assessment, sustainability, planetary boundaries, SDGs"
    lines.append(f"- Rolling window: **{start_year}–{end_year}**")
    lines.append(f"- Keyword focus: **{keyword_label}**")
    lines.append(f"- Processed papers: **{len(lca_artifacts.papers)}**\n")
    lines.append(f"Full citation table: [`{lca_artifacts.report_path.name}`]({lca_artifacts.report_path.name}).\n")
    if lca_artifacts.chart_path and lca_artifacts.chart_path.exists():
        caption = lca_artifacts.chart_caption or "LCA citation visualisation"
        relative = lca_artifacts.chart_path.name
        lines.append(f"![{caption}]({relative})\n")

    lines.append("### Top Citation Questions\n")
    if lca_artifacts.questions:
        lines.extend(_render_question_table(lca_artifacts.questions[:8]))
    else:
        lines.append("- No citation questions were extracted.\n")

    lines.append("### Emerging Topics\n")
    if lca_artifacts.trending_topics:
        lines.extend(_render_trending_table(lca_artifacts.trending_topics[:8]))
    else:
        lines.append("- No accelerating topic clusters detected in the rolling window.\n")

    lines.append("### Research Gaps with High Citation Potential\n")
    if lca_artifacts.research_gaps:
        for gap in lca_artifacts.research_gaps[:8]:
            doi = f"https://doi.org/{gap.supporting_doi}" if gap.supporting_doi else "N/A"
            lines.append(
                f"- **{gap.topic}** — {gap.rationale} Representative study: *{gap.representative_title}* ({doi})."
            )
        lines.append("")
    else:
        lines.append("- No high-leverage gaps identified.\n")

    lines.append("## Assets & Raw Data\n")
    dataset_name = lca_artifacts.raw_data_path.name if lca_artifacts.raw_data_path else "N/A"
    lines.append(f"- Citation dataset: `{dataset_name}`")
    lines.append(f"- Citation report: `{lca_artifacts.report_path.name}`")
    if lca_artifacts.chart_path:
        lines.append(f"- Chart: `{lca_artifacts.chart_path.name}`")
    if deep_summary:
        lines.append("- Deep Research summary embedded above.")
    lines.append("")

    return "\n".join(lines)


def _render_question_table(questions: Iterable[CitationQuestion]) -> List[str]:
    rows = [
        "| Question | Citations | Year | Journal | DOI |",
        "|----------|-----------|------|---------|-----|",
    ]
    for item in questions:
        doi_link = f"[{item.doi}](https://doi.org/{item.doi})" if item.doi else "—"
        rows.append(
            f"| {item.question} | {item.citation_count} | {item.publication_year} | {item.journal or '—'} | {doi_link} |"
        )
    rows.append("")
    return rows


def _render_trending_table(topics: Iterable[TrendingTopic]) -> List[str]:
    rows = [
        "| Topic | Trend score | Citation growth | Recent share |",
        "|-------|-------------|-----------------|--------------|",
    ]
    for topic in topics:
        rows.append(
            f"| {topic.topic} | {topic.trend_score:+.2f} | {topic.citation_growth:+.1f} | {topic.recent_share*100:.1f}% |"
        )
    rows.append("")
    return rows
