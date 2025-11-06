"""
Primary Typer application wiring for the sustainability research CLI.

Phase 0 focuses on surfacing data source catalogue commands so Codex and human
operators can quickly assess which integrations are available before invoking
heavier workflows.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from ..adapters import AdapterError
from ..adapters.api.base import APIError
from ..core import DataSourceDescriptor, DataSourceRegistry, DataSourceStatus, ExecutionContext, ExecutionOptions, RegistryLoadError
from ..services import ResearchServices
from ..workflows import (
    run_citation_template_workflow,
    run_deep_research_template,
    run_paper_search,
    run_simple_workflow,
    run_synthesis_workflow,
    run_trending_metrics_workflow,
)
from ..workflows.profiles import (
    CITATION_PROFILES,
    DEEP_RESEARCH_PROFILES,
    get_citation_profile,
    get_deep_research_profile,
)
from .adapters import resolve_adapter

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help=(
        "Deterministic sustainability research CLI for TianGong.\n\n"
        "Command groups:\n"
        "- sources: catalogue, audit, and verify data integrations.\n"
        "- research: run SDG/GRI mapping, code and paper discovery, synthesis, and tooling checks.\n"
        "- research workflow: execute curated multi-step studies.\n"
        "- research visuals: confirm AntV MCP chart server availability."
    ),
)
sources_app = typer.Typer(help=("Inspect and validate external data source integrations. Includes list, describe, audit, and" " per-source verification commands."))
app.add_typer(sources_app, name="sources")
research_app = typer.Typer(
    help=("Execute sustainability research commands such as SDG mapping, repository discovery, carbon" " intensity lookups, literature search, synthesis, and MCP tooling checks.")
)
app.add_typer(research_app, name="research")
visuals_app = typer.Typer(help="Visualization tooling, including AntV MCP chart server verification.")
research_app.add_typer(visuals_app, name="visuals")
workflow_app = typer.Typer(help="Predefined multi-step research workflows such as simple, citation-scan, and deep-report templates.")
research_app.add_typer(workflow_app, name="workflow")

_CURRENT_YEAR = datetime.now(UTC).year
_DEEP_PROFILE_CHOICES = tuple(sorted(DEEP_RESEARCH_PROFILES))
_CITATION_PROFILE_CHOICES = tuple(sorted(CITATION_PROFILES))


def _load_registry(registry_file: Optional[Path]) -> DataSourceRegistry:
    if registry_file:
        return DataSourceRegistry.from_yaml(registry_file)
    datasources_pkg = "tiangong_ai_for_sustainability.resources.datasources"
    with resources.as_file(resources.files(datasources_pkg) / "core.yaml") as resolved:
        return DataSourceRegistry.from_yaml(resolved)


def _render_descriptor(descriptor: DataSourceDescriptor) -> str:
    payload = {
        "id": descriptor.source_id,
        "name": descriptor.name,
        "category": descriptor.category,
        "priority": descriptor.priority.value,
        "description": descriptor.description,
        "protocols": list(descriptor.protocols),
        "base_urls": list(descriptor.base_urls),
        "authentication": descriptor.authentication,
        "requires_credentials": descriptor.requires_credentials,
        "status": descriptor.status.value,
        "blocked_reason": descriptor.blocked_reason,
        "capabilities": list(descriptor.capabilities),
        "tags": list(descriptor.tags),
        "notes": descriptor.notes,
        "references": list(descriptor.references),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _read_text_file(path: Path) -> str:
    if not path.is_file():
        raise typer.BadParameter(f"File '{path}' does not exist.")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pdfminer.high_level import extract_text  # type: ignore[import]
        except ImportError as exc:
            raise typer.BadParameter("PDF support requires pdfminer.six. Install it with 'uv add pdfminer.six' or provide a text file.") from exc
        return extract_text(str(path))

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise typer.BadParameter(f"Failed to decode file '{path}': {exc}") from exc


def _normalise_osdg_results(payload: Dict[str, Any], goal_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    data_candidates = []
    for key in ("classification", "classifications", "data", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            data_candidates = value
            break

    if not data_candidates and isinstance(payload.get("classification"), dict):
        data_candidates = [payload["classification"]]

    for item in data_candidates:
        if not isinstance(item, dict):
            continue
        goal_code: Optional[str] = None
        goal_title: Optional[str] = None
        score: Optional[float] = None

        goal_field = item.get("goal") or item.get("sdg") or item.get("target")
        if isinstance(goal_field, dict):
            code_val = goal_field.get("code") or goal_field.get("id") or goal_field.get("goal")
            if isinstance(code_val, (int, str)):
                goal_code = str(code_val)
            title_val = goal_field.get("title") or goal_field.get("name")
            if isinstance(title_val, str):
                goal_title = title_val
        elif isinstance(goal_field, (int, str)):
            goal_code = str(goal_field)

        score_val = item.get("score") or item.get("confidence") or item.get("probability")
        if isinstance(score_val, (int, float)):
            score = float(score_val)

        if goal_code and goal_code in goal_map:
            goal_title = goal_title or goal_map[goal_code].get("title")  # type: ignore[index]

        if goal_code:
            entries.append({"code": goal_code, "title": goal_title, "score": score, "raw": item})

    return entries


def _parse_status(status: Optional[str]) -> Optional[DataSourceStatus]:
    if status is None:
        return None
    try:
        return DataSourceStatus(status.lower())
    except ValueError:
        raise typer.BadParameter(f"Unknown status '{status}'. Expected one of: " f"{', '.join(item.value for item in DataSourceStatus)}.") from None


def _parse_prompt_variables(values: Optional[List[str]]) -> Dict[str, str]:
    variables: Dict[str, str] = {}
    if not values:
        return variables
    for entry in values:
        if "=" not in entry:
            raise typer.BadParameter(f"Prompt variable '{entry}' must use key=value format.")
        key, value = entry.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter(f"Prompt variable '{entry}' is missing a key.")
        variables[key] = value
    return variables


@app.callback(invoke_without_command=False)
def main(
    ctx: typer.Context,
    registry_file: Optional[Path] = typer.Option(
        None,
        "--registry",
        "-r",
        help="Override data source registry YAML file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    cache_dir: Optional[Path] = typer.Option(
        None,
        "--cache-dir",
        help="Override cache directory used by commands.",
        file_okay=False,
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Emit execution plans without performing actions."),
    background: bool = typer.Option(False, "--background", help="Enable background execution when supported."),
    prompt_template: Optional[str] = typer.Option(
        None,
        "--prompt-template",
        help="Default prompt template alias or path for LLM-enabled workflows.",
    ),
    prompt_language: Optional[str] = typer.Option(
        None,
        "--prompt-language",
        help="Preferred language for prompt templates (e.g. 'en', 'zh').",
    ),
    prompt_variable: Optional[List[str]] = typer.Option(
        None,
        "--prompt-variable",
        "-P",
        help="Placeholder in the form key=value to substitute inside prompt templates. Can be repeated.",
    ),
) -> None:
    """
    Configure global execution context.

    The callback stores the resolved execution context in Typer's state so child
    commands can retrieve it via :class:`typer.Context`.
    """

    try:
        registry = _load_registry(registry_file)
    except RegistryLoadError as exc:
        raise typer.Exit(code=1) from typer.BadParameter(str(exc))

    options = ExecutionOptions(
        dry_run=dry_run,
        background_tasks=background,
        prompt_template=prompt_template,
        prompt_language=prompt_language,
        prompt_variables=_parse_prompt_variables(prompt_variable),
    )
    context = ExecutionContext.build_default(
        cache_dir=cache_dir,
        options=options,
    )
    # When an allowlist has not been specified, default to all non-blocked sources.
    context.enabled_sources.update(entry.source_id for entry in registry.iter_enabled())
    state = ctx.ensure_object(dict)
    state["registry"] = registry
    state["context"] = context


def _require_registry(ctx: typer.Context) -> DataSourceRegistry:
    state = ctx.ensure_object(dict)
    registry = state.get("registry")
    if not isinstance(registry, DataSourceRegistry):
        raise typer.Exit(code=2)
    return registry


def _require_context(ctx: typer.Context) -> ExecutionContext:
    state = ctx.ensure_object(dict)
    context = state.get("context")
    if not isinstance(context, ExecutionContext):
        raise typer.Exit(code=2)
    return context


@sources_app.command("list")
def sources_list(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by lifecycle status."),
    show_blocked: bool = typer.Option(False, "--show-blocked", help="Include blocked sources in the list."),
) -> None:
    """List registered data sources with basic metadata."""

    registry = _require_registry(ctx)
    status_filter = _parse_status(status)
    entries = registry.list(status=status_filter) if status_filter else list(registry.iter_enabled(allow_blocked=show_blocked))
    if not entries:
        typer.echo("No data sources match the requested filters.")
        raise typer.Exit(code=0)

    header = f"{'ID':<22} {'Priority':<8} {'Status':<11} Description"
    typer.echo(header)
    typer.echo("-" * len(header))
    for entry in entries:
        descr = entry.description.replace("\n", " ")
        typer.echo(f"{entry.source_id:<22} {entry.priority.value:<8} {entry.status.value:<11} {descr}")


@sources_app.command("describe")
def sources_describe(
    ctx: typer.Context,
    source_id: str = typer.Argument(..., help="Identifier of the data source."),
    output_json: bool = typer.Option(False, "--json", help="Emit descriptor in JSON format."),
) -> None:
    """Show detailed metadata for a specific data source."""

    registry = _require_registry(ctx)
    descriptor = registry.get(source_id)
    if not descriptor:
        typer.echo(f"Data source '{source_id}' is not registered.", err=True)
        raise typer.Exit(code=1)

    if output_json:
        typer.echo(_render_descriptor(descriptor))
        return

    typer.echo(f"ID: {descriptor.source_id}")
    typer.echo(f"Name: {descriptor.name}")
    typer.echo(f"Category: {descriptor.category}")
    typer.echo(f"Priority: {descriptor.priority.value}")
    typer.echo(f"Status: {descriptor.status.value}")
    if descriptor.blocked_reason:
        typer.echo(f"Blocked Reason: {descriptor.blocked_reason}")
    typer.echo(f"Authentication: {descriptor.authentication}")
    typer.echo(f"Requires Credentials: {descriptor.requires_credentials}")
    typer.echo(f"Protocols: {', '.join(descriptor.protocols) or 'N/A'}")
    if descriptor.base_urls:
        for url in descriptor.base_urls:
            typer.echo(f"Base URL: {url}")
    if descriptor.capabilities:
        typer.echo(f"Capabilities: {', '.join(descriptor.capabilities)}")
    if descriptor.tags:
        typer.echo(f"Tags: {', '.join(descriptor.tags)}")
    if descriptor.references:
        typer.echo(f"References: {', '.join(descriptor.references)}")
    if descriptor.notes:
        typer.echo(f"Notes: {descriptor.notes}")


@sources_app.command("audit")
def sources_audit(
    ctx: typer.Context,
    show_blocked: bool = typer.Option(False, "--show-blocked", help="Include blocked sources in the audit results."),
    output_json: bool = typer.Option(False, "--json", help="Emit the audit report in JSON format."),
    fail_on_error: bool = typer.Option(True, "--fail-on-error/--no-fail-on-error", help="Control whether failures set a non-zero exit code."),
) -> None:
    """
    Run verification across all registered data sources and emit a summary report.
    """

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    descriptors = list(registry.iter_enabled(allow_blocked=show_blocked))
    if not descriptors:
        typer.echo("No data sources available for audit.")
        raise typer.Exit(code=0)

    records: List[Dict[str, Any]] = []
    failures = 0
    for descriptor in descriptors:
        enabled = context.is_enabled(descriptor.source_id)
        record: Dict[str, Any] = {
            "id": descriptor.source_id,
            "name": descriptor.name,
            "priority": descriptor.priority.value,
            "registry_status": descriptor.status.value,
            "requires_credentials": descriptor.requires_credentials,
            "enabled": enabled,
            "success": False,
            "message": "",
            "details": None,
        }

        if descriptor.status == DataSourceStatus.BLOCKED:
            record["message"] = f"Blocked: {descriptor.blocked_reason or 'No blocked reason provided.'}"
            record["details"] = {"reason": "blocked"}
        elif descriptor.requires_credentials and not enabled:
            record["message"] = "Requires credentials; configure secrets and enable the source."
            record["details"] = {"reason": "credentials-missing"}
        else:
            adapter = resolve_adapter(descriptor.source_id, context)
            try:
                verification = services.verify_source(descriptor.source_id, adapter)
            except AdapterError as exc:
                record["message"] = f"Adapter error: {exc}"
                record["details"] = {"reason": "adapter-error"}
            else:
                record["success"] = verification.success
                record["message"] = verification.message
                if verification.details is not None:
                    record["details"] = dict(verification.details)

        if not record["success"]:
            failures += 1
        records.append(record)

    if output_json:
        typer.echo(json.dumps({"results": records}, ensure_ascii=False, indent=2))
    else:
        header = f"{'ID':<22} {'Registry':<9} {'Enabled':<7} {'Result':<7} Message"
        typer.echo(header)
        typer.echo("-" * len(header))
        for record in records:
            message = str(record["message"]).replace("\n", " ").strip()
            enabled_str = "yes" if record["enabled"] else "no"
            result_str = "pass" if record["success"] else "fail"
            typer.echo(f"{record['id']:<22} {record['registry_status']:<9} {enabled_str:<7} {result_str:<7} {message}")
        passed = len(records) - failures
        typer.echo(f"Audit complete: {len(records)} source(s), {passed} passed, {failures} failed.")

    if failures and fail_on_error:
        raise typer.Exit(code=1)


@sources_app.command("verify")
def sources_verify(
    ctx: typer.Context,
    source_id: str = typer.Argument(..., help="Identifier of the data source."),
) -> None:
    """
    Run lightweight verification against a data source.

    Phase 0 uses stubbed checks that can be extended with real connectivity
    tests once adapters are implemented.
    """

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    descriptor = registry.get(source_id)
    if not descriptor:
        typer.echo(f"Data source '{source_id}' is not registered.", err=True)
        raise typer.Exit(code=1)

    if descriptor.status == DataSourceStatus.BLOCKED:
        typer.echo(f"Source '{source_id}' is blocked: {descriptor.blocked_reason}")
        raise typer.Exit(code=1)

    if descriptor.requires_credentials and source_id not in context.enabled_sources:
        typer.echo(
            f"Source '{source_id}' requires credentials. Provide API keys in .secrets or enable explicitly.",
            err=True,
        )
        raise typer.Exit(code=1)

    services = ResearchServices(registry=registry, context=context)
    adapter = resolve_adapter(source_id, context)
    try:
        result = services.verify_source(source_id, adapter)
    except AdapterError as exc:
        typer.echo(f"Verification failed: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(result.message)
    if result.details:
        typer.echo(f"Details: {json.dumps(result.details, ensure_ascii=False)}")
    if not result.success:
        raise typer.Exit(code=1)


@research_app.command("map-sdg")
def research_map_sdg(
    ctx: typer.Context,
    file_path: Path = typer.Argument(..., exists=True, resolve_path=True, help="Path to a text or PDF file."),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Optional language hint for the classifier."),
    output_json: bool = typer.Option(False, "--json", help="Emit raw JSON results."),
) -> None:
    """Classify a document and map its content to SDG goals via OSDG."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    text = _read_text_file(file_path).strip()
    if not text:
        typer.echo("Input file is empty after stripping whitespace.", err=True)
        raise typer.Exit(code=1)

    try:
        payload = services.classify_text_with_osdg(text, language=language)
    except AdapterError as exc:
        typer.echo(f"Failed to classify text with OSDG API: {exc}", err=True)
        raise typer.Exit(code=1)

    if output_json:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if isinstance(payload, dict) and payload.get("note"):
        typer.echo(payload["note"])
        return

    if not isinstance(payload, dict):
        typer.echo("Unexpected response from OSDG API.")
        typer.echo(str(payload))
        raise typer.Exit(code=1)

    goal_map = services.sdg_goal_map()
    matches = _normalise_osdg_results(payload, goal_map)

    if not matches:
        typer.echo("No SDG matches were returned by the OSDG API.")
        typer.echo("Raw response:")
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        raise typer.Exit(code=1)

    typer.echo(f"OSDG returned {len(matches)} SDG match(es):")
    for entry in matches:
        code = entry.get("code")
        title = entry.get("title") or goal_map.get(code, {}).get("title") if code else None
        score = entry.get("score")
        score_str = f" (score {score:.2f})" if isinstance(score, float) else ""
        typer.echo(f"- SDG {code}: {title}{score_str}")


