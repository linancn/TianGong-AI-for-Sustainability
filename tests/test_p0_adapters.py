from __future__ import annotations

from unittest.mock import MagicMock

from tiangong_ai_for_sustainability.adapters.api import APIError
from tiangong_ai_for_sustainability.adapters.api.ilostat import ILOSTATAdapter
from tiangong_ai_for_sustainability.adapters.api.imf import EXPECTED_TITLE, IMFClimateAdapter
from tiangong_ai_for_sustainability.adapters.api.ipbes import IPBESAdapter
from tiangong_ai_for_sustainability.adapters.api.ipcc import IPCCDDCAdapter
from tiangong_ai_for_sustainability.adapters.api.transparency import TransparencyCPIAdapter
from tiangong_ai_for_sustainability.adapters.api.wikidata import WikidataAdapter


def test_ipcc_adapter_verify_success():
    client = MagicMock()
    client.list_recent_records.return_value = [{"metadata": {"title": "Atlas dataset", "doi": "10.1234/ipcc"}}]
    client.fetch_latest_title.return_value = "Atlas dataset"
    adapter = IPCCDDCAdapter(client=client)

    result = adapter.verify()

    assert result.success is True
    assert result.details["latest_title"] == "Atlas dataset"
    assert result.details["doi"] == "10.1234/ipcc"
    client.list_recent_records.assert_called_once_with(adapter.community_id, size=1)


def test_ipcc_adapter_verify_failure():
    client = MagicMock()
    client.list_recent_records.side_effect = APIError("timeout")
    adapter = IPCCDDCAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "verification failed" in result.message.lower()


def test_ipbes_adapter_success():
    client = MagicMock()
    client.list_recent_records.return_value = [{"metadata": {"title": "IPBES report"}}]
    client.fetch_latest_title.return_value = "IPBES report"
    adapter = IPBESAdapter(client=client)

    result = adapter.verify()

    assert result.success is True
    assert result.details["latest_title"] == "IPBES report"


def test_ilostat_adapter_success():
    client = MagicMock()
    client.list_datasets.return_value = [{"id": "EMP_TEMP", "name": "Employment, temporary"}]
    adapter = ILOSTATAdapter(client=client)

    result = adapter.verify()

    assert result.success is True
    assert result.details["dataset_id"] == "EMP_TEMP"
    assert "Employment" in result.details["dataset_label"]


def test_ilostat_adapter_failure():
    client = MagicMock()
    client.list_datasets.side_effect = APIError("blocked")
    adapter = ILOSTATAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "verification failed" in result.message.lower()


def test_imf_climate_adapter_success():
    client = MagicMock()
    client.fetch_homepage_title.return_value = EXPECTED_TITLE
    adapter = IMFClimateAdapter(client=client)

    result = adapter.verify()

    assert result.success is True
    assert result.details["title"] == EXPECTED_TITLE


def test_imf_climate_adapter_failure():
    client = MagicMock()
    client.fetch_homepage_title.side_effect = APIError("404")
    adapter = IMFClimateAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "verification failed" in result.message.lower()


def test_transparency_cpi_adapter_success():
    client = MagicMock()
    client.fetch_sample_row.return_value = {"country": "Exampleland", "2023": "67"}
    adapter = TransparencyCPIAdapter(client=client)

    result = adapter.verify()

    assert result.success is True
    assert result.details["sample_country"] == "Exampleland"
    assert result.details["sample_year"] == "2023"
    assert result.details["sample_score"] == "67"


def test_transparency_cpi_adapter_failure():
    client = MagicMock()
    client.fetch_sample_row.side_effect = APIError("down")
    adapter = TransparencyCPIAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "verification failed" in result.message.lower()


def test_wikidata_adapter_success():
    client = MagicMock()
    client.run_query.return_value = [
        {
            "item": {"value": "http://www.wikidata.org/entity/Q30"},
            "itemLabel": {"value": "United States of America"},
        }
    ]
    adapter = WikidataAdapter(client=client)

    result = adapter.verify()

    assert result.success is True
    assert result.details["sample_item"].endswith("Q30")
    assert result.details["sample_label"] == "United States of America"
    client.run_query.assert_called_once_with(adapter.sample_query)


def test_wikidata_adapter_failure():
    client = MagicMock()
    client.run_query.side_effect = APIError("rate limited")
    adapter = WikidataAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "verification failed" in result.message.lower()
