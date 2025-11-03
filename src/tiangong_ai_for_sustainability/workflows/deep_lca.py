"""
Composite workflow that combines deterministic citation analysis with optional
OpenAI Deep Research synthesis to produce a rich Markdown report.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Mapping, Optional, Sequence

from ..adapters import AdapterError
from ..core.logging import get_logger
from ..deep_research import DeepResearchClient, DeepResearchResult, ResearchPrompt
from ..services import ResearchServices
from .lca_citations import (
    CitationQuestion,
    LCACitationWorkflowArtifacts,
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
    doc_variants: List[Path]
    conversion_warnings: List[str]
    lca_artifacts: LCACitationWorkflowArtifacts
    prompt_template_identifier: Optional[str] = None
    prompt_template_path: Optional[Path] = None
    prompt_language: Optional[str] = None


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
    prompt_template: Optional[str] = None,
    prompt_language: Optional[str] = None,
    lca_runner: Optional[Callable[..., LCACitationWorkflowArtifacts]] = None,
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
        Direct overrides for the Deep Research request. Helpful for quick,
        ad-hoc customisation without switching templates.
    prompt_template / prompt_language:
        Optional template selection parameters. When instructions are not
        provided explicitly, the helper resolves the referenced template (alias
        or path) and uses its contents as the Deep Research instruction block.
        The language hint chooses between English/Chinese defaults.
    lca_runner:
        Dependency injection hook used by tests; defaults to
        :func:`run_lca_citation_workflow`.
    """

    context = getattr(services, "context", None)
    options = getattr(context, "options", None)
    is_dry_run = bool(getattr(options, "dry_run", False))

    if hasattr(services, "context") and hasattr(services.context, "get_logger"):
        workflow_logger = services.context.get_logger("workflow.deep_lca")
    else:  # pragma: no cover - defensive fallback
        workflow_logger = get_logger("workflow.deep_lca")

    workflow_logger.info(
        "Starting deep LCA workflow",
        extra={
            "output_dir": output_dir.as_posix(),
            "years": years,
            "max_records": max_records,
            "deep_research_enabled": deep_research,
            "dry_run": is_dry_run,
        },
    )

    output_dir = output_dir.resolve()

    if is_dry_run:
        lca_report_path = output_dir / "lca_citations.md"
        chart_path = output_dir / "lca_trends.png"
        final_report_path = output_dir / "deep_lca_report.md"
        workflow_logger.info(
            "Dry-run plan generated",
            extra={
                "output_dir": output_dir.as_posix(),
                "steps": [
                    "Run LCA citation workflow and derive questions, trends, gaps.",
                    "Invoke Deep Research (optional) for synthesis.",
                    "Generate Markdown report and optional document variants.",
                ],
            },
        )
        placeholder_artifacts = LCACitationWorkflowArtifacts(
            report_path=lca_report_path,
            chart_path=None,
            chart_caption=None,
            raw_data_path=None,
            questions=[],
            trending_topics=[],
            research_gaps=[],
            papers=[],
        )
        return DeepLCAWorkflowArtifacts(
            final_report_path=final_report_path,
            citation_report_path=lca_report_path,
            chart_path=None,
            chart_caption=None,
            raw_data_path=None,
            deep_research_summary=None,
            deep_research_response_path=None,
            doc_variants=[],
            conversion_warnings=[],
            lca_artifacts=placeholder_artifacts,
            prompt_template_identifier=None,
            prompt_template_path=None,
            prompt_language=prompt_language,
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    lca_report_path = output_dir / "lca_citations.md"
    chart_path = output_dir / "lca_trends.png"
    raw_data_path = output_dir / "lca_citations.json"

    lca_runner = lca_runner or run_lca_citation_workflow
    workflow_logger.info("Running LCA citation workflow")
    lca_artifacts = lca_runner(
        services,
        report_path=lca_report_path,
        chart_path=chart_path,
        raw_data_path=raw_data_path,
        years=years,
        max_records=max_records,
        keyword_overrides=keywords,
    )
    workflow_logger.debug(
        "LCA citation workflow completed",
        extra={
            "report_path": lca_artifacts.report_path.as_posix(),
            "chart_path": lca_artifacts.chart_path.as_posix() if lca_artifacts.chart_path else None,
            "paper_count": len(lca_artifacts.papers),
        },
    )

    deep_summary: Optional[str] = None
    deep_response_path: Optional[Path] = None
    loaded_prompt = None
    prompt_variables = getattr(getattr(services, "context", None), "options", None)
    prompt_variables_map = dict(getattr(prompt_variables, "prompt_variables", {}) if prompt_variables else {})
    if prompt_variables_map:
        workflow_logger.debug("Prompt variables provided", extra={"keys": sorted(prompt_variables_map)})

    if deep_research:
        effective_instructions = deep_research_instructions
        template_hint = prompt_template
        language_hint = prompt_language
        if effective_instructions is None:
            try:
                loaded_prompt = services.load_prompt_template(template_hint, language=language_hint)
            except AdapterError as exc:
                workflow_logger.warning(
                    "Prompt template unavailable; falling back to default Deep Research instructions",
                    extra={"error": str(exc)},
                )
            else:
                effective_instructions = _apply_prompt_variables(loaded_prompt.content, prompt_variables_map)
                workflow_logger.info(
                    "Using prompt template for Deep Research instructions",
                    extra={
                        "identifier": loaded_prompt.identifier,
                        "language": loaded_prompt.language,
                        "path": loaded_prompt.path.as_posix(),
                    },
                )
        try:
            workflow_logger.info("Invoking Deep Research synthesis")
            result = _run_deep_research(
                lca_artifacts=lca_artifacts,
                years=years,
                prompt_override=deep_research_prompt,
                instructions_override=effective_instructions,
            )
        except Exception as exc:  # pragma: no cover - depends on runtime credentials
            deep_summary = f"Deep Research unavailable: {exc}"
            workflow_logger.error("Deep Research invocation failed", extra={"error": str(exc)})
        else:
            deep_summary = result.output_text.strip() or None
            deep_response_path = output_dir / "deep_research.json"
            deep_response_path.write_text(
                json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            workflow_logger.info("Deep Research synthesis completed", extra={"response_path": deep_response_path.as_posix()})
    else:
        workflow_logger.info("Deep Research disabled for this run")

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

    doc_variants, conversion_warnings = _generate_document_variants(
        markdown_path=final_report_path,
        output_dir=output_dir,
    )

    workflow_logger.info(
        "Generated deep LCA report",
        extra={
            "final_report_path": final_report_path.as_posix(),
            "doc_variants": [item.as_posix() for item in doc_variants],
            "warnings": conversion_warnings,
        },
    )

    return DeepLCAWorkflowArtifacts(
        final_report_path=final_report_path,
        citation_report_path=lca_artifacts.report_path,
        chart_path=lca_artifacts.chart_path,
        chart_caption=lca_artifacts.chart_caption,
        raw_data_path=lca_artifacts.raw_data_path,
        deep_research_summary=deep_summary,
        deep_research_response_path=deep_response_path,
        doc_variants=doc_variants,
        conversion_warnings=conversion_warnings,
        lca_artifacts=lca_artifacts,
        prompt_template_identifier=getattr(loaded_prompt, "identifier", None),
        prompt_template_path=getattr(loaded_prompt, "path", None),
        prompt_language=getattr(loaded_prompt, "language", prompt_language),
    )


def _run_deep_research(
    *,
    lca_artifacts: LCACitationWorkflowArtifacts,
    years: int,
    prompt_override: Optional[str],
    instructions_override: Optional[str],
) -> DeepResearchResult:
    prompt = ResearchPrompt(question=prompt_override.strip()) if prompt_override else _build_default_prompt(years)
    context = _build_prompt_context(lca_artifacts)
    if context:
        prompt.context = context
    client = DeepResearchClient()
    return client.run(
        prompt,
        instructions=instructions_override
        or (
            "Synthesize the findings into concise sections that complement the deterministic "
            "citation scan provided in the context. Highlight citation leaders, accelerating "
            "themes, and unanswered questions."
        ),
        max_tool_calls=30,
    )


def _apply_prompt_variables(content: str, variables: Mapping[str, str]) -> str:
    if not variables:
        return content
    rendered = content
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _build_default_prompt(years: int) -> ResearchPrompt:
    return ResearchPrompt(
        question=("Investigate how recent peer-reviewed life cycle assessment (LCA) research " "connects planetary boundaries with the Sustainable Development Goals."),
        follow_up_questions=[
            "Which research questions attract the highest citation energy and why?",
            "Which LCA sub-topics show accelerating citation trends in the last few years?",
            "Where do clear research gaps remain that could yield high impact if addressed?",
        ],
        context=(f"Time horizon: last {years} years. Assume the deterministic citation scan has already " "filtered relevant journals and returns structured summaries."),
    )


def _build_prompt_context(lca_artifacts: LCACitationWorkflowArtifacts) -> str:
    lines: List[str] = []
    if lca_artifacts.questions:
        lines.append("Top citation questions:")
        for item in lca_artifacts.questions[:5]:
            lines.append(f"- {item.paper_title} ({item.citation_count} citations, {item.publication_year}); DOI: {item.doi or 'N/A'}")
    if lca_artifacts.trending_topics:
        lines.append("\nTrending concepts with positive citation slopes:")
        for topic in lca_artifacts.trending_topics[:5]:
            lines.append(f"- {topic.topic} (trend score {topic.trend_score:+.2f}, recent share {topic.recent_share*100:.1f}%)")
    if lca_artifacts.research_gaps:
        lines.append("\nSparse but high-impact gaps:")
        for gap in lca_artifacts.research_gaps[:5]:
            lines.append(f"- {gap.topic} ({gap.paper_count} papers, {gap.avg_citations:.1f} average citations) — {gap.rationale}")
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
        lines.append("Deep Research synthesis was unavailable. See the deterministic citation scan and raw data sections below.\n")

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
            lines.append(f"- **{gap.topic}** — {gap.rationale} Representative study: *{gap.representative_title}* ({doi}).")
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


def _generate_document_variants(
    *,
    markdown_path: Path,
    output_dir: Path,
) -> tuple[List[Path], List[str]]:
    """Convert the Markdown report into additional formats using Pandoc when available."""

    pandoc_path = shutil.which("pandoc")
    outputs: List[Path] = []
    warnings: List[str] = []

    if pandoc_path is None:
        warnings.append("Pandoc not found on PATH; skipped generating PDF/DOCX variants. " "Install pandoc (and a TeX engine for PDF) to enable automatic conversions.")
        return outputs, warnings

    resource_path = f"{markdown_path.parent.resolve()}:{output_dir.resolve()}"
    conversions = {
        "pdf": ["--from=gfm", f"--resource-path={resource_path}", "-o"],
        "docx": ["--from=gfm", f"--resource-path={resource_path}", "-o"],
    }

    for extension, base_args in conversions.items():
        target = output_dir / f"{markdown_path.stem}.{extension}"
        cmd = [pandoc_path, str(markdown_path), *base_args, str(target)]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            log = exc.stderr.decode("utf-8", "ignore") if exc.stderr else ""
            warnings.append(f"Failed to generate {extension.upper()} via pandoc: {exc}. Output: {log.strip()}")
            continue
        outputs.append(target)

    return outputs, warnings


def _render_question_table(questions: Iterable[CitationQuestion]) -> List[str]:
    rows = [
        "| Question | Citations | Year | Journal | DOI |",
        "|----------|-----------|------|---------|-----|",
    ]
    for item in questions:
        doi_link = f"[{item.doi}](https://doi.org/{item.doi})" if item.doi else "—"
        rows.append(f"| {item.question} | {item.citation_count} | {item.publication_year} | {item.journal or '—'} | {doi_link} |")
    rows.append("")
    return rows


def _render_trending_table(topics: Iterable[TrendingTopic]) -> List[str]:
    rows = [
        "| Topic | Trend score | Citation growth | Recent share |",
        "|-------|-------------|-----------------|--------------|",
    ]
    for topic in topics:
        rows.append(f"| {topic.topic} | {topic.trend_score:+.2f} | {topic.citation_growth:+.1f} | {topic.recent_share*100:.1f}% |")
    rows.append("")
    return rows
