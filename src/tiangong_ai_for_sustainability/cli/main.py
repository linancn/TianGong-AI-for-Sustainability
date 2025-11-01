"""
Primary Typer application wiring for the sustainability research CLI.

Phase 0 focuses on surfacing data source catalogue commands so Codex and human
operators can quickly assess which integrations are available before invoking
heavier workflows.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from ..adapters import AdapterError, DataSourceAdapter, ChartMCPAdapter
from ..adapters.api import (
    GitHubTopicsAdapter,
    GitHubTopicsClient,
    OSDGAdapter,
    OSDGClient,
    SemanticScholarAdapter,
    SemanticScholarClient,
    UNSDGAdapter,
)
from ..adapters.environment import GridIntensityCLIAdapter
from ..core import DataSourceDescriptor, DataSourceRegistry, DataSourceStatus, ExecutionContext, ExecutionOptions, RegistryLoadError
from ..services import ResearchServices
from ..workflows import run_simple_workflow

app = typer.Typer(no_args_is_help=True, add_completion=False, help="TianGong sustainability research CLI.")
sources_app = typer.Typer(help="Inspect and validate external data source integrations.")
app.add_typer(sources_app, name="sources")
research_app = typer.Typer(help="Execute research workflows.")
app.add_typer(research_app, name="research")
visuals_app = typer.Typer(help="Visualization tooling")
research_app.add_typer(visuals_app, name="visuals")
workflow_app = typer.Typer(help="Predefined multi-step research workflows")
research_app.add_typer(workflow_app, name="workflow")


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

    context = ExecutionContext.build_default(
        cache_dir=cache_dir,
        options=ExecutionOptions(dry_run=dry_run, background_tasks=background),
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


def _resolve_adapter(source_id: str, context: ExecutionContext) -> Optional[DataSourceAdapter]:
    secrets = context.secrets.data

    semantic_key: Optional[str] = None
    semantic_section = secrets.get("semantic_scholar")
    if isinstance(semantic_section, dict):
        value = semantic_section.get("api_key")
        if isinstance(value, str) and value:
            semantic_key = value

    github_token: Optional[str] = None
    github_section = secrets.get("github")
    if isinstance(github_section, dict):
        value = github_section.get("token")
        if isinstance(value, str) and value:
            github_token = value

    osdg_token: Optional[str] = None
    osdg_section = secrets.get("osdg")
    if isinstance(osdg_section, dict):
        value = osdg_section.get("api_token")
        if isinstance(value, str) and value:
            osdg_token = value

    adapters = (
        GridIntensityCLIAdapter(),
        UNSDGAdapter(),
        SemanticScholarAdapter(client=SemanticScholarClient(api_key=semantic_key)),
        GitHubTopicsAdapter(client=GitHubTopicsClient(token=github_token)),
        OSDGAdapter(client=OSDGClient(api_token=osdg_token)),
        ChartMCPAdapter(),
    )
    for adapter in adapters:
        if source_id == adapter.source_id:
            return adapter
    return None


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
    adapter = _resolve_adapter(source_id, context)
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
            "Hint: install Node.js and run `npx -y @antv/mcp-server-chart --transport streamable` "
            "(default endpoint http://127.0.0.1:1122/mcp).",
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

    typer.echo(f"Report written to {artifacts.report_path}")
    if artifacts.chart_path:
        typer.echo(f"Chart saved to {artifacts.chart_path}")
    else:
        typer.echo("Chart generation skipped or failed; see report for details.")


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


if __name__ == "__main__":  # pragma: no cover
    app()
