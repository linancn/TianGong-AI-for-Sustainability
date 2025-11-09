from __future__ import annotations

from tiangong_ai_for_sustainability.adapters.api.web_of_science import WebOfScienceAdapter
from tiangong_ai_for_sustainability.adapters.base import AdapterError


class _NoKeyClient:
    api_key = None

    def sample_search(self):  # pragma: no cover - should never be called
        raise AssertionError("sample_search should not be invoked when api_key is missing")


class _SuccessfulClient:
    def __init__(self) -> None:
        self.api_key = "token"

    def sample_search(self):
        return {
            "metadata": {"total": 123, "page": 1},
            "hits": [
                {
                    "title": "Sustainability benchmarking via Web of Science",
                    "uid": "WOS:0000000001",
                    "identifiers": {"doi": "10.1234/example"},
                }
            ],
        }


class _FailingClient:
    def __init__(self) -> None:
        self.api_key = "token"

    def sample_search(self):
        raise AdapterError("downstream failure")


def test_web_of_science_adapter_missing_credentials():
    adapter = WebOfScienceAdapter(client=_NoKeyClient())

    result = adapter.verify()

    assert not result.success
    assert "api_key" in result.message


def test_web_of_science_adapter_success_details():
    adapter = WebOfScienceAdapter(client=_SuccessfulClient())

    result = adapter.verify()

    assert result.success
    assert result.details == {
        "total_results": 123,
        "page": 1,
        "sample_title": "Sustainability benchmarking via Web of Science",
        "sample_uid": "WOS:0000000001",
        "sample_doi": "10.1234/example",
    }


def test_web_of_science_adapter_reports_errors():
    adapter = WebOfScienceAdapter(client=_FailingClient())

    result = adapter.verify()

    assert not result.success
    assert "downstream failure" in result.message
