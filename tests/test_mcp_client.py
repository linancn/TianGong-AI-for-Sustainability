from __future__ import annotations

from types import SimpleNamespace

import pytest

from tiangong_ai_for_sustainability.core.mcp import MCPServerConfig
from tiangong_ai_for_sustainability.core.mcp_client import MCPToolClient


class DummyPortal:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def call(self, func, *args, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append((func, args, kwargs))
        return func(*args, **kwargs)

    def wrap_async_context_manager(self, cm):  # type: ignore[no-untyped-def]
        return cm


class DummyPortalCM:
    def __init__(self, portal: DummyPortal) -> None:
        self.portal = portal

    def __enter__(self) -> DummyPortal:
        return self.portal

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        return False


class DummyConnection:
    def __init__(self, session) -> None:  # type: ignore[no-untyped-def]
        self.session = session
        self.closed = False

    def close(self) -> None:
        self.closed = True


def build_client(session) -> tuple[MCPToolClient, DummyPortal]:  # type: ignore[no-untyped-def]
    config = MCPServerConfig(
        source_id="svc",
        service_name="svc",
        url="https://example.com/mcp",
    )
    portal = DummyPortal()
    client = MCPToolClient.__new__(MCPToolClient)
    client._configs = {"svc": config}
    client._portal = portal
    client._portal_cm = DummyPortalCM(portal)
    client._connections = {"svc": DummyConnection(session)}
    client._closed = False
    return client, portal


def test_mcp_tool_client_list_tools_uses_portal():
    class Session:
        def list_tools(self):  # type: ignore[no-untyped-def]
            return SimpleNamespace(tools=[SimpleNamespace(name="alpha", description="first")])

    client, portal = build_client(Session())
    tools = client.list_tools("svc")

    assert len(tools) == 1
    assert tools[0].name == "alpha"
    assert portal.calls[0][0].__name__ == "list_tools"


def test_mcp_tool_client_invoke_tool_success():
    class Session:
        def list_tools(self):  # type: ignore[no-untyped-def]
            return SimpleNamespace(tools=[])

        def call_tool(self, tool_name, arguments=None):  # type: ignore[no-untyped-def]
            return SimpleNamespace(isError=False, structuredContent={"ok": True}, content=[])

    client, portal = build_client(Session())
    payload, attachments = client.invoke_tool("svc", "alpha", {"value": 1})

    assert payload == {"ok": True}
    assert attachments is None
    assert portal.calls[-1][0].__name__ == "call_tool"
    assert portal.calls[-1][1][0] == "alpha"
    assert portal.calls[-1][1][1] == {"value": 1}


def test_mcp_tool_client_invoke_tool_error():
    class Session:
        def list_tools(self):  # type: ignore[no-untyped-def]
            return SimpleNamespace(tools=[])

        def call_tool(self, tool_name, arguments=None):  # type: ignore[no-untyped-def]
            return SimpleNamespace(isError=True, structuredContent=None, content=[])

    client, _ = build_client(Session())

    with pytest.raises(RuntimeError, match="reported an error"):
        client.invoke_tool("svc", "alpha", {})