@research_app.command("find-code")
def research_find_code(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="GitHub topic to search for (e.g. 'life-cycle-assessment')."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=100, help="Number of repositories to return."),
    output_json: bool = typer.Option(False, "--json", help="Emit raw JSON results."),
) -> None:
    """Discover code repositories linked to sustainability topics via GitHub Topics."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    if context.options.dry_run:
        typer.echo(f"Dry-run: would search GitHub for topic '{topic}' (limit={limit}).")
        return

    client = services.github_topics_client()
    try:
        payload = client.search_repositories(topic, per_page=limit)
    except AdapterError as exc:
        typer.echo(f"GitHub Topics search failed: {exc}", err=True)
        raise typer.Exit(code=1)

    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        typer.echo("Unexpected response from GitHub API.", err=True)
        raise typer.Exit(code=1)

    if output_json:
        typer.echo(json.dumps(items, ensure_ascii=False, indent=2))
        return

    if not items:
        typer.echo("No repositories matched the requested topic.")
        return

    total = payload.get("total_count")
    if isinstance(total, int):
        typer.echo(f"GitHub returned {total} matching repositories (showing up to {len(items)}).")

    for repo in items:
        if not isinstance(repo, dict):
            continue
        name = repo.get("full_name", "unknown")
        stars = repo.get("stargazers_count")
        url = repo.get("html_url", "")
        description = repo.get("description")
        stars_str = f" ⭐{stars}" if isinstance(stars, int) else ""
        line = f"- {name}{stars_str}"
        if url:
            line += f" → {url}"
        typer.echo(line)
        if isinstance(description, str) and description.strip():
            typer.echo(f"  {description.strip()}")


@visuals_app.command("verify")
def research_visuals_verify(ctx: typer.Context) -> None:
    """Verify connectivity to the AntV MCP chart server."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    result = services.verify_chart_mcp()
    typer.echo(result.message)
    if result.details:
        typer.echo(f"Details: {json.dumps(result.details, ensure_ascii=False)}")
    if not result.success:
        typer.echo(
            "Hint: install Node.js and run `npx -y @antv/mcp-server-chart --transport streamable` " "(default endpoint http://127.0.0.1:1122/mcp).",
            err=True,
        )
        raise typer.Exit(code=1)


