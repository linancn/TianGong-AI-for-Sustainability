from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tiangong_ai_for_sustainability.adapters import AdapterError
from tiangong_ai_for_sustainability.config import OpenAISettings, SecretsBundle
from tiangong_ai_for_sustainability.core import (
    DataSourceDescriptor,
    DataSourcePriority,
    DataSourceRegistry,
    DataSourceStatus,
    ExecutionContext,
    ExecutionOptions,
)
from tiangong_ai_for_sustainability.services.research import ResearchServices


def build_context(secrets_data: dict[str, dict[str, object]], enabled_sources: list[str]) -> ExecutionContext:
    secrets = SecretsBundle(source_path=None, data=secrets_data, openai=OpenAISettings())
    context = ExecutionContext.build_default(
        enabled_sources=enabled_sources,
        options=ExecutionOptions(),
        secrets=secrets,
    )
    return context


def register_remote(registry: DataSourceRegistry, source_id: str) -> None:
    registry.register(
        DataSourceDescriptor(
            source_id=source_id,
            name=source_id,
            category="automation",
            priority=DataSourcePriority.P2,
            description="Remote MCP",
            requires_credentials=True,
            status=DataSourceStatus.TRIAL,
        )
    )


def test_research_services_mcp_helpers(monkeypatch):
    registry = DataSourceRegistry()
    register_remote(registry, "tiangong_ai_remote")

    secrets_data = {
        "tiangong_ai_remote": {
            "transport": "streamable_http",
            "service_name": "tiangong_ai_remote",
            "url": "https://example.com/mcp",
            "api_key": "token",
        }
    }
    context = build_context(secrets_data, ["tiangong_ai_remote"])

    mock_client = MagicMock()
    mock_client.list_tools.return_value = [SimpleNamespace(name="alpha", description="first")]
    mock_client.invoke_tool.return_value = ({"ok": True}, None)

    with patch("tiangong_ai_for_sustainability.services.research.MCPToolClient", return_value=mock_client):
        services = ResearchServices(registry=registry, context=context)

        tools = services.list_mcp_tools("tiangong_ai_remote")
        assert tools == [{"name": "alpha", "description": "first"}]

        payload, attachments = services.invoke_mcp_tool("tiangong_ai_remote", "alpha_tool", {"value": 1})
        assert payload == {"ok": True}
        assert attachments is None

    mock_client.list_tools.assert_called_once()
    mock_client.invoke_tool.assert_called_once_with("tiangong_ai_remote", "alpha_tool", {"value": 1})


def test_research_services_invoke_requires_credentials():
    registry = DataSourceRegistry()
    register_remote(registry, "tiangong_ai_remote")

    secrets_data = {
        "tiangong_ai_remote": {
            "transport": "streamable_http",
            "service_name": "tiangong_ai_remote",
            "url": "https://example.com/mcp",
            "requires_api_key": True,
        }
    }
    context = build_context(secrets_data, ["tiangong_ai_remote"])
    services = ResearchServices(registry=registry, context=context)

    try:
        services.invoke_mcp_tool("tiangong_ai_remote", "alpha_tool", {})
    except AdapterError as exc:
        assert "requires an API key" in str(exc)
    else:  # pragma: no cover - safety
        raise AssertionError("AdapterError expected when credentials missing")
