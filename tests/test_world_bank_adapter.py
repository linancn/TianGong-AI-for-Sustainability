from __future__ import annotations

from unittest.mock import MagicMock

from tiangong_ai_for_sustainability.adapters.api import APIError
from tiangong_ai_for_sustainability.adapters.api.world_bank import (
    _VERIFICATION_INDICATOR,
    WorldBankAdapter,
    WorldBankClient,
)


def test_world_bank_adapter_verify_success():
    metadata = {"total": 1}
    entry = {
        "id": _VERIFICATION_INDICATOR,
        "name": "CO2 emissions (metric tons per capita)",
        "source": {"value": "World Bank Open Data"},
    }
    client = MagicMock()
    client.fetch_indicator.return_value = (metadata, entry)
    adapter = WorldBankAdapter(client=client)

    result = adapter.verify()

    assert result.success is True
    assert result.details["indicator_id"] == _VERIFICATION_INDICATOR
    assert "World Bank API reachable" in result.message
    client.fetch_indicator.assert_called_once_with(_VERIFICATION_INDICATOR, per_page=1)


def test_world_bank_adapter_verify_failure():
    client = MagicMock()
    client.fetch_indicator.side_effect = APIError("boom")
    adapter = WorldBankAdapter(client=client)

    result = adapter.verify()

    assert result.success is False
    assert "verification failed" in result.message.lower()


def test_world_bank_client_fetch_indicator(monkeypatch):
    def fake_get_json(self, path, *, params):
        assert path == f"/indicator/{_VERIFICATION_INDICATOR}"
        assert params["format"] == "json"
        assert params["per_page"] == 1
        return [
            {"page": 1, "total": 1},
            [
                {
                    "id": _VERIFICATION_INDICATOR,
                    "name": "CO2 emissions (metric tons per capita)",
                }
            ],
        ]

    monkeypatch.setattr(WorldBankClient, "_get_json", fake_get_json, raising=False)
    client = WorldBankClient()

    metadata, entry = client.fetch_indicator(_VERIFICATION_INDICATOR)

    assert metadata["total"] == 1
    assert entry["id"] == _VERIFICATION_INDICATOR