@workflow_app.command("simple")
def research_workflow_simple(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Research topic or query phrase."),
    report_output: Path = typer.Option(Path("reports") / "snapshot.md", "--report-output", help="Path for the generated Markdown report."),
    chart_output: Path = typer.Option(
        Path(".cache") / "tiangong" / "visuals" / "snapshot.png",
        "--chart-output",
        help="Path for the generated chart PNG.",
    ),
    github_limit: int = typer.Option(5, help="Maximum number of GitHub repositories to include."),
    paper_limit: int = typer.Option(5, help="Maximum number of papers to include."),
    carbon_location: str = typer.Option("CAISO_NORTH", help="Grid intensity location identifier."),
) -> None:
    """Run the simple sustainability workflow and emit a report plus chart."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    artifacts = run_simple_workflow(
        services,
        topic=topic,
        report_path=report_output,
        chart_path=chart_output,
        github_limit=github_limit,
        paper_limit=paper_limit,
        carbon_location=carbon_location,
    )

    if context.options.dry_run:
        typer.echo("Dry-run: generated execution plan; no files were written.")
        plan = artifacts.carbon_snapshot if isinstance(artifacts.carbon_snapshot, dict) else {}
        steps = plan.get("planned_steps") if isinstance(plan, dict) else None
        if steps:
            typer.echo("Planned steps:")
            for item in steps:
                typer.echo(f"- {item}")
        typer.echo(f"Planned report location: {report_output}")
        if chart_output:
            typer.echo(f"Planned chart location: {chart_output}")
        return

    typer.echo(f"Report written to {artifacts.report_path}")
    if artifacts.chart_path:
        typer.echo(f"Chart saved to {artifacts.chart_path}")
    else:
        typer.echo("Chart generation skipped or failed; see report for details.")


@workflow_app.command("deep-report")
def research_workflow_deep_report(
    ctx: typer.Context,
    profile: str = typer.Option(
        "lca",
        "--profile",
        "-p",
        case_sensitive=False,
        help=f"Domain profile slug. Available: {', '.join(_DEEP_PROFILE_CHOICES)}.",
        show_default=True,
    ),
    output_dir: Path = typer.Option(Path("output"), "--output-dir", help="Directory to store all generated artefacts."),
    years: int = typer.Option(5, "--years", help="Number of years to include in the lookback window."),
    max_records: int = typer.Option(200, "--max-records", help="Maximum number of OpenAlex papers to ingest."),
    keyword: Optional[List[str]] = typer.Option(
        None,
        "--keyword",
        "-k",
        help="Additional keyword filters (can be repeated).",
    ),
    skip_deep_research: bool = typer.Option(
        False,
        "--skip-deep-research",
        help="Disable the OpenAI Deep Research step and rely on deterministic outputs only.",
    ),
    deep_prompt: Optional[str] = typer.Option(
        None,
        "--deep-prompt",
        help="Override the default Deep Research question.",
    ),
    deep_instructions: Optional[str] = typer.Option(
        None,
        "--deep-instructions",
        help="Override the system instructions supplied to Deep Research.",
    ),
    prompt_template: Optional[str] = typer.Option(
        None,
        "--prompt-template",
        help="Prompt template alias or path applied to Deep Research instructions.",
    ),
    prompt_language: Optional[str] = typer.Option(
        None,
        "--prompt-language",
        help="Language hint for prompt template selection (e.g. 'en', 'zh').",
    ),
    prompt_variable: Optional[List[str]] = typer.Option(
        None,
        "--prompt-variable",
        "-P",
        help="Template placeholder assignment in key=value form. Can be repeated.",
    ),
) -> None:
    """Run the deep research workflow for the selected domain profile."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    try:
        profile_cfg = get_deep_research_profile(profile.lower())
    except KeyError as exc:
        choices = ", ".join(_DEEP_PROFILE_CHOICES)
        raise typer.BadParameter(f"{exc}. Available profiles: {choices}.") from exc

    resolved_output_dir = output_dir
    if output_dir == Path("output"):
        resolved_output_dir = output_dir / profile_cfg.slug
    resolved_output_dir = resolved_output_dir.resolve()

    if prompt_template:
        context.options.prompt_template = prompt_template
    if prompt_language:
        context.options.prompt_language = prompt_language
    if prompt_variable:
        merged = dict(context.options.prompt_variables)
        merged.update(_parse_prompt_variables(prompt_variable))
        context.options.prompt_variables = merged

    artifacts = run_deep_research_template(
        services,
        profile=profile_cfg,
        output_dir=resolved_output_dir,
        years=years,
        max_records=max_records,
        keywords=keyword,
        deep_research=not skip_deep_research,
        deep_research_prompt=deep_prompt,
        deep_research_instructions=deep_instructions,
        prompt_template=prompt_template,
        prompt_language=prompt_language,
    )

    if context.options.dry_run:
        typer.echo("Dry-run: generated execution plan; no artefacts were created.")
        typer.echo(f"Planned profile: {profile_cfg.display_name} ({profile_cfg.slug})")
        typer.echo(f"Planned output directory: {resolved_output_dir}")
        typer.echo("Planned steps:")
        steps = [
            f"Run citation scan for profile '{profile_cfg.slug}'.",
            "Invoke Deep Research for synthesis." if not skip_deep_research else "Skip Deep Research synthesis (disabled via flag).",
            "Produce Markdown report and optional exports.",
        ]
        for step in steps:
            typer.echo(f"- {step}")
        return

    typer.echo(f"Profile: {artifacts.profile_display_name or profile_cfg.display_name} ({artifacts.profile_slug or profile_cfg.slug})")
    typer.echo(f"Final report written to {artifacts.final_report_path}")
    typer.echo(f"Citation scan stored at {artifacts.citation_report_path}")
    if artifacts.chart_path:
        typer.echo(f"Chart saved to {artifacts.chart_path}")
    if artifacts.raw_data_path:
        typer.echo(f"Citation dataset cached at {artifacts.raw_data_path}")
    if artifacts.deep_research_response_path:
        typer.echo(f"Deep Research response saved to {artifacts.deep_research_response_path}")
    elif artifacts.deep_research_summary and artifacts.deep_research_summary.startswith("Deep Research unavailable"):
        typer.echo(artifacts.deep_research_summary)
    for path in artifacts.doc_variants:
        typer.echo(f"Additional export created: {path}")
    for note in artifacts.conversion_warnings:
        typer.echo(f"Notice: {note}")
    if artifacts.prompt_template_path:
        typer.echo(f"Prompt template ({artifacts.prompt_template_identifier}) -> {artifacts.prompt_template_path}")
    elif prompt_template or context.options.prompt_template:
        typer.echo(f"Prompt template alias: {prompt_template or context.options.prompt_template}")


