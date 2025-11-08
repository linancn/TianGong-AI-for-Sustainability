from __future__ import annotations

from unittest.mock import patch

from tiangong_ai_for_sustainability.adapters.api.arxiv import ArxivAdapter
from tiangong_ai_for_sustainability.adapters.api.crossref import CrossrefAdapter
from tiangong_ai_for_sustainability.adapters.api.ilostat import ILOSTATAdapter
from tiangong_ai_for_sustainability.adapters.api.imf import IMFClimateAdapter
from tiangong_ai_for_sustainability.adapters.api.ipbes import IPBESAdapter
from tiangong_ai_for_sustainability.adapters.api.ipcc import IPCCDDCAdapter
from tiangong_ai_for_sustainability.adapters.api.kaggle import KaggleAdapter
from tiangong_ai_for_sustainability.adapters.api.openalex import OpenAlexAdapter
from tiangong_ai_for_sustainability.adapters.api.transparency import TransparencyCPIAdapter
from tiangong_ai_for_sustainability.adapters.api.wikidata import WikidataAdapter
from tiangong_ai_for_sustainability.adapters.api.world_bank import WorldBankAdapter
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


def test_resolve_adapter_world_bank(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("world_bank_sustainability", context)

    assert isinstance(adapter, WorldBankAdapter)


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
