from __future__ import annotations

from types import SimpleNamespace

from tiangong_ai_for_sustainability.adapters.tools.remote_mcp import RemoteMCPAdapter
from tiangong_ai_for_sustainability.core.mcp_config import MCPServerConfig


class DummyClient:
    def __init__(self, configs):
        self.configs = configs
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True

    def list_tools(self, service_name: str):
        assert service_name in self.configs, "service name not passed to client"
        return [SimpleNamespace(name="tool_a"), SimpleNamespace(name="tool_b")]


def test_remote_mcp_adapter_requires_api_key():
    config = MCPServerConfig(
        source_id="tiangong_ai_remote",
        service_name="tiangong_ai_remote",
        url="https://example.com/mcp",
        api_key=None,
        requires_api_key=True,
    )
    adapter = RemoteMCPAdapter(config=config, client_factory=lambda mapping: DummyClient(mapping))
    result = adapter.verify()
    assert result.success is False
    assert "requires an API key" in result.message


def test_remote_mcp_adapter_verify_success():
    config = MCPServerConfig(
        source_id="tiangong_ai_remote",
        service_name="tiangong_ai_remote",
        url="https://example.com/mcp",
        api_key="token",
        requires_api_key=True,
    )
    created_mapping = {}

    def factory(mapping):
        created_mapping.update(mapping)
        return DummyClient(mapping)

    adapter = RemoteMCPAdapter(config=config, client_factory=factory)
    result = adapter.verify()
    assert result.success is True
    assert "2 tool" in result.message
    assert created_mapping["tiangong_ai_remote"] is config
