"""
Helpers for resolving data source adapters in CLI contexts.
"""

from __future__ import annotations

import os
from typing import Optional

from ..adapters import ChartMCPAdapter, DataSourceAdapter
from ..adapters.api import (
    ArxivAdapter,
    ArxivClient,
    CopernicusDataspaceAdapter,
    CopernicusDataspaceClient,
    CrossrefAdapter,
    CrossrefClient,
    GitHubTopicsAdapter,
    GitHubTopicsClient,
    ILOSTATAdapter,
    ILOSTATClient,
    IMFClimateAdapter,
    IMFClimateClient,
    IPBESAdapter,
    IPCCDDCAdapter,
    KaggleAdapter,
    KaggleClient,
    NasaEarthdataAdapter,
    NasaEarthdataClient,
    OpenAlexAdapter,
    OpenAlexClient,
    OSDGAdapter,
    OSDGClient,
    SemanticScholarAdapter,
    SemanticScholarClient,
    TransparencyCPIAdapter,
    TransparencyCPIClient,
    UNSDGAdapter,
    UNSDGClient,
    WikidataAdapter,
    WikidataClient,
    WorldBankAdapter,
    WorldBankClient,
    ZenodoCommunityClient,
)
from ..adapters.environment import GoogleEarthEngineCLIAdapter, GridIntensityCLIAdapter
from ..adapters.tools import OpenAIDeepResearchAdapter, RemoteMCPAdapter
from ..core.context import ExecutionContext
from ..core.mcp_config import load_mcp_server_configs


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

    openalex_mailto: Optional[str] = None
    openalex_section = secrets.get("openalex")
    if isinstance(openalex_section, dict):
        value = openalex_section.get("mailto")
        if isinstance(value, str) and value:
            openalex_mailto = value
    if not openalex_mailto:
        env_mailto = os.getenv("TIANGONG_OPENALEX_MAILTO")
        if env_mailto:
            openalex_mailto = env_mailto
    if not openalex_mailto:
        openalex_mailto = crossref_mailto

    kaggle_username: Optional[str] = None
    kaggle_key: Optional[str] = None
    kaggle_section = secrets.get("kaggle")
    if isinstance(kaggle_section, dict):
        username_value = kaggle_section.get("username")
        key_value = kaggle_section.get("key")
        if isinstance(username_value, str) and username_value:
            kaggle_username = username_value
        if isinstance(key_value, str) and key_value:
            kaggle_key = key_value

    adapters = (
        GridIntensityCLIAdapter(),
        GoogleEarthEngineCLIAdapter(),
        IPCCDDCAdapter(client=ZenodoCommunityClient()),
        IPBESAdapter(client=ZenodoCommunityClient()),
        UNSDGAdapter(client=UNSDGClient()),
        SemanticScholarAdapter(client=SemanticScholarClient(api_key=semantic_key)),
        OpenAlexAdapter(client=OpenAlexClient(mailto=openalex_mailto)),
        ILOSTATAdapter(client=ILOSTATClient()),
        IMFClimateAdapter(client=IMFClimateClient()),
        TransparencyCPIAdapter(client=TransparencyCPIClient()),
        WikidataAdapter(client=WikidataClient()),
        WorldBankAdapter(client=WorldBankClient()),
        ArxivAdapter(client=ArxivClient()),
        GitHubTopicsAdapter(client=GitHubTopicsClient(token=github_token)),
        OSDGAdapter(client=OSDGClient(api_token=osdg_token)),
        CrossrefAdapter(client=CrossrefClient(mailto=crossref_mailto)),
        KaggleAdapter(client=KaggleClient(username=kaggle_username, key=kaggle_key)),
        CopernicusDataspaceAdapter(client=CopernicusDataspaceClient()),
        NasaEarthdataAdapter(client=NasaEarthdataClient()),
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
