"""
Research service façade coordinating registries, adapters, and execution context.

The service layer keeps orchestration logic reusable for both CLI commands and
Codex-driven automation flows. Over time this module will grow to include
pipeline execution helpers (LLM prompting, indexing, graph construction), but we
start with lightweight registry-aware utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..adapters import AdapterError, DataSourceAdapter, VerificationResult
from ..adapters.environment import GridIntensityCLIAdapter
from ..core import DataSourceDescriptor, DataSourceRegistry, DataSourceStatus, ExecutionContext


@dataclass(slots=True)
class ResearchServices:
    """High-level façade used by CLI commands and automations."""

    registry: DataSourceRegistry
    context: ExecutionContext

    def list_enabled_sources(self) -> list[DataSourceDescriptor]:
        """Return descriptors for sources enabled in the execution context."""

        entries = []
        for descriptor in self.registry.iter_enabled(allow_blocked=False):
            if self.context.is_enabled(descriptor.source_id):
                entries.append(descriptor)
        return entries

    def resolve_source(self, source_id: str) -> DataSourceDescriptor:
        """Fetch a descriptor or raise a descriptive error."""

        descriptor = self.registry.get(source_id)
        if not descriptor:
            raise AdapterError(f"Data source '{source_id}' is not registered.")
        if not self.context.is_enabled(source_id):
            raise AdapterError(f"Data source '{source_id}' is disabled in the current execution context.")
        return descriptor

    def verify_source(self, source_id: str, adapter: Optional[DataSourceAdapter] = None) -> VerificationResult:
        """
        Run verification for a source.

        Parameters
        ----------
        source_id:
            Identifier of the data source.
        adapter:
            Optional adapter overriding automatic lookup. When ``None`` the
            method performs registry-level checks only.
        """

        descriptor = self.registry.get(source_id)
        if not descriptor:
            raise AdapterError(f"Data source '{source_id}' is not registered.")

        if descriptor.status == DataSourceStatus.BLOCKED:
            return VerificationResult(
                success=False,
                message=f"Source '{source_id}' is blocked: {descriptor.blocked_reason}",
            )

        if adapter:
            return adapter.verify()

        return VerificationResult(
            success=True,
            message=f"Source '{source_id}' is registered with priority {descriptor.priority.value} (metadata only).",
            details={"status": descriptor.status.value},
        )

    def get_carbon_intensity(self, location: str, provider: str = "WattTime") -> Dict[str, Any]:
        """
        Query the grid-intensity CLI for carbon intensity metrics.

        Respects the execution context's dry-run option by emitting a plan
        instead of invoking the CLI.
        """

        adapter = GridIntensityCLIAdapter()
        if not self.context.is_enabled(adapter.source_id):
            raise AdapterError(f"Data source '{adapter.source_id}' is disabled in the current execution context.")

        if self.context.options.dry_run:
            return {
                "provider": provider,
                "location": location,
                "note": "Dry-run mode enabled; grid-intensity CLI was not executed.",
            }

        result = adapter.query(location=location, provider=provider)
        result.setdefault("provider", provider)
        result.setdefault("location", location)
        return result
