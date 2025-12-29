from __future__ import annotations

from tiangong_ai_for_sustainability.adapters.tools import GeminiDeepResearchAdapter
from tiangong_ai_for_sustainability.config import GeminiSettings


def test_gemini_deep_research_adapter_missing_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    adapter = GeminiDeepResearchAdapter(settings=GeminiSettings())

    result = adapter.verify()

    assert not result.success
    assert "Gemini API key is not configured" in result.message


def test_gemini_deep_research_adapter_success(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "env-token")
    settings = GeminiSettings(agent="custom-agent", api_endpoint="https://custom-endpoint.example.com")
    adapter = GeminiDeepResearchAdapter(settings=settings)

    result = adapter.verify()

    assert result.success
    assert result.details == {"agent": "custom-agent", "endpoint": "https://custom-endpoint.example.com"}
