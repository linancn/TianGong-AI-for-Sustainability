"""
Adapter for remote MCP services defined via secrets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import LoggerAdapter
from typing import Callable, Mapping, Sequence

from ...core.logging import get_logger
from ...core.mcp_client import MCPToolClient
from ...core.mcp_config import MCPServerConfig
from ..base import DataSourceAdapter, VerificationResult

ClientFactory = Callable[[Mapping[str, MCPServerConfig]], MCPToolClient]


@dataclass(slots=True)
class RemoteMCPAdapter(DataSourceAdapter):
    """Verify connectivity to a remote MCP server."""

    config: MCPServerConfig
    client_factory: ClientFactory = MCPToolClient
    source_id: str = field(init=False)
    logger: LoggerAdapter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.source_id = self.config.source_id
        self.logger = get_logger(
            self.__class__.__name__,
            extra={"service_name": self.config.service_name, "source_id": self.config.source_id},
        )

    def verify(self) -> VerificationResult:
        if self.config.requires_api_key and not self.config.api_key:
            self.logger.warning("Remote MCP server missing API key", extra={"source_id": self.config.source_id})
            return VerificationResult(
                success=False,
                message=(f"MCP server '{self.config.source_id}' requires an API key. " "Add the credential to .secrets/secrets.toml or configure the referenced environment variable."),
                details={"source_id": self.config.source_id, "service_name": self.config.service_name},
            )

        client = self.client_factory({self.config.service_name: self.config})
        try:
            with client:
                tools = client.list_tools(self.config.service_name)
        except Exception as exc:  # pragma: no cover - network and credential issues
            self.logger.warning(
                "Remote MCP verification failed",
                extra={"error": str(exc), "service_name": self.config.service_name},
            )
            return VerificationResult(
                success=False,
                message=f"Failed to connect to MCP server '{self.config.service_name}': {exc}",
                details={
                    "service_name": self.config.service_name,
                    "source_id": self.config.source_id,
                    "url": self.config.url,
                },
            )

        tool_names = _tool_names(tools)
        self.logger.info(
            "Remote MCP server reachable",
            extra={"service_name": self.config.service_name, "tool_count": len(tool_names)},
        )
        return VerificationResult(
            success=True,
            message=(f"MCP server '{self.config.service_name}' reachable. " f"Discovered {len(tool_names)} tool(s)."),
            details={
                "service_name": self.config.service_name,
                "source_id": self.config.source_id,
                "url": self.config.url,
                "tool_count": len(tool_names),
                "tools": tool_names,
            },
        )


def _tool_names(tools: Sequence[object]) -> list[str]:
    names: list[str] = []
    for tool in tools:
        name = getattr(tool, "name", None)
        if isinstance(name, str) and name:
            names.append(name)
    return names


__all__ = ["RemoteMCPAdapter"]
