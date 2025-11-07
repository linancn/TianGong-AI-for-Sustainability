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
from logging import LoggerAdapter
from typing import Any, Dict, Mapping, Optional, Sequence

from ..adapters import AdapterError, ChartMCPAdapter, DataSourceAdapter, VerificationResult
from ..adapters.api import ArxivClient, CrossrefClient, GitHubTopicsClient, OpenAlexClient, OSDGClient, SemanticScholarClient, UNSDGClient
from ..adapters.environment import GridIntensityCLIAdapter
from ..core import DataSourceDescriptor, DataSourceRegistry, DataSourceStatus, ExecutionContext, get_logger
from ..core.mcp import MCPServerConfig, load_mcp_server_configs
from ..core.mcp_client import MCPToolClient
from ..core.prompts import LoadedPromptTemplate, PromptTemplateError, load_prompt_template


@dataclass(slots=True)
class ResearchServices:
    """High-level façade used by CLI commands and automations."""

    registry: DataSourceRegistry
    context: ExecutionContext
    logger: LoggerAdapter = field(init=False, repr=False)
    _un_sdg_client: Optional[UNSDGClient] = field(default=None, init=False, repr=False)
    _semantic_scholar_client: Optional[SemanticScholarClient] = field(default=None, init=False, repr=False)
    _openalex_client: Optional[OpenAlexClient] = field(default=None, init=False, repr=False)
    _arxiv_client: Optional[ArxivClient] = field(default=None, init=False, repr=False)
    _github_topics_client: Optional[GitHubTopicsClient] = field(default=None, init=False, repr=False)
    _osdg_client: Optional[OSDGClient] = field(default=None, init=False, repr=False)
    _crossref_client: Optional[CrossrefClient] = field(default=None, init=False, repr=False)
    _sdg_goal_cache: Optional[Dict[str, Dict[str, Any]]] = field(default=None, init=False, repr=False)
    _mcp_configs: Optional[Dict[str, MCPServerConfig]] = field(default=None, init=False, repr=False)
    _mcp_client: Optional[MCPToolClient] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if hasattr(self.context, "get_logger"):
            self.logger = self.context.get_logger(self.__class__.__name__)
        else:  # pragma: no cover - defensive for legacy contexts
            self.logger = get_logger(self.__class__.__name__)

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
        self._require_source_enabled(source_id)
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

    def _require_source_enabled(self, source_id: str) -> None:
        if not self.context.is_enabled(source_id):
            raise AdapterError(f"Data source '{source_id}' is disabled in the current execution context.")

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

        self.logger.info("Querying carbon intensity", extra={"location": location, "provider": provider})
        result = adapter.query(location=location, provider=provider)
        result.setdefault("provider", provider)
        result.setdefault("location", location)
        self.logger.debug("Carbon intensity result", extra={"payload": result})
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
        self._require_source_enabled("un_sdg_api")
        if self._un_sdg_client is None:
            self._un_sdg_client = UNSDGClient()
        return self._un_sdg_client

    def semantic_scholar_client(self) -> SemanticScholarClient:
        self._require_source_enabled("semantic_scholar")
        if self._semantic_scholar_client is None:
            api_key = self._get_secret("semantic_scholar", "api_key")
            self._semantic_scholar_client = SemanticScholarClient(api_key=api_key)
        return self._semantic_scholar_client

    def openalex_client(self) -> OpenAlexClient:
        self._require_source_enabled("openalex")
        if self._openalex_client is None:
            mailto = self._get_secret("openalex", "mailto") or os.getenv("TIANGONG_OPENALEX_MAILTO") or "tiangong-cli@localhost"
            self._openalex_client = OpenAlexClient(mailto=mailto)
        return self._openalex_client

    def arxiv_client(self) -> ArxivClient:
        self._require_source_enabled("arxiv")
        if self._arxiv_client is None:
            self._arxiv_client = ArxivClient()
        return self._arxiv_client

    def github_topics_client(self) -> GitHubTopicsClient:
        self._require_source_enabled("github_topics")
        if self._github_topics_client is None:
            token = self._get_secret("github", "token")
            self._github_topics_client = GitHubTopicsClient(token=token)
        return self._github_topics_client

    def osdg_client(self) -> OSDGClient:
        self._require_source_enabled("osdg_api")
        if self._osdg_client is None:
            api_token = self._get_secret("osdg", "api_token")
            self._osdg_client = OSDGClient(api_token=api_token)
        return self._osdg_client

    def crossref_client(self) -> CrossrefClient:
        self._require_source_enabled("crossref")
        if self._crossref_client is None:
            mailto = self._get_secret("crossref", "mailto") or os.getenv("TIANGONG_CROSSREF_MAILTO")
            if not mailto:
                raise AdapterError("Crossref requires a contact email. Set crossref.mailto in .secrets or TIANGONG_CROSSREF_MAILTO.")
            self._crossref_client = CrossrefClient(mailto=mailto)
        return self._crossref_client

    def sdg_goal_map(self) -> Dict[str, Dict[str, Any]]:
        if self._sdg_goal_cache is None:
            self.logger.info("Loading SDG catalogue via UNSDG client")
            goals = self.un_sdg_client().list_goals()
            goal_map: Dict[str, Dict[str, Any]] = {}
            for goal in goals:
                code = str(goal.get("code")) if isinstance(goal, dict) else None
                if code:
                    goal_map[code] = goal  # type: ignore[assignment]
            self._sdg_goal_cache = goal_map
            self.logger.debug("Cached SDG goal map", extra={"goal_count": len(goal_map)})
        return self._sdg_goal_cache

    def classify_text_with_osdg(self, text: str, *, language: Optional[str] = None) -> Dict[str, Any]:
        if self.context.options.dry_run:
            self.logger.debug(
                "Skipping OSDG classification due to dry-run mode",
                extra={"language": language, "text_length": len(text)},
            )
            return {
                "note": "Dry-run mode enabled; skipped OSDG classification.",
                "language": language,
                "length": len(text),
            }
        client = self.osdg_client()
        self.logger.info(
            "Submitting text to OSDG classifier",
            extra={"language": language, "text_length": len(text)},
        )
        return client.classify_text(text, language=language)

    def chart_mcp_endpoint(self) -> str:
        self._require_source_enabled("chart_mcp_server")
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
        self.logger.info("Verifying AntV MCP chart endpoint", extra={"endpoint": endpoint})
        return adapter.verify()

    # -- Remote MCP helpers -----------------------------------------------------

    def mcp_server_configs(self) -> Dict[str, MCPServerConfig]:
        if self._mcp_configs is None:
            self._mcp_configs = load_mcp_server_configs(self.context.secrets)
        return self._mcp_configs

    def mcp_tool_client(self) -> MCPToolClient:
        if self._mcp_client is None:
            configs = self.mcp_server_configs()
            if not configs:
                raise AdapterError("No MCP servers are configured in the current secrets bundle.")
            self._mcp_client = MCPToolClient(configs)
        return self._mcp_client

    def list_mcp_tools(self, source_id: str) -> Sequence[Dict[str, Any]]:
        config = self._resolve_mcp_config(source_id)
        client = self.mcp_tool_client()
        tools = client.list_tools(config.service_name)
        return [{"name": getattr(tool, "name", None), "description": getattr(tool, "description", None)} for tool in tools]

    def invoke_mcp_tool(
        self,
        source_id: str,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> tuple[Any, Optional[list[dict[str, Any]]]]:
        config = self._resolve_mcp_config(source_id)
        if config.requires_api_key and not config.api_key:
            raise AdapterError(f"MCP server '{source_id}' requires an API key. " "Add credentials to .secrets or configure the referenced environment variable.")
        client = self.mcp_tool_client()
        return client.invoke_tool(config.service_name, tool_name, arguments or {})

    def _resolve_mcp_config(self, source_id: str) -> MCPServerConfig:
        self._require_source_enabled(source_id)
        configs = self.mcp_server_configs()
        config = configs.get(source_id)
        if not config:
            raise AdapterError(f"MCP server '{source_id}' is not configured.")
        return config

    # -- Prompt templates ------------------------------------------------------

    def load_prompt_template(
        self,
        template: Optional[str] = None,
        *,
        language: Optional[str] = None,
    ) -> LoadedPromptTemplate:
        """
        Resolve a prompt template using the execution context defaults.

        Parameters
        ----------
        template:
            Optional alias or path. When omitted the execution options'
            ``prompt_template`` value (if any) is used.
        language:
            Optional override for the language hint. Falls back to
            ``ExecutionOptions.prompt_language`` when not provided.
        """

        chosen_template = template or getattr(self.context.options, "prompt_template", None)
        chosen_language = language or getattr(self.context.options, "prompt_language", None)
        try:
            loaded = load_prompt_template(chosen_template, language=chosen_language)
        except PromptTemplateError as exc:
            raise AdapterError(str(exc)) from exc
        self.logger.debug(
            "Loaded prompt template",
            extra={
                "identifier": loaded.identifier,
                "path": loaded.path.as_posix(),
                "language": loaded.language,
            },
        )
        return loaded
