from tiangong_ai_for_sustainability.adapters.tools import OpenAIDeepResearchAdapter
from tiangong_ai_for_sustainability.config import OpenAISettings


def test_openai_deep_research_adapter_missing_key():
    adapter = OpenAIDeepResearchAdapter(settings=OpenAISettings())
    result = adapter.verify()
    assert not result.success
    assert "OpenAI API key is not configured" in result.message


def test_openai_deep_research_adapter_success():
    settings = OpenAISettings(
        api_key="test-key",
        deep_research_model="o4-mini-deep-research",
    )
    adapter = OpenAIDeepResearchAdapter(settings=settings)
    result = adapter.verify()
    assert result.success
    assert result.details == {"model": "o4-mini-deep-research"}
