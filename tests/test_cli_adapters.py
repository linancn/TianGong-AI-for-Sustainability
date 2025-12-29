from __future__ import annotations

from unittest.mock import patch

from tiangong_ai_for_sustainability.adapters.api.arxiv import ArxivAdapter
from tiangong_ai_for_sustainability.adapters.api.crossref import CrossrefAdapter
from tiangong_ai_for_sustainability.adapters.api.dimensions import DimensionsAIAdapter
from tiangong_ai_for_sustainability.adapters.api.esa_copernicus import CopernicusDataspaceAdapter
from tiangong_ai_for_sustainability.adapters.api.esg import (
    CdpClimateAdapter,
    IssESGAdapter,
    LsegESGAdapter,
    MsciESGAdapter,
    SpGlobalESGAdapter,
    SustainalyticsAdapter,
)
from tiangong_ai_for_sustainability.adapters.api.ilostat import ILOSTATAdapter
from tiangong_ai_for_sustainability.adapters.api.imf import IMFClimateAdapter
from tiangong_ai_for_sustainability.adapters.api.ipbes import IPBESAdapter
from tiangong_ai_for_sustainability.adapters.api.ipcc import IPCCDDCAdapter
from tiangong_ai_for_sustainability.adapters.api.kaggle import KaggleAdapter
from tiangong_ai_for_sustainability.adapters.api.lens import LensOrgAdapter
from tiangong_ai_for_sustainability.adapters.api.nasa_earthdata import NasaEarthdataAdapter
from tiangong_ai_for_sustainability.adapters.api.open_supply_hub import OpenSupplyHubAdapter
from tiangong_ai_for_sustainability.adapters.api.openalex import OpenAlexAdapter
from tiangong_ai_for_sustainability.adapters.api.premium_literature import AcmDigitalLibraryAdapter, ScopusAdapter
from tiangong_ai_for_sustainability.adapters.api.standards import (
    GhgProtocolWorkbooksAdapter,
    GriTaxonomyAdapter,
)
from tiangong_ai_for_sustainability.adapters.api.transparency import TransparencyCPIAdapter
from tiangong_ai_for_sustainability.adapters.api.web_of_science import WebOfScienceAdapter
from tiangong_ai_for_sustainability.adapters.api.wikidata import WikidataAdapter
from tiangong_ai_for_sustainability.adapters.api.world_bank import WorldBankAdapter
from tiangong_ai_for_sustainability.adapters.environment import GoogleEarthEngineCLIAdapter
from tiangong_ai_for_sustainability.adapters.tools import GeminiDeepResearchAdapter
from tiangong_ai_for_sustainability.cli.adapters import resolve_adapter
from tiangong_ai_for_sustainability.core.context import ExecutionContext


