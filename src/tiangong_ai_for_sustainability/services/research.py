"""
Research service façade coordinating registries, adapters, and execution context.

The service layer keeps orchestration logic reusable for both CLI commands and
Codex-driven automation flows. Over time this module will grow to include
pipeline execution helpers (LLM prompting, indexing, graph construction), but we
start with lightweight registry-aware utilities.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..adapters import AdapterError, DataSourceAdapter, VerificationResult, ChartMCPAdapter
from ..adapters.api import GitHubTopicsClient, OSDGClient, SemanticScholarClient, UNSDGClient
from ..adapters.environment import GridIntensityCLIAdapter
from ..core import DataSourceDescriptor, DataSourceRegistry, DataSourceStatus, ExecutionContext


@dataclass(slots=True)
class ResearchServices:
    """High-level façade used by CLI commands and automations."""

    registry: DataSourceRegistry
    context: ExecutionContext
    _un_sdg_client: Optional[UNSDGClient] = field(default=None, init=False, repr=False)
    _semantic_scholar_client: Optional[SemanticScholarClient] = field(default=None, init=False, repr=False)
    _github_topics_client: Optional[GitHubTopicsClient] = field(default=None, init=False, repr=False)
    _osdg_client: Optional[OSDGClient] = field(default=None, init=False, repr=False)
    _sdg_goal_cache: Optional[Dict[str, Dict[str, Any]]] = field(default=None, init=False, repr=False)

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

    # -- Client factories -------------------------------------------------

    def _get_secret(self, section: str, key: str) -> Optional[str]:
        section_data = self.context.secrets.data.get(section)
        if isinstance(section_data, dict):
            value = section_data.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def un_sdg_client(self) -> UNSDGClient:
        if self._un_sdg_client is None:
            self._un_sdg_client = UNSDGClient()
        return self._un_sdg_client

    def semantic_scholar_client(self) -> SemanticScholarClient:
        if self._semantic_scholar_client is None:
            api_key = self._get_secret("semantic_scholar", "api_key")
            self._semantic_scholar_client = SemanticScholarClient(api_key=api_key)
        return self._semantic_scholar_client

    def github_topics_client(self) -> GitHubTopicsClient:
        if self._github_topics_client is None:
            token = self._get_secret("github", "token")
            self._github_topics_client = GitHubTopicsClient(token=token)
        return self._github_topics_client

    def osdg_client(self) -> OSDGClient:
        if self._osdg_client is None:
            api_token = self._get_secret("osdg", "api_token")
            self._osdg_client = OSDGClient(api_token=api_token)
        return self._osdg_client

    def sdg_goal_map(self) -> Dict[str, Dict[str, Any]]:
        if self._sdg_goal_cache is None:
            goals = self.un_sdg_client().list_goals()
            goal_map: Dict[str, Dict[str, Any]] = {}
            for goal in goals:
                code = str(goal.get("code")) if isinstance(goal, dict) else None
                if code:
                    goal_map[code] = goal  # type: ignore[assignment]
            self._sdg_goal_cache = goal_map
        return self._sdg_goal_cache

    def classify_text_with_osdg(self, text: str, *, language: Optional[str] = None) -> Dict[str, Any]:
        if self.context.options.dry_run:
            return {
                "note": "Dry-run mode enabled; skipped OSDG classification.",
                "language": language,
                "length": len(text),
            }
        client = self.osdg_client()
        return client.classify_text(text, language=language)

    def chart_mcp_endpoint(self) -> str:
        secret_endpoint = self._get_secret("chart_mcp", "endpoint")
        if secret_endpoint:
            return secret_endpoint
        env_endpoint = os.getenv("TIANGONG_CHART_MCP_ENDPOINT")
        if env_endpoint:
            return env_endpoint
        return ChartMCPAdapter().endpoint

    def verify_chart_mcp(self) -> VerificationResult:
        endpoint = self.chart_mcp_endpoint()
        adapter = ChartMCPAdapter(endpoint=endpoint)
        return adapter.verify()
