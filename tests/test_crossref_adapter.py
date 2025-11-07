from __future__ import annotations

from unittest.mock import MagicMock

from tiangong_ai_for_sustainability.adapters.api import APIError
from tiangong_ai_for_sustainability.adapters.api.crossref import _VERIFICATION_DOI, CrossrefAdapter


def test_crossref_adapter_verify_success():
    client = MagicMock()
    client.mailto = "research@example.com"
    client.get_work.return_value = {
        "title": ["Sample Title"],
        "issued": {"date-parts": [[2021, 5, 12]]},
    }
    adapter = CrossrefAdapter(client=client)

    result = adapter.verify()

    assert result.success is True
    assert result.details["sample_title"] == "Sample Title"
    assert result.details["issued_year"] == 2021
    client.get_work.assert_called_once_with(_VERIFICATION_DOI, select=["title", "issued"])


def test_crossref_adapter_verify_failure():
    client = MagicMock()
    client.mailto = "research@example.com"
    client.get_work.side_effect = APIError("down")
    adapter = CrossrefAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "Crossref API verification failed" in result.message


def test_crossref_adapter_missing_mailto():
    client = MagicMock()
    client.mailto = None
    client.get_work = MagicMock()
    adapter = CrossrefAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "contact email" in result.message
    client.get_work.assert_not_called()


def test_crossref_client_serialises_filters(monkeypatch):
    from tiangong_ai_for_sustainability.adapters.api.crossref import CrossrefClient

    captured_params = {}

    def fake_get_json(self, path, *, params):
        captured_params.update(params)
        return {"message": {}}

    monkeypatch.setattr(CrossrefClient, "_get_json", fake_get_json, raising=False)
    client = CrossrefClient(mailto="research@example.com")

    client.search_works(
        query="sustainability",
        filters={
            "from-pub-date": "2020-01-01",
            "type": ["journal-article", "book-chapter"],
        },
    )

    assert captured_params["filter"] == "from-pub-date:2020-01-01,type:journal-article,type:book-chapter"
    assert captured_params["mailto"] == "research@example.com"
