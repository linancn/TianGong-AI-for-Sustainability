#!/usr/bin/env python3
"""
CLI shim around :class:`tiangong_ai_for_sustainability.deep_research.DeepResearchClient`.

Before running ensure ``OPENAI_API_KEY`` is exported.

Example usage::

    uv run python scripts/examples/run_deep_research.py \\
        "How can AI improve municipal recycling rates?" \\
        --context "Focus on medium-sized European cities." \\
        --follow-up "List the highest impact data integrations." \\
        --tag pilot \\
        --mcp-server server_label=local-fs,server_url=http://127.0.0.1:3001
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Iterable, List

from tiangong_ai_for_sustainability.deep_research import (
    DeepResearchClient,
    DeepResearchConfig,
    MCPServerConfig,
    ResearchPrompt,
)


def parse_mcp_server(raw: str) -> MCPServerConfig:
    """
    Parse key=value pairs describing an MCP server configuration.

    Required keys: ``server_label`` and ``server_url``.
    Optional keys: ``server_description``, ``authorization``, ``allowed_tools``,
    ``require_manual_approval`` (truthy values), ``connector_id``.
    """

    pieces = {}
    for part in raw.split(","):
        if "=" not in part:
            raise ValueError(f"Expected key=value pairs in --mcp-server argument, got {part!r}")
        key, value = part.split("=", 1)
        pieces[key.strip()] = value.strip()

    try:
        server_label = pieces.pop("server_label")
        server_url = pieces.pop("server_url")
    except KeyError as exc:
        raise ValueError("Both server_label and server_url are required for --mcp-server") from exc

    config = MCPServerConfig(
        server_label=server_label,
        server_url=server_url,
        server_description=pieces.pop("server_description", None),
        authorization=pieces.pop("authorization", None),
        connector_id=pieces.pop("connector_id", None),
    )

    if "allowed_tools" in pieces:
        config.allowed_tools = tuple(item.strip() for item in pieces.pop("allowed_tools").split("|") if item.strip())
    if "require_manual_approval" in pieces:
        config.require_manual_approval = pieces.pop("require_manual_approval").lower() in {"1", "true", "yes"}
    if "headers" in pieces:
        header_pairs = {}
        for header in pieces.pop("headers").split("|"):
            if ":" not in header:
                raise ValueError("headers value must be colon-separated HTTP header definitions.")
            name, header_value = header.split(":", 1)
            header_pairs[name.strip()] = header_value.strip()
        config.custom_headers = header_pairs

    if pieces:
        keys = ", ".join(sorted(pieces.keys()))
        raise ValueError(f"Unsupported keys in --mcp-server argument: {keys}")
    return config


def collect_mcp_servers(arguments: Iterable[str]) -> List[MCPServerConfig]:
    """Convert CLI arguments into MCP server definitions."""

    servers: List[MCPServerConfig] = []
    for raw in arguments:
        servers.append(parse_mcp_server(raw))
    return servers


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an OpenAI Deep Research task.")
    parser.add_argument("question", help="Primary research question.")
    parser.add_argument("--context", help="Optional supporting context injected into the prompt.")
    parser.add_argument("--follow-up", dest="follow_ups", action="append", default=[], help="Additional follow-up questions.")
    parser.add_argument("--instruction", help="Optional system-level instruction string.")
    parser.add_argument("--tag", dest="tags", action="append", default=[], help="Tag metadata to embed in the response metadata.")
    parser.add_argument("--temperature", type=float, help="Override sampling temperature.")
    parser.add_argument("--max-output-tokens", type=int, help="Hard cap for generated tokens.")
    parser.add_argument("--stream", action="store_true", help="Enable streaming mode.")
    parser.add_argument("--background", action="store_true", help="Request background execution.")
    parser.add_argument("--json", action="store_true", help="Emit the full JSON response.")
    parser.add_argument("--mcp-server", dest="mcp_servers", action="append", default=[], help="Register an MCP server (key=value pairs).")

    args = parser.parse_args(argv)

    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY must be set before invoking Deep Research.")

    prompt = ResearchPrompt(question=args.question, context=args.context, follow_up_questions=args.follow_ups)

    config = DeepResearchConfig(
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        enable_background_mode=args.background,
    )
    client = DeepResearchClient(config=config)

    servers = collect_mcp_servers(args.mcp_servers)

    if args.background:
        response = client.run_background(prompt, instructions=args.instruction, tags=args.tags, mcp_servers=servers)
        print(json.dumps({"response_id": response.id, "status": response.status}, indent=2))
        return 0

    result = client.run(
        prompt,
        instructions=args.instruction,
        tags=args.tags,
        mcp_servers=servers,
        stream=args.stream,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.output_text or "[No textual output available]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
