"""
Adapter for the AntV MCP chart server.

The server is distributed via npm (`@antv/mcp-server-chart`) and can expose
multiple transports. This adapter focuses on the SSE endpoint because it is the
simplest to probe from Python without a full MCP client.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from logging import LoggerAdapter
from typing import Optional

import httpx

from ..base import AdapterError, DataSourceAdapter, VerificationResult
from ...core.logging import get_logger

DEFAULT_ENDPOINT = "http://127.0.0.1:1122/mcp"


@dataclass(slots=True)
class ChartMCPAdapter(DataSourceAdapter):
    """Verify availability of the AntV MCP chart server."""

    source_id: str = "chart_mcp_server"
    endpoint: str = DEFAULT_ENDPOINT
    transport: str = "streamable"
    logger: LoggerAdapter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__, extra={"transport": self.transport})

    def _resolve_endpoint(self) -> str:
        env_override = os.getenv("TIANGONG_CHART_MCP_ENDPOINT")
        if env_override:
            return env_override
        return self.endpoint

    def verify(self) -> VerificationResult:
        node_exists = shutil.which("node") is not None or shutil.which("npx") is not None
        if not node_exists:
            self.logger.warning("Node.js tooling not found; MCP chart server unavailable")
            return VerificationResult(
                success=False,
                message=("Node.js (with npx) is not installed or not on PATH. Install Node.js " "to run the AntV MCP chart server. See https://nodejs.org/"),
                details={"requirement": "nodejs"},
            )

        endpoint = self._resolve_endpoint()
        self.logger.debug("Verifying MCP chart server", extra={"endpoint": endpoint})
        try:
            timeout = httpx.Timeout(connect=3.0, read=3.0, write=3.0, pool=None)
            headers = {"Accept": "application/json"}
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(endpoint, headers=headers)
        except httpx.RequestError as exc:
            self.logger.warning(
                "Failed to reach MCP chart server",
                extra={"endpoint": endpoint, "error": str(exc)},
            )
            return VerificationResult(
                success=False,
                message=(
                    f"Unable to reach MCP chart server at {endpoint}. " "Start it with `npx -y @antv/mcp-server-chart --transport streamable` " "or configure TIANGONG_CHART_MCP_ENDPOINT."
                ),
                details={"error": str(exc), "endpoint": endpoint},
            )

        status = response.status_code
        if status in (200, 204):
            content_type = (response.headers.get("content-type") or "").lower()
            if not any(token in content_type for token in ("application/json", "application/stream+json", "application/octet-stream")):
                self.logger.warning(
                    "MCP chart server returned unexpected content type",
                    extra={"endpoint": endpoint, "content_type": content_type},
                )
                return VerificationResult(
                    success=False,
                    message=(f"Endpoint {endpoint} responded but returned unexpected content-type " f"'{content_type}'. Ensure the server is running with `--transport streamable`."),
                    details={"content_type": content_type, "endpoint": endpoint},
                )
        elif status in (400, 404, 405):
            self.logger.debug(
                "MCP chart server reachable with non-2xx status",
                extra={"endpoint": endpoint, "status": status},
            )
            return VerificationResult(
                success=True,
                message=(f"MCP chart server reachable at {endpoint} (HTTP {status}). " "Streamable transport expects POST requests; this status is acceptable for connectivity checks."),
                details={"endpoint": endpoint, "transport": self.transport, "status": status},
            )
        else:
            self.logger.warning(
                "MCP chart server responded with unexpected status",
                extra={"endpoint": endpoint, "status": status},
            )
            return VerificationResult(
                success=False,
                message=(f"MCP chart server responded with HTTP {status} at {endpoint}. " "Verify the server is running with streamable transport."),
                details={"status": status, "endpoint": endpoint},
            )

        self.logger.info("MCP chart server verified", extra={"endpoint": endpoint})
        return VerificationResult(
            success=True,
            message=f"MCP chart server reachable at {endpoint}.",
            details={"endpoint": endpoint, "transport": self.transport},
        )

    def renderable(self) -> bool:
        """
        Placeholder hint indicating that chart rendering is possible once the server is reachable.

        Real rendering is orchestrated via MCP clients. This helper can be used by services to
        signal that downstream operations may proceed.
        """

        result = self.verify()
        return result.success