@workflow_app.command("citation-scan")
def research_workflow_citation_scan(
    ctx: typer.Context,
    profile: str = typer.Option(
        "lca",
        "--profile",
        "-p",
        case_sensitive=False,
        help=f"Domain profile slug. Available: {', '.join(_CITATION_PROFILE_CHOICES)}.",
        show_default=True,
    ),
    report_output: Optional[Path] = typer.Option(None, "--report-output", help="Markdown report destination."),
    chart_output: Optional[Path] = typer.Option(None, "--chart-output", help="Path for the generated trend chart PNG."),
    raw_output: Optional[Path] = typer.Option(None, "--raw-output", help="Path to persist the raw dataset as JSON."),
    years: int = typer.Option(5, "--years", help="Number of years to include in the lookback window."),
    max_records: int = typer.Option(300, "--max-records", help="Maximum number of papers to ingest from OpenAlex."),
    keyword: Optional[List[str]] = typer.Option(
        None,
        "--keyword",
        "-k",
        help="Additional keyword filters (can be repeated).",
    ),
) -> None:
    """Run the deterministic citation workflow for the selected profile."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    try:
        profile_cfg = get_citation_profile(profile.lower())
    except KeyError as exc:
        choices = ", ".join(_CITATION_PROFILE_CHOICES)
        raise typer.BadParameter(f"{exc}. Available profiles: {choices}.") from exc

    report_path = (report_output or Path("reports") / f"{profile_cfg.slug}_citations.md").resolve()
    chart_path = (chart_output or Path(".cache") / "tiangong" / "visuals" / f"{profile_cfg.slug}_citations.png").resolve()
    raw_path = (raw_output or Path(".cache") / "tiangong" / "data" / f"{profile_cfg.slug}_citations.json").resolve()

    artifacts = run_citation_template_workflow(
        services,
        profile=profile_cfg,
        report_path=report_path,
        chart_path=chart_path,
        raw_data_path=raw_path,
        years=years,
        keyword_overrides=keyword,
        max_records=max_records,
    )

    if context.options.dry_run:
        typer.echo("Dry-run: generated execution plan; no files were written.")
        typer.echo(f"Planned profile: {profile_cfg.display_name} ({profile_cfg.slug})")
        typer.echo(f"Planned report location: {report_path}")
        typer.echo(f"Planned chart location: {chart_path}")
        typer.echo(f"Planned dataset location: {raw_path}")
        return

    typer.echo(f"Profile: {profile_cfg.display_name} ({profile_cfg.slug})")
    typer.echo(f"Report written to {artifacts.report_path}")
    if artifacts.chart_path:
        typer.echo(f"Chart saved to {artifacts.chart_path}")
    else:
        typer.echo("Chart generation skipped or failed; review the report for details.")
    if artifacts.raw_data_path:
        typer.echo(f"Raw dataset cached at {artifacts.raw_data_path}")


@research_app.command("get-carbon-intensity")
def research_get_carbon_intensity(
    ctx: typer.Context,
    location: str = typer.Argument(..., help="Provider-specific location identifier, e.g. CAISO_NORTH."),
    provider: str = typer.Option("WattTime", "--provider", "-p", help="grid-intensity provider to use."),
    output_json: bool = typer.Option(False, "--json", help="Emit raw JSON instead of a formatted message."),
) -> None:
    """Fetch carbon intensity metrics via the grid-intensity CLI."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    try:
        payload = services.get_carbon_intensity(location=location, provider=provider)
    except AdapterError as exc:
        typer.echo(f"Failed to retrieve carbon intensity: {exc}", err=True)
        raise typer.Exit(code=1)

    if output_json:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    intensity = payload.get("carbon_intensity") or payload.get("co2e")
    units = payload.get("units") or payload.get("unit")
    summary = f"Provider {payload.get('provider', provider)} reports carbon intensity for {payload.get('location', location)}"
    if intensity is not None:
        summary += f": {intensity}"
        if units:
            summary += f" {units}"
    typer.echo(summary)
    if "datetime" in payload:
        typer.echo(f"Timestamp: {payload['datetime']}")


