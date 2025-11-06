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
from typing import Callable, Iterable, List, Optional, Sequence

from ..adapters import AdapterError
from ..core.logging import get_logger
from ..llm import DeepResearchClient, DeepResearchResult, ResearchPrompt
from ..services import ResearchServices
from .citation_template import (
    CitationQuestion,
    CitationWorkflowArtifacts,
    TrendingTopic,
    run_citation_template_workflow,
    run_lca_citation_workflow,
)
from .profiles import DeepResearchProfile, get_deep_research_profile


@dataclass(slots=True)
class DeepResearchWorkflowArtifacts:
    """Bundle of outputs produced by a deep research workflow."""

    final_report_path: Path
    citation_report_path: Path
    chart_path: Optional[Path]
    chart_caption: Optional[str]
    raw_data_path: Optional[Path]
    deep_research_summary: Optional[str]
    deep_research_response_path: Optional[Path]
    doc_variants: List[Path]
    conversion_warnings: List[str]
    citation_artifacts: CitationWorkflowArtifacts
    prompt_template_identifier: Optional[str] = None
    prompt_template_path: Optional[Path] = None
    prompt_language: Optional[str] = None
    profile_slug: Optional[str] = None
    profile_display_name: Optional[str] = None


def run_deep_research_template(
    services: ResearchServices,
    *,
    profile: DeepResearchProfile,
    output_dir: Path,
    years: int = 5,
    max_records: int = 200,
    keywords: Optional[Sequence[str]] = None,
    deep_research: bool = True,
    deep_research_prompt: Optional[str] = None,
    deep_research_instructions: Optional[str] = None,
    prompt_template: Optional[str] = None,
    prompt_language: Optional[str] = None,
    citation_runner: Optional[Callable[..., CitationWorkflowArtifacts]] = None,
) -> DeepResearchWorkflowArtifacts:
    """
    Run the end-to-end deep research workflow for the provided profile.

    Parameters
    ----------
    services:
        Shared :class:`ResearchServices` instance.
    profile:
        Domain configuration that determines keywords, prompts, and artefact naming.
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

    logger_name = f"workflow.deep_research.{profile.slug}"
    if hasattr(services, "context") and hasattr(services.context, "get_logger"):
        workflow_logger = services.context.get_logger(logger_name)
    else:  # pragma: no cover - defensive fallback
        workflow_logger = get_logger(logger_name)

    workflow_logger.info(
        "Starting deep research workflow",
        extra={
            "profile": profile.slug,
            "display_name": profile.display_name,
            "output_dir": output_dir.as_posix(),
            "years": years,
            "max_records": max_records,
            "deep_research_enabled": deep_research,
            "dry_run": is_dry_run,
        },
    )

    output_dir = output_dir.resolve()

    if is_dry_run:
        citation_report_path = output_dir / profile.citation_report_filename()
        chart_path = output_dir / profile.chart_filename()
        final_report_path = output_dir / profile.final_report_filename()
        workflow_logger.info(
            "Dry-run plan generated",
            extra={
                "output_dir": output_dir.as_posix(),
                "steps": [
                    "Run citation template workflow and derive questions, trends, gaps.",
                    "Invoke Deep Research (optional) for synthesis.",
                    "Generate Markdown report and optional document variants.",
                ],
                "profile": profile.slug,
            },
        )
        placeholder_artifacts = CitationWorkflowArtifacts(
            report_path=citation_report_path,
            chart_path=None,
            chart_caption=None,
            raw_data_path=None,
            questions=[],
            trending_topics=[],
            research_gaps=[],
            papers=[],
        )
        return DeepResearchWorkflowArtifacts(
            final_report_path=final_report_path,
            citation_report_path=citation_report_path,
            chart_path=None,
            chart_caption=None,
            raw_data_path=None,
            deep_research_summary=None,
            deep_research_response_path=None,
            doc_variants=[],
            conversion_warnings=[],
            citation_artifacts=placeholder_artifacts,
            prompt_template_identifier=None,
            prompt_template_path=None,
            prompt_language=prompt_language,
            profile_slug=profile.slug,
            profile_display_name=profile.display_name,
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    citation_report_path = output_dir / profile.citation_report_filename()
    chart_path = output_dir / profile.chart_filename()
    raw_data_path = output_dir / profile.dataset_filename()

    citation_runner = citation_runner or run_citation_template_workflow
    workflow_logger.info("Running citation workflow", extra={"profile": profile.slug})
    citation_artifacts = citation_runner(
        services,
        profile=profile,
        report_path=citation_report_path,
        chart_path=chart_path,
        raw_data_path=raw_data_path,
        years=years,
        max_records=max_records,
        keyword_overrides=keywords,
    )
    workflow_logger.debug(
        "Citation workflow completed",
        extra={
            "profile": profile.slug,
            "report_path": citation_artifacts.report_path.as_posix(),
            "chart_path": citation_artifacts.chart_path.as_posix() if citation_artifacts.chart_path else None,
            "paper_count": len(citation_artifacts.papers),
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
                effective_instructions = loaded_prompt.render(prompt_variables_map)
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
                profile=profile,
                citation_artifacts=citation_artifacts,
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

    final_report_path = output_dir / profile.final_report_filename()
    final_report_path.write_text(
        _render_final_report(
            profile=profile,
            citation_artifacts=citation_artifacts,
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
        "Generated deep research report",
        extra={
            "profile": profile.slug,
            "final_report_path": final_report_path.as_posix(),
            "doc_variants": [item.as_posix() for item in doc_variants],
            "warnings": conversion_warnings,
        },
    )

    return DeepResearchWorkflowArtifacts(
        final_report_path=final_report_path,
        citation_report_path=citation_artifacts.report_path,
        chart_path=citation_artifacts.chart_path,
        chart_caption=citation_artifacts.chart_caption,
        raw_data_path=citation_artifacts.raw_data_path,
        deep_research_summary=deep_summary,
        deep_research_response_path=deep_response_path,
        doc_variants=doc_variants,
        conversion_warnings=conversion_warnings,
        citation_artifacts=citation_artifacts,
        prompt_template_identifier=getattr(loaded_prompt, "identifier", None),
        prompt_template_path=getattr(loaded_prompt, "path", None),
        prompt_language=getattr(loaded_prompt, "language", prompt_language),
        profile_slug=profile.slug,
        profile_display_name=profile.display_name,
    )


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
    lca_runner: Optional[Callable[..., CitationWorkflowArtifacts]] = None,
) -> DeepResearchWorkflowArtifacts:
    """Backward-compatible entry that keeps the original LCA naming."""

    profile = get_deep_research_profile("lca")
    runner = lca_runner or run_lca_citation_workflow
    return run_deep_research_template(
        services,
        profile=profile,
        output_dir=output_dir,
        years=years,
        max_records=max_records,
        keywords=keywords,
        deep_research=deep_research,
        deep_research_prompt=deep_research_prompt,
        deep_research_instructions=deep_research_instructions,
        prompt_template=prompt_template,
        prompt_language=prompt_language,
        citation_runner=runner,
    )


def _run_deep_research(
    *,
    profile: DeepResearchProfile,
    citation_artifacts: CitationWorkflowArtifacts,
    years: int,
    prompt_override: Optional[str],
    instructions_override: Optional[str],
) -> DeepResearchResult:
    prompt = ResearchPrompt(question=prompt_override.strip()) if prompt_override else _build_default_prompt(profile, years)
    context = _build_prompt_context(citation_artifacts)
    if context:
        prompt.context = context
    elif profile.prompt_context_template:
        prompt.context = profile.prompt_context_template.format(years=years)
    client = DeepResearchClient()
    return client.run(
        prompt,
        instructions=instructions_override or profile.prompt_instructions,
        max_tool_calls=30,
    )


def _build_default_prompt(profile: DeepResearchProfile, years: int) -> ResearchPrompt:
    return ResearchPrompt(
        question=profile.prompt_question,
        follow_up_questions=list(profile.prompt_follow_ups),
        context=profile.prompt_context_template.format(years=years),
    )


def _build_prompt_context(citation_artifacts: CitationWorkflowArtifacts) -> str:
    lines: List[str] = []
    if citation_artifacts.questions:
        lines.append("Top citation questions:")
        for item in citation_artifacts.questions[:5]:
            lines.append(f"- {item.paper_title} ({item.citation_count} citations, {item.publication_year}); DOI: {item.doi or 'N/A'}")
    if citation_artifacts.trending_topics:
        lines.append("\nTrending concepts with positive citation slopes:")
        for topic in citation_artifacts.trending_topics[:5]:
            lines.append(f"- {topic.topic} (trend score {topic.trend_score:+.2f}, recent share {topic.recent_share*100:.1f}%)")
    if citation_artifacts.research_gaps:
        lines.append("\nSparse but high-impact gaps:")
        for gap in citation_artifacts.research_gaps[:5]:
            lines.append(f"- {gap.topic} ({gap.paper_count} papers, {gap.avg_citations:.1f} average citations) — {gap.rationale}")
    return "\n".join(lines).strip()


def _derive_start_year(years: int) -> int:
    today = date.today()
    return max(1900, today.year - max(years, 1) + 1)


def _render_final_report(
    *,
    profile: DeepResearchProfile,
    citation_artifacts: CitationWorkflowArtifacts,
    deep_summary: Optional[str],
    start_year: int,
    end_year: int,
    keywords: Optional[Sequence[str]],
) -> str:
    lines: List[str] = []
    lines.append(f"# {profile.deep_report_title} ({start_year}–{end_year})\n")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"_Generated {generated} by TianGong Sustainability CLI_\n")

    lines.append("## Executive Summary\n")
    if deep_summary:
        lines.append(deep_summary.strip() + "\n")
    else:
        lines.append("Deep Research synthesis was unavailable. See the deterministic citation scan and raw data sections below.\n")

    lines.append("## Citation Highlights\n")
    keyword_label = ", ".join(keywords) if keywords else ", ".join(profile.normalised_keywords())
    lines.append(f"- Rolling window: **{start_year}–{end_year}**")
    lines.append(f"- Keyword focus: **{keyword_label}**")
    lines.append(f"- Processed papers: **{len(citation_artifacts.papers)}**\n")
    lines.append(f"Full citation table: [`{citation_artifacts.report_path.name}`]({citation_artifacts.report_path.name}).\n")
    if citation_artifacts.chart_path and citation_artifacts.chart_path.exists():
        caption = citation_artifacts.chart_caption or f"{profile.display_name} citation visualisation"
        relative = citation_artifacts.chart_path.name
        lines.append(f"![{caption}]({relative})\n")

    lines.append("### Top Citation Questions\n")
    if citation_artifacts.questions:
        lines.extend(_render_question_table(citation_artifacts.questions[:8]))
    else:
        lines.append("- No citation questions were extracted.\n")

    lines.append("### Emerging Topics\n")
    if citation_artifacts.trending_topics:
        lines.extend(_render_trending_table(citation_artifacts.trending_topics[:8]))
    else:
        lines.append("- No accelerating topic clusters detected in the rolling window.\n")

    lines.append("### Research Gaps with High Citation Potential\n")
    if citation_artifacts.research_gaps:
        for gap in citation_artifacts.research_gaps[:8]:
            doi = f"https://doi.org/{gap.supporting_doi}" if gap.supporting_doi else "N/A"
            lines.append(f"- **{gap.topic}** — {gap.rationale} Representative study: *{gap.representative_title}* ({doi}).")
        lines.append("")
    else:
        lines.append("- No high-leverage gaps identified.\n")

    lines.append("## Assets & Raw Data\n")
    dataset_name = citation_artifacts.raw_data_path.name if citation_artifacts.raw_data_path else "N/A"
    lines.append(f"- Citation dataset: `{dataset_name}`")
    lines.append(f"- Citation report: `{citation_artifacts.report_path.name}`")
    if citation_artifacts.chart_path:
        lines.append(f"- Chart: `{citation_artifacts.chart_path.name}`")
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
