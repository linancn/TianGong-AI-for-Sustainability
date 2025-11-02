from __future__ import annotations

from types import SimpleNamespace

import pytest

from tiangong_ai_for_sustainability.config import OpenAISettings, SecretsBundle
from tiangong_ai_for_sustainability.deep_research import DeepResearchClient, DeepResearchConfig, ResearchPrompt


class StubResponses:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, object], object | None]] = []

    def create(self, *, extra_body=None, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append((kwargs, extra_body))
        return SimpleNamespace(
            id="resp_123",
            output=[SimpleNamespace(type="output_text", text="Answer summary")],
            model_dump=lambda: {"id": "resp_123"},
        )


def build_client() -> tuple[DeepResearchClient, StubResponses]:
    secrets = SecretsBundle(source_path=None, data={}, openai=OpenAISettings(api_key="test", default_model="gpt-unit"))
    responses = StubResponses()
    stub_openai = SimpleNamespace(responses=responses)
    client = DeepResearchClient(client=stub_openai, secrets=secrets, config=DeepResearchConfig())
    return client, responses


def test_deep_research_run_includes_tools_and_metadata():
    client, responses = build_client()
    prompt = ResearchPrompt(question="How can AI reduce carbon emissions?", context="Focus on software efficiency.")

    result = client.run(prompt, tags=["unit"], code_interpreter=True)

    assert result.output_text == "Answer summary"
    assert len(responses.calls) == 1
    kwargs, extra_body = responses.calls[0]
    assert extra_body is None
    assert kwargs["model"] == "gpt-unit"
    assert kwargs["metadata"]["tags"] == ["unit"]
    tools = kwargs.get("tools", [])
    assert any(tool.get("type") == "web_search_preview" for tool in tools)
    assert any(tool.get("type") == "code_interpreter" for tool in tools)
    message_block = kwargs["input"][0]["content"][0]["text"]
    assert "How can AI reduce carbon emissions?" in message_block


def test_deep_research_run_requires_data_source():
    client, _ = build_client()

    with pytest.raises(ValueError, match="require at least one data source tool"):
        client.run("What is sustainability?", use_web_search=False)