@research_app.command("metrics-trending")
def research_metrics_trending(
    ctx: typer.Context,
    start_year: int = typer.Option(2020, "--start-year", min=1900, max=_CURRENT_YEAR, help="Lower bound (inclusive) for publication years."),
    end_year: Optional[int] = typer.Option(None, "--end-year", help="Upper bound (inclusive) for publication years. Defaults to the current year."),
    max_records: int = typer.Option(120, "--max-records", "-n", min=10, max=400, help="Safety cap for OpenAlex works fetched per metric."),
    output_path: Optional[Path] = typer.Option(None, "--output", "-o", resolve_path=True, help="Optional JSON report destination."),
) -> None:
    """Summarise scarcity, footprint, and biodiversity metrics via OpenAlex."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    resolved_output = output_path.resolve() if output_path else None

    try:
        artifacts = run_trending_metrics_workflow(
            services,
            start_year=start_year,
            end_year=end_year,
            max_records_per_metric=max_records,
            output_path=resolved_output,
        )
    except (AdapterError, APIError) as exc:
        typer.echo(f"Failed to compute trending metrics: {exc}", err=True)
        raise typer.Exit(code=1)

    if artifacts.plan:
        typer.echo("Dry-run plan:")
        for step in artifacts.plan:
            typer.echo(f"- {step}")
        return

    if not artifacts.metrics:
        typer.echo("No metrics available. Ensure OpenAlex is enabled and reachable.", err=True)
        raise typer.Exit(code=1)

    for summary in artifacts.metrics:
        typer.echo(f"{summary.label}:")
        typer.echo(f"  Works analysed: {summary.total_works} | Total citations: {summary.total_citations}")
        if summary.citation_trend:
            trend_str = ", ".join(f"{year}:{citations}" for year, citations in summary.citation_trend.items())
            typer.echo(f"  Citations by year: {trend_str}")
        if summary.top_works:
            typer.echo("  Top works:")
            for entry in summary.top_works:
                title = entry.get("title") or "Untitled"
                year = entry.get("year")
                cites = entry.get("cited_by_count")
                doi = entry.get("doi")
                details = f"{title} ({year}) — {cites} citations"
                if doi:
                    details += f" | DOI {doi}"
                typer.echo(f"    - {details}")
        if summary.top_concepts:
            concept_str = ", ".join(f"{concept['name']} ({concept['weighted_citations']})" for concept in summary.top_concepts)
            typer.echo(f"  High-signal concepts: {concept_str}")
        typer.echo("")

    if artifacts.output_path:
        typer.echo(f"Metrics written to {artifacts.output_path}")


@research_app.command("synthesize")
def research_synthesize(
    ctx: typer.Context,
    question: str = typer.Argument(..., help="Primary research question to explore."),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Optional topic override for repository/paper discovery."),
    sdg_text: Optional[Path] = typer.Option(None, "--sdg-text", resolve_path=True, help="Path to a text or PDF file used for SDG alignment."),
    repo_limit: int = typer.Option(5, "--repo-limit", help="Maximum number of repositories to include."),
    paper_limit: int = typer.Option(5, "--paper-limit", help="Maximum number of papers to include."),
    carbon_location: Optional[str] = typer.Option(None, "--carbon-location", help="Grid intensity location identifier."),
    output: Path = typer.Option(Path("reports") / "synthesis.md", "--output", "-o", resolve_path=True, help="Destination path for the Markdown synthesis report."),
    instructions: Optional[str] = typer.Option(None, "--instructions", help="Override LLM instructions directly (bypasses templates)."),
    skip_llm: bool = typer.Option(False, "--skip-llm", help="Skip the LLM synthesis step and emit deterministic findings only."),
    prompt_template: Optional[str] = typer.Option(None, "--prompt-template", help="Prompt template alias or path applied to LLM instructions."),
    prompt_language: Optional[str] = typer.Option(None, "--prompt-language", help="Language hint for prompt template selection."),
    prompt_variable: Optional[List[str]] = typer.Option(None, "--prompt-variable", "-P", help="Template placeholder assignment in key=value form. Can be repeated."),
) -> None:
    """Run an orchestration workflow that combines deterministic evidence and LLM synthesis."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    if prompt_template:
        context.options.prompt_template = prompt_template
    if prompt_language:
        context.options.prompt_language = prompt_language
    if prompt_variable:
        merged = dict(context.options.prompt_variables)
        merged.update(_parse_prompt_variables(prompt_variable))
        context.options.prompt_variables = merged

    sdg_context_text: Optional[str] = None
    if sdg_text:
        sdg_context_text = _read_text_file(sdg_text)

    artifacts = run_synthesis_workflow(
        services,
        question=question,
        report_path=output,
        topic=topic,
        sdg_context=sdg_context_text,
        repository_limit=repo_limit,
        paper_limit=paper_limit,
        carbon_location=carbon_location,
        prompt_template=prompt_template,
        prompt_language=prompt_language,
        instructions_override=instructions,
        skip_llm=skip_llm,
    )

    if context.options.dry_run and artifacts.plan:
        typer.echo("Dry-run: generated execution plan; no artefacts were created.")
        for step in artifacts.plan:
            typer.echo(f"- {step}")
        typer.echo(f"Planned report location: {output}")
        return

    typer.echo(f"Synthesis report written to {artifacts.report_path}")
    if artifacts.llm_response_path:
        typer.echo(f"LLM response saved to {artifacts.llm_response_path}")
    elif artifacts.llm_summary and artifacts.llm_summary.startswith("Deep Research unavailable"):
        typer.echo(artifacts.llm_summary)
    elif skip_llm:
        typer.echo("LLM synthesis skipped; report contains deterministic findings only.")

    if artifacts.llm_summary and not skip_llm:
        typer.echo("\nLLM synthesis summary:")
        typer.echo(artifacts.llm_summary)

    if artifacts.prompt_template_path:
        typer.echo(f"Prompt template ({artifacts.prompt_template_identifier}) -> {artifacts.prompt_template_path}")
    elif prompt_template or context.options.prompt_template:
        typer.echo(f"Prompt template alias: {prompt_template or context.options.prompt_template}")


