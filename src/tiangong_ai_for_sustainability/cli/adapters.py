"""
Helpers for resolving data source adapters in CLI contexts.
"""

from __future__ import annotations

import os
from typing import Optional

from ..adapters import ChartMCPAdapter, DataSourceAdapter
from ..adapters.api import (
    AcmDigitalLibraryAdapter,
    ArxivAdapter,
    ArxivClient,
    CdpClimateAdapter,
    CopernicusDataspaceAdapter,
    CopernicusDataspaceClient,
    CrossrefAdapter,
    CrossrefClient,
    DifyKnowledgeBaseAdapter,
    DifyKnowledgeBaseClient,
    DimensionsAIAdapter,
    DimensionsAIClient,
    GhgProtocolWorkbooksAdapter,
    GitHubTopicsAdapter,
    GitHubTopicsClient,
    GriTaxonomyAdapter,
    ILOSTATAdapter,
    ILOSTATClient,
    IMFClimateAdapter,
    IMFClimateClient,
    IPBESAdapter,
    IPCCDDCAdapter,
    IssESGAdapter,
    KaggleAdapter,
    KaggleClient,
    LensOrgAdapter,
    LensOrgClient,
    LsegESGAdapter,
    MsciESGAdapter,
    NasaEarthdataAdapter,
    NasaEarthdataClient,
    OpenAlexAdapter,
    OpenAlexClient,
    OpenSupplyHubAdapter,
    OpenSupplyHubClient,
    OSDGAdapter,
    OSDGClient,
    ScopusAdapter,
    SemanticScholarAdapter,
    SemanticScholarClient,
    SpGlobalESGAdapter,
    SustainalyticsAdapter,
    TransparencyCPIAdapter,
    TransparencyCPIClient,
    UNSDGAdapter,
    UNSDGClient,
    WebOfScienceAdapter,
    WikidataAdapter,
    WikidataClient,
    WorldBankAdapter,
    WorldBankClient,
    ZenodoCommunityClient,
)
from ..adapters.api.web_of_science import WebOfScienceClient
from ..adapters.environment import GoogleEarthEngineCLIAdapter, GridIntensityCLIAdapter
from ..adapters.tools import GeminiDeepResearchAdapter, OpenAIDeepResearchAdapter, RemoteMCPAdapter
from ..core.context import ExecutionContext
from ..core.mcp_config import load_mcp_server_configs


