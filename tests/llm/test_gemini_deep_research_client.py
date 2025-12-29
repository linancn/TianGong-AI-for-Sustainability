from __future__ import annotations

import httpx
import pytest

from tiangong_ai_for_sustainability.config import GeminiSettings, OpenAISettings, SecretsBundle
from tiangong_ai_for_sustainability.llm.gemini_deep_research import GeminiDeepResearchClient, GeminiDeepResearchError


class StubHTTPClient:
    def __init__(self, get_payloads: list[dict[str, object]] | None = None) -> None:
        self.posts: list[dict[str, object]] = []
        self.gets: list[dict[str, object]] = []
        self._get_payloads = list(get_payloads or [])

    def post(self, url: str, *, headers=None, json=None, timeout=None):  # type: ignore[no-untyped-def]
        self.posts.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"id": "interactions/123", "status": "running"}, request=request)

    def get(self, url: str, *, headers=None, timeout=None):  # type: ignore[no-untyped-def]
        payload = self._get_payloads.pop(0) if self._get_payloads else {"id": "interactions/123", "status": "completed"}
        self.gets.append({"url": url, "headers": headers, "timeout": timeout})
        request = httpx.Request("GET", url)
        return httpx.Response(200, json=payload, request=request)


def _build_client(http_client: StubHTTPClient | None = None, settings: GeminiSettings | None = None) -> GeminiDeepResearchClient:
    secrets = SecretsBundle(source_path=None, data={}, openai=OpenAISettings(), gemini=GeminiSettings())
    return GeminiDeepResearchClient(
        settings=settings or GeminiSettings(api_key="abc123"),
        secrets=secrets,
        http_client=http_client or StubHTTPClient(),
    )


def test_start_research_builds_payload(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    http_client = StubHTTPClient()
    client = _build_client(http_client=http_client, settings=GeminiSettings(api_key="abc123"))

    result = client.start_research("Research the impact of AI on renewable energy", file_search_stores=("store-a",))

    assert result["interaction_id"] == "interactions/123"
    assert len(http_client.posts) == 1
    payload = http_client.posts[0]
    assert payload["url"].endswith("/v1beta/interactions")
    assert payload["headers"]["x-goog-api-key"] == "abc123"
    assert payload["json"]["background"] is True
    assert payload["json"]["store"] is True
    assert payload["json"]["agent"] == "deep-research-pro-preview-12-2025"
    assert payload["json"]["tools"][0]["file_search_store_names"] == ["store-a"]


def test_poll_until_complete(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    http_client = StubHTTPClient(
        get_payloads=[
            {"id": "interactions/999", "status": "in_progress"},
            {"id": "interactions/999", "status": "completed"},
        ]
    )
    client = _build_client(http_client=http_client, settings=GeminiSettings(api_key="abc123"))
    monkeypatch.setattr("tiangong_ai_for_sustainability.llm.gemini_deep_research.time.sleep", lambda _: None)

    result = client.poll_until_complete("interactions/999", interval=0.01, max_attempts=5)

    assert result["status"] == "completed"
    assert len(http_client.gets) == 2


def test_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(GeminiDeepResearchError):
        _build_client(settings=GeminiSettings(api_key=None))


def test_start_research_rejects_empty_prompt(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = _build_client(settings=GeminiSettings(api_key="abc123"))

    with pytest.raises(GeminiDeepResearchError):
        client.start_research("   ")