@research_app.command("find-papers")
def research_find_papers(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query or keyword."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=50, help="Maximum number of papers per source."),
    include_openalex: bool = typer.Option(True, "--openalex/--no-openalex", help="Toggle OpenAlex enrichment."),
    include_arxiv: bool = typer.Option(False, "--arxiv/--no-arxiv", help="Toggle local arXiv dump enrichment (TIANGONG_ARXIV_INDEX or cache)."),
    include_scopus: bool = typer.Option(False, "--scopus/--no-scopus", help="Toggle Scopus export enrichment (TIANGONG_SCOPUS_INDEX or cache)."),
    citation_graph: bool = typer.Option(False, "--citation-graph/--no-citation-graph", help="Emit citation edges derived from OpenAlex references."),
    output_json: bool = typer.Option(False, "--json", help="Emit aggregated results as JSON."),
    sdg_text: Optional[Path] = typer.Option(None, "--sdg-text", resolve_path=True, help="Optional text/PDF file used to seed SDG alignment."),
) -> None:
    """Aggregate literature evidence across Semantic Scholar and (optionally) OpenAlex."""

    registry = _require_registry(ctx)
    context = _require_context(ctx)
    services = ResearchServices(registry=registry, context=context)

    sdg_context_text: Optional[str] = None
    if sdg_text:
        sdg_context_text = _read_text_file(sdg_text)

    artifacts = run_paper_search(
        services,
        query=query,
        sdg_context=sdg_context_text,
        limit=limit,
        include_openalex=include_openalex,
        include_arxiv=include_arxiv,
        include_scopus=include_scopus,
        include_citations=citation_graph,
    )

    if context.options.dry_run and artifacts.plan:
        typer.echo("Dry-run: generated execution plan; no searches executed.")
        for step in artifacts.plan:
            typer.echo(f"- {step}")
        return

    payload = {
        "query": artifacts.query,
        "sdg_matches": artifacts.sdg_matches,
        "semantic_scholar": artifacts.semantic_scholar,
        "arxiv": artifacts.arxiv,
        "scopus": artifacts.scopus,
        "openalex": artifacts.openalex,
        "notes": artifacts.notes,
    }
    if artifacts.citation_edges is not None:
        payload["citation_edges"] = artifacts.citation_edges

    if output_json:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    typer.echo(f"SDG alignment suggestions ({len(artifacts.sdg_matches)}):")
    if artifacts.sdg_matches:
        for match in artifacts.sdg_matches:
            code = match.get("code", "?")
            title = match.get("title", "Unknown goal")
            score = match.get("score", 0)
            typer.echo(f"- SDG {code} — {title} (score {score})")
    else:
        typer.echo("(no suggested SDG matches)")

    typer.echo("")
    typer.echo(f"Semantic Scholar results ({len(artifacts.semantic_scholar)}):")
    for paper in artifacts.semantic_scholar:
        title = paper.get("title", "Untitled")
        year = paper.get("year") or "?"
        authors = ", ".join(paper.get("authors", [])) or "N/A"
        typer.echo(f"- {title} ({year}) — {authors}")
        url = paper.get("url")
        if url:
            typer.echo(f"  {url}")

    if artifacts.openalex:
        typer.echo("")
        typer.echo(f"OpenAlex results ({len(artifacts.openalex)}):")
        for work in artifacts.openalex:
            title = work.get("title", "Untitled")
            year = work.get("year") or "?"
            cites = work.get("cited_by_count", "?")
            typer.echo(f"- {title} ({year}) — cited by {cites} works")
            doi = work.get("doi")
            if doi:
                typer.echo(f"  DOI: {doi}")

    if artifacts.citation_edges is not None:
        typer.echo("")
        typer.echo(f"Citation edges recorded: {len(artifacts.citation_edges)}")

    if artifacts.arxiv:
        typer.echo("")
        typer.echo(f"arXiv local results ({len(artifacts.arxiv)}):")
        for record in artifacts.arxiv:
            title = record.get("title", "Untitled")
            year = record.get("year") or "?"
            typer.echo(f"- {title} ({year})")
            summary = record.get("summary")
            if summary:
                typer.echo(f"  Summary: {summary[:160]}{'…' if len(summary) > 160 else ''}")

    if artifacts.scopus:
        typer.echo("")
        typer.echo(f"Scopus results ({len(artifacts.scopus)}):")
        for record in artifacts.scopus:
            title = record.get("title", "Untitled")
            year = record.get("year") or "?"
            cites = record.get("cited_by_count", "?")
            typer.echo(f"- {title} ({year}) — cited by {cites}")
            doi = record.get("doi")
            if doi:
                typer.echo(f"  DOI: {doi}")

    if artifacts.notes:
        typer.echo("")
        typer.echo("Notes:")
        for note in artifacts.notes:
            typer.echo(f"- {note}")


if __name__ == "__main__":  # pragma: no cover
    app()
