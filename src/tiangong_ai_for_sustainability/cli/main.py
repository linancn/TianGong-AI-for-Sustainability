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
from typing import Optional

import typer

from ..core import (
    DataSourceDescriptor,
    DataSourcePriority,
    DataSourceRegistry,
    DataSourceStatus,
    ExecutionContext,
    ExecutionOptions,
    RegistryLoadError,
)

app = typer.Typer(no_args_is_help=True, add_completion=False, help="TianGong sustainability research CLI.")
sources_app = typer.Typer(help="Inspect and validate external data source integrations.")
app.add_typer(sources_app, name="sources")


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


def _parse_status(status: Optional[str]) -> Optional[DataSourceStatus]:
    if status is None:
        return None
    try:
        return DataSourceStatus(status.lower())
    except ValueError:
        raise typer.BadParameter(f"Unknown status '{status}'. Expected one of: "
                                 f"{', '.join(item.value for item in DataSourceStatus)}.") from None


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

    typer.echo(f"Source '{source_id}' is registered with priority {descriptor.priority.value} and status {descriptor.status.value}.")
    typer.echo(
        "Detailed connectivity tests are not yet implemented. This command currently validates registry metadata only."
    )


if __name__ == "__main__":  # pragma: no cover
    app()
