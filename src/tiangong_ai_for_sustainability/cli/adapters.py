"""
Helpers for resolving data source adapters in CLI contexts.
"""

from __future__ import annotations

from typing import Optional

from ..adapters import ChartMCPAdapter, DataSourceAdapter
from ..adapters.api import (
    ArxivAdapter,
    ArxivClient,
    CrossrefAdapter,
    CrossrefClient,
    GitHubTopicsAdapter,
    GitHubTopicsClient,
    OSDGAdapter,
    OSDGClient,
    SemanticScholarAdapter,
    SemanticScholarClient,
    UNSDGAdapter,
    UNSDGClient,
)
from ..adapters.environment import GridIntensityCLIAdapter
from ..adapters.tools import OpenAIDeepResearchAdapter, RemoteMCPAdapter
from ..core.context import ExecutionContext
from ..core.mcp import load_mcp_server_configs


def resolve_adapter(source_id: str, context: ExecutionContext) -> Optional[DataSourceAdapter]:
    """
    Locate a concrete adapter implementation for a registry source.
    """

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

    crossref_mailto: Optional[str] = None
    crossref_section = secrets.get("crossref")
    if isinstance(crossref_section, dict):
        value = crossref_section.get("mailto")
        if isinstance(value, str) and value:
            crossref_mailto = value

    adapters = (
        GridIntensityCLIAdapter(),
        UNSDGAdapter(client=UNSDGClient()),
        SemanticScholarAdapter(client=SemanticScholarClient(api_key=semantic_key)),
        ArxivAdapter(client=ArxivClient()),
        GitHubTopicsAdapter(client=GitHubTopicsClient(token=github_token)),
        OSDGAdapter(client=OSDGClient(api_token=osdg_token)),
        CrossrefAdapter(client=CrossrefClient(mailto=crossref_mailto)),
        ChartMCPAdapter(),
        OpenAIDeepResearchAdapter(settings=context.secrets.openai),
    )
    for adapter in adapters:
        if source_id == adapter.source_id:
            return adapter

    mcp_configs = load_mcp_server_configs(context.secrets)
    config = mcp_configs.get(source_id)
    if config:
        return RemoteMCPAdapter(config=config)
    return None
