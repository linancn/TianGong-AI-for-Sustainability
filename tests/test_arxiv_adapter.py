from __future__ import annotations

from tiangong_ai_for_sustainability.adapters.api.arxiv import ArxivAdapter, ArxivAPIError


def test_arxiv_adapter_verify_success():
    class DummyClient:
        def fetch_by_id(self, arxiv_id: str):
            assert arxiv_id == "1707.08567"
            return {
                "arxiv_id": arxiv_id,
                "title": "Mastering the Game of Go",
                "published": "2016-10-18T00:00:00",
            }

    adapter = ArxivAdapter(client=DummyClient())

    result = adapter.verify()

    assert result.success is True
    assert result.details["sample_id"] == "1707.08567"
    assert result.details["sample_title"] == "Mastering the Game of Go"


def test_arxiv_adapter_verify_failure():
    class FailingClient:
        def fetch_by_id(self, arxiv_id: str):
            raise ArxivAPIError("boom")

    adapter = ArxivAdapter(client=FailingClient())

    result = adapter.verify()

    assert result.success is False
    assert "boom" in result.message
