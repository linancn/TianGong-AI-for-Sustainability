"""
Utilities for loading Model Context Protocol (MCP) server configurations.

The helpers translate secret entries into strongly typed connection settings that the
rest of the codebase can share. Secrets are expected to follow the structure used in
``.secrets/secrets.toml`` where each MCP server is represented by a top-level table::

    [tiangong_ai_remote]
    transport = "streamable_http"
    service_name = "tiangong_ai_remote"
    url = "https://mcp.tiangong.earth/mcp"
    api_key = "<TOKEN>"
    api_key_header = "Authorization"  # optional, defaults to Authorization
    api_key_prefix = "Bearer"         # optional, defaults to Bearer for Authorization
    timeout = 30

Nested tables (``[section.headers]``) are treated as additional headers and merged with
the authentication header.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from ..config import SecretsBundle

SUPPORTED_TRANSPORTS = {"streamable_http"}
DEFAULT_TIMEOUT_SECONDS = 30.0


def _clean_secret(value: Any) -> Optional[str]:
    """Return a normalised secret value or ``None`` if the placeholder is empty."""

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("<") and text.endswith(">"):
        # Convention used in secrets.example files to mark placeholders.
        return None
    return text


def _string_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_headers(section: Mapping[str, Any]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    raw_headers = section.get("headers")
    if isinstance(raw_headers, Mapping):
        for key, raw_value in raw_headers.items():
            if raw_value is None:
                continue
            headers[str(key)] = str(raw_value)
    return headers


@dataclass(slots=True)
class MCPServerConfig:
    """Parsed configuration block describing an MCP server."""

    source_id: str
    service_name: str
    url: str
    transport: str = "streamable_http"
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    api_key: Optional[str] = None
    api_key_header: Optional[str] = "Authorization"
    api_key_prefix: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    requires_api_key: bool = True

    def resolved_headers(self) -> Dict[str, str]:
        """
        Build the HTTP header map used when opening the MCP connection.
        """

        resolved: Dict[str, str] = dict(self.headers)
        if self.api_key and self.api_key_header:
            header_name = self.api_key_header
            prefix = self.api_key_prefix
            if prefix is None and header_name.lower() == "authorization":
                prefix = "Bearer"
            value = f"{prefix} {self.api_key}" if prefix else self.api_key
            resolved[header_name] = value
        return resolved

    def connection_payload(self) -> Dict[str, Any]:
        """
        Return the dictionary passed to transport-specific clients.
        """

        payload: Dict[str, Any] = {"transport": self.transport, "url": self.url}
        headers = self.resolved_headers()
        if headers:
            payload["headers"] = headers
        if self.timeout and self.timeout > 0:
            payload["timeout"] = float(self.timeout)
        return payload


def load_mcp_server_configs(
    secrets: SecretsBundle,
    *,
    env: Mapping[str, str] | None = None,
) -> Dict[str, MCPServerConfig]:
    """
    Parse MCP server definitions from the provided secrets bundle.

    Parameters
    ----------
    secrets:
        Loaded secrets bundle.
    env:
        Optional environment mapping used for resolving ``api_key_env`` overrides.

    Returns
    -------
    dict
        Mapping of secret section name to :class:`MCPServerConfig`.
    """

    env_map: Mapping[str, str] = env or os.environ
    results: Dict[str, MCPServerConfig] = {}
    for section_name, raw_section in secrets.data.items():
        if not isinstance(raw_section, Mapping):
            continue

        transport = _string_or_none(raw_section.get("transport")) or "streamable_http"
        if transport not in SUPPORTED_TRANSPORTS:
            continue

        url = _string_or_none(raw_section.get("url"))
        if not url:
            continue

        service_name = _string_or_none(raw_section.get("service_name")) or section_name
        timeout_raw = raw_section.get("timeout")
        timeout = DEFAULT_TIMEOUT_SECONDS
        if isinstance(timeout_raw, (int, float)) and timeout_raw > 0:
            timeout = float(timeout_raw)
        elif isinstance(timeout_raw, str):
            try:
                parsed = float(timeout_raw)
                if parsed > 0:
                    timeout = parsed
            except ValueError:
                pass

        api_key = _clean_secret(raw_section.get("api_key"))
        api_key_env = _string_or_none(raw_section.get("api_key_env") or raw_section.get("api_key_env_var"))
        if not api_key and api_key_env:
            env_value = env_map.get(api_key_env)
            api_key = _clean_secret(env_value)

        api_key_header = _string_or_none(raw_section.get("api_key_header")) or "Authorization"
        api_key_prefix = _string_or_none(raw_section.get("api_key_prefix") or raw_section.get("authorization_scheme") or raw_section.get("auth_scheme"))
        requires_api_key = bool(raw_section.get("requires_api_key", True))
        headers = _extract_headers(raw_section)

        config = MCPServerConfig(
            source_id=section_name,
            service_name=service_name,
            transport=transport,
            url=url,
            timeout=timeout,
            api_key=api_key,
            api_key_header=api_key_header,
            api_key_prefix=api_key_prefix,
            headers=headers,
            requires_api_key=requires_api_key,
        )
        results[section_name] = config

    return results


__all__ = ["MCPServerConfig", "load_mcp_server_configs"]
