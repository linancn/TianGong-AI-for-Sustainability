from __future__ import annotations

from unittest.mock import MagicMock

from tiangong_ai_for_sustainability.adapters.api import APIError
from tiangong_ai_for_sustainability.adapters.api.crossref import _VERIFICATION_DOI, CrossrefAdapter


def test_crossref_adapter_verify_success():
    client = MagicMock()
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
    client.get_work.side_effect = APIError("down")
    adapter = CrossrefAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "Crossref API verification failed" in result.message