def test_resolve_adapter_crossref(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("crossref", {})["mailto"] = "research@example.com"

    adapter = resolve_adapter("crossref", context)

    assert isinstance(adapter, CrossrefAdapter)
    assert adapter.client.mailto == "research@example.com"


def test_resolve_adapter_arxiv(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("arxiv", context)

    assert isinstance(adapter, ArxivAdapter)


def test_resolve_adapter_kaggle(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("kaggle", {})["username"] = "researcher"
    context.secrets.data["kaggle"]["key"] = "secret"

    with patch("tiangong_ai_for_sustainability.cli.adapters.KaggleClient") as mock_client:
        client_instance = object()
        mock_client.return_value = client_instance
        adapter = resolve_adapter("kaggle", context)

    assert isinstance(adapter, KaggleAdapter)
    assert adapter.client is client_instance
    mock_client.assert_called_once_with(username="researcher", key="secret")


def test_resolve_adapter_copernicus(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    with patch("tiangong_ai_for_sustainability.cli.adapters.CopernicusDataspaceClient") as mock_client:
        client_instance = object()
        mock_client.return_value = client_instance
        adapter = resolve_adapter("esa_copernicus", context)

    assert isinstance(adapter, CopernicusDataspaceAdapter)
    assert adapter.client is client_instance
    mock_client.assert_called_once_with()


def test_resolve_adapter_dimensions(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("dimensions_ai", {})["api_key"] = "dim-token"

    with patch("tiangong_ai_for_sustainability.cli.adapters.DimensionsAIClient") as mock_client:
        client_instance = object()
        mock_client.return_value = client_instance
        adapter = resolve_adapter("dimensions_ai", context)

    assert isinstance(adapter, DimensionsAIAdapter)
    assert adapter.client is client_instance
    mock_client.assert_called_once_with(api_key="dim-token")


def test_resolve_adapter_cdp_climate(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("cdp_climate", {})["api_key"] = "cdp-token"

    adapter = resolve_adapter("cdp_climate", context)

    assert isinstance(adapter, CdpClimateAdapter)
    assert adapter.api_key == "cdp-token"


def test_resolve_adapter_nasa_earthdata(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    with patch("tiangong_ai_for_sustainability.cli.adapters.NasaEarthdataClient") as mock_client:
        client_instance = object()
        mock_client.return_value = client_instance
        adapter = resolve_adapter("nasa_earthdata", context)

    assert isinstance(adapter, NasaEarthdataAdapter)
    assert adapter.client is client_instance
    mock_client.assert_called_once_with()


def test_resolve_adapter_lseg_esg(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("lseg_esg", {})["api_key"] = "lseg-token"

    adapter = resolve_adapter("lseg_esg", context)

    assert isinstance(adapter, LsegESGAdapter)
    assert adapter.api_key == "lseg-token"


def test_resolve_adapter_lens(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("lens_org_api", {})["api_key"] = "lens-token"

    with patch("tiangong_ai_for_sustainability.cli.adapters.LensOrgClient") as mock_client:
        client_instance = object()
        mock_client.return_value = client_instance
        adapter = resolve_adapter("lens_org_api", context)

    assert isinstance(adapter, LensOrgAdapter)
    assert adapter.client is client_instance
    mock_client.assert_called_once_with(api_key="lens-token")


def test_resolve_adapter_open_supply_hub(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("open_supply_hub", {})["api_key"] = "osh-token"

    with patch("tiangong_ai_for_sustainability.cli.adapters.OpenSupplyHubClient") as mock_client:
        client_instance = object()
        mock_client.return_value = client_instance
        adapter = resolve_adapter("open_supply_hub", context)

    assert isinstance(adapter, OpenSupplyHubAdapter)
    assert adapter.client is client_instance
    mock_client.assert_called_once_with(api_key="osh-token")


def test_resolve_adapter_msci_esg(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("msci_esg", {})["api_key"] = "msci-token"

    adapter = resolve_adapter("msci_esg", context)

    assert isinstance(adapter, MsciESGAdapter)
    assert adapter.api_key == "msci-token"


def test_resolve_adapter_sustainalytics(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("sustainalytics", {})["api_key"] = "susta-token"

    adapter = resolve_adapter("sustainalytics", context)

    assert isinstance(adapter, SustainalyticsAdapter)
    assert adapter.api_key == "susta-token"


def test_resolve_adapter_google_earth_engine(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("google_earth_engine", context)

    assert isinstance(adapter, GoogleEarthEngineCLIAdapter)


def test_resolve_adapter_world_bank(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("world_bank_sustainability", context)

    assert isinstance(adapter, WorldBankAdapter)


def test_resolve_adapter_sp_global_esg(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("sp_global_esg", {})["api_key"] = "spg-token"

    adapter = resolve_adapter("sp_global_esg", context)

    assert isinstance(adapter, SpGlobalESGAdapter)
    assert adapter.api_key == "spg-token"


def test_resolve_adapter_iss_esg(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("iss_esg", {})["api_key"] = "iss-token"

    adapter = resolve_adapter("iss_esg", context)

    assert isinstance(adapter, IssESGAdapter)
    assert adapter.api_key == "iss-token"


def test_resolve_adapter_acm(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("acm_digital_library", {})["api_key"] = "acm-token"

    adapter = resolve_adapter("acm_digital_library", context)

    assert isinstance(adapter, AcmDigitalLibraryAdapter)
    assert adapter.api_key == "acm-token"


def test_resolve_adapter_scopus(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("scopus", {})["api_key"] = "scopus-token"

    adapter = resolve_adapter("scopus", context)

    assert isinstance(adapter, ScopusAdapter)
    assert adapter.api_key == "scopus-token"


def test_resolve_adapter_web_of_science(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("web_of_science", {})["api_key"] = "wos-token"

    with patch("tiangong_ai_for_sustainability.cli.adapters.WebOfScienceClient") as mock_client:
        client_instance = object()
        mock_client.return_value = client_instance
        adapter = resolve_adapter("web_of_science", context)

    assert isinstance(adapter, WebOfScienceAdapter)
    assert adapter.client is client_instance
    mock_client.assert_called_once_with(api_key="wos-token")


def test_resolve_adapter_gri_taxonomy(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("gri_taxonomy", context)

    assert isinstance(adapter, GriTaxonomyAdapter)


def test_resolve_adapter_ghg_workbooks(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("ghg_protocol_workbooks", context)

    assert isinstance(adapter, GhgProtocolWorkbooksAdapter)


def test_resolve_adapter_openalex(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("openalex", {})["mailto"] = "contact@example.com"

    adapter = resolve_adapter("openalex", context)

    assert isinstance(adapter, OpenAlexAdapter)
    assert adapter.client.mailto == "contact@example.com"


def test_resolve_adapter_ipcc(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("ipcc_ddc", context)

    assert isinstance(adapter, IPCCDDCAdapter)


def test_resolve_adapter_ipbes(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("ipbes_data_portal", context)

    assert isinstance(adapter, IPBESAdapter)


def test_resolve_adapter_ilostat(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("ilostat", context)

    assert isinstance(adapter, ILOSTATAdapter)


def test_resolve_adapter_imf(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("imf_climate_dashboard", context)

    assert isinstance(adapter, IMFClimateAdapter)


def test_resolve_adapter_transparency(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("transparency_international_cpi", context)

    assert isinstance(adapter, TransparencyCPIAdapter)


def test_resolve_adapter_wikidata(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("wikidata", context)

    assert isinstance(adapter, WikidataAdapter)


def test_resolve_adapter_gemini_deep_research(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.gemini.api_key = "gemini-key"

    adapter = resolve_adapter("gemini_deep_research", context)

    assert isinstance(adapter, GeminiDeepResearchAdapter)
