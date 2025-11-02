from __future__ import annotations

from tiangong_ai_for_sustainability.config import OpenAISettings, SecretsBundle
from tiangong_ai_for_sustainability.core.mcp import MCPServerConfig, load_mcp_server_configs


def build_bundle(data: dict[str, dict[str, object]]) -> SecretsBundle:
    return SecretsBundle(source_path=None, data=data, openai=OpenAISettings())


def test_load_mcp_server_configs_parses_headers():
    secrets = build_bundle(
        {
            "tiangong_ai_remote": {
                "transport": "streamable_http",
                "service_name": "tg_ai",
                "url": "https://example.com/mcp",
                "api_key": "secret-token",
                "api_key_header": "x-api-key",
                "timeout": 45,
                "headers": {"X-Extra": "value"},
            },
            "tiangong_lca_remote": {
                "transport": "streamable_http",
                "url": "https://example.com/other",
                "api_key": "<PLACEHOLDER>",
                "requires_api_key": True,
            },
        }
    )

    configs = load_mcp_server_configs(secrets)
    assert set(configs) == {"tiangong_ai_remote", "tiangong_lca_remote"}

    ai_config = configs["tiangong_ai_remote"]
    assert isinstance(ai_config, MCPServerConfig)
    assert ai_config.service_name == "tg_ai"
    headers = ai_config.resolved_headers()
    assert headers["x-api-key"] == "secret-token"
    assert headers["X-Extra"] == "value"
    payload = ai_config.connection_payload()
    assert payload["url"] == "https://example.com/mcp"
    assert payload["timeout"] == 45.0

    lca_config = configs["tiangong_lca_remote"]
    assert lca_config.api_key is None
    assert lca_config.requires_api_key is True
    assert lca_config.resolved_headers() == {}


def test_load_mcp_server_configs_reads_env(monkeypatch):
    env = {"TG_REMOTE_KEY": "env-secret"}
    monkeypatch.setenv("TG_REMOTE_KEY", env["TG_REMOTE_KEY"])

    secrets = build_bundle(
        {
            "tiangong_ai_remote": {
                "transport": "streamable_http",
                "url": "https://example.com/mcp",
                "api_key_env": "TG_REMOTE_KEY",
            }
        }
    )

    configs = load_mcp_server_configs(secrets)
    config = configs["tiangong_ai_remote"]
    # Authorization header defaults to Bearer prefix
    headers = config.resolved_headers()
    assert headers["Authorization"] == "Bearer env-secret"