def resolve_adapter(source_id: str, context: ExecutionContext) -> Optional[DataSourceAdapter]:
    """
    Locate a concrete adapter implementation for a registry source.
    """

    secrets = context.secrets.data

    def get_api_key(section_name: str, env_var: str) -> Optional[str]:
        section = secrets.get(section_name)
        if isinstance(section, dict):
            value = section.get("api_key")
            if isinstance(value, str) and value:
                return value
        env_value = os.getenv(env_var)
        if env_value:
            return env_value
        return None

    def get_string(section_name: str, key: str, env_var: Optional[str] = None) -> Optional[str]:
        section = secrets.get(section_name)
        if isinstance(section, dict):
            value = section.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                return env_value
        return None

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

    ilostat_cookies: Optional[dict[str, str]] = None
    ilostat_section = secrets.get("ilostat")
    if isinstance(ilostat_section, dict):
        cookies: dict[str, str] = {}
        cf_clearance = ilostat_section.get("cf_clearance")
        if isinstance(cf_clearance, str) and cf_clearance:
            cookies["cf_clearance"] = cf_clearance
        session_token = ilostat_section.get("session") or ilostat_section.get("ilostat_session")
        if isinstance(session_token, str) and session_token:
            cookies["session"] = session_token
        if cookies:
            ilostat_cookies = cookies

    dimensions_key = get_api_key("dimensions_ai", "TIANGONG_DIMENSIONS_API_KEY")
    lens_key = get_api_key("lens_org_api", "TIANGONG_LENS_API_KEY")
    cdp_key = get_api_key("cdp_climate", "TIANGONG_CDP_API_KEY")
    lseg_key = get_api_key("lseg_esg", "TIANGONG_LSEG_API_KEY")
    msci_key = get_api_key("msci_esg", "TIANGONG_MSCI_API_KEY")
    sustainalytics_key = get_api_key("sustainalytics", "TIANGONG_SUSTAINALYTICS_API_KEY")
    spglobal_key = get_api_key("sp_global_esg", "TIANGONG_SPGLOBAL_API_KEY")
    iss_key = get_api_key("iss_esg", "TIANGONG_ISS_API_KEY")
    open_supply_key = get_api_key("open_supply_hub", "TIANGONG_OPEN_SUPPLY_HUB_API_KEY")
    acm_key = get_api_key("acm_digital_library", "TIANGONG_ACM_API_KEY")
    scopus_key = get_api_key("scopus", "TIANGONG_SCOPUS_API_KEY")
    wos_key = get_api_key("web_of_science", "TIANGONG_WOS_API_KEY")
    dify_api_key = get_api_key("dify_knowledge", "TIANGONG_DIFY_API_KEY")

    dify_dataset_id = get_string("dify_knowledge", "dataset_id", "TIANGONG_DIFY_DATASET_ID")
    dify_base_url = get_string("dify_knowledge", "api_base_url", "TIANGONG_DIFY_API_BASE_URL") or DifyKnowledgeBaseClient.DEFAULT_BASE_URL
    dify_test_query = get_string("dify_knowledge", "test_query", "TIANGONG_DIFY_TEST_QUERY") or "sustainability research evidence"
    dify_retrieval_model = None
    dify_section = secrets.get("dify_knowledge")
    if isinstance(dify_section, dict):
        raw_model = dify_section.get("retrieval_model")
        if isinstance(raw_model, dict):
            dify_retrieval_model = raw_model

    adapters = (
        GridIntensityCLIAdapter(),
        GoogleEarthEngineCLIAdapter(),
        IPCCDDCAdapter(client=ZenodoCommunityClient()),
        IPBESAdapter(client=ZenodoCommunityClient()),
        UNSDGAdapter(client=UNSDGClient()),
        SemanticScholarAdapter(client=SemanticScholarClient(api_key=semantic_key)),
        OpenAlexAdapter(client=OpenAlexClient(mailto=openalex_mailto)),
        ILOSTATAdapter(client=ILOSTATClient(cookies=ilostat_cookies)),
        IMFClimateAdapter(client=IMFClimateClient()),
        TransparencyCPIAdapter(client=TransparencyCPIClient()),
        WikidataAdapter(client=WikidataClient()),
        WorldBankAdapter(client=WorldBankClient()),
        ArxivAdapter(client=ArxivClient()),
        GitHubTopicsAdapter(client=GitHubTopicsClient(token=github_token)),
        OSDGAdapter(client=OSDGClient(api_token=osdg_token)),
        CrossrefAdapter(client=CrossrefClient(mailto=crossref_mailto)),
        KaggleAdapter(client=KaggleClient(username=kaggle_username, key=kaggle_key)),
        DimensionsAIAdapter(client=DimensionsAIClient(api_key=dimensions_key)),
        LensOrgAdapter(client=LensOrgClient(api_key=lens_key)),
        OpenSupplyHubAdapter(client=OpenSupplyHubClient(api_key=open_supply_key)),
        CdpClimateAdapter(api_key=cdp_key),
        LsegESGAdapter(api_key=lseg_key),
        MsciESGAdapter(api_key=msci_key),
        SustainalyticsAdapter(api_key=sustainalytics_key),
        SpGlobalESGAdapter(api_key=spglobal_key),
        IssESGAdapter(api_key=iss_key),
        AcmDigitalLibraryAdapter(api_key=acm_key),
        ScopusAdapter(api_key=scopus_key),
        WebOfScienceAdapter(client=WebOfScienceClient(api_key=wos_key)),
        GriTaxonomyAdapter(),
        GhgProtocolWorkbooksAdapter(),
        CopernicusDataspaceAdapter(client=CopernicusDataspaceClient()),
        NasaEarthdataAdapter(client=NasaEarthdataClient()),
        DifyKnowledgeBaseAdapter(
            client=DifyKnowledgeBaseClient(api_key=dify_api_key, base_url=dify_base_url),
            dataset_id=dify_dataset_id,
            test_query=dify_test_query,
            retrieval_model=dify_retrieval_model,
        ),
        ChartMCPAdapter(),
        OpenAIDeepResearchAdapter(settings=context.secrets.openai),
        GeminiDeepResearchAdapter(settings=context.secrets.gemini),
    )
    for adapter in adapters:
        if source_id == adapter.source_id:
            return adapter

    mcp_configs = load_mcp_server_configs(context.secrets)
    config = mcp_configs.get(source_id)
    if config:
        return RemoteMCPAdapter(config=config)
    return None
