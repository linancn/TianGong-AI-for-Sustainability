#!/usr/bin/env python
"""
Collect focused corpora from the TianGong remote MCP service.

This helper targets under-represented concepts highlighted in recent analyses,
including SAFER (safe and fair Earth system boundaries) and sustainable
nanotechnology. The script emits compact JSON datasets that can be reused for
replication studies or downstream adapters.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping

from tiangong_ai_for_sustainability.config import load_secrets
from tiangong_ai_for_sustainability.core.mcp_client import MCPToolClient
from tiangong_ai_for_sustainability.core.mcp_config import load_mcp_server_configs


@dataclass(frozen=True)
class CorpusConfig:
    concept_id: str
    label: str
    query: str
    notes: str


CORPUS_PRESETS: Mapping[str, CorpusConfig] = {
    "safer": CorpusConfig(
        concept_id="safer",
        label="Safe and Fair Earth System Boundaries (SAFER)",
        query='("safe and fair earth system boundaries" OR SAFER) AND ("planetary boundaries" OR "life cycle assessment" OR LCA)',
        notes="Targets literature discussing SAFER indicators within LCA and sustainability contexts.",
    ),
    "nanotechnology": CorpusConfig(
        concept_id="sustainable_nanotechnology",
        label="Sustainable Nanotechnology",
        query='("sustainable nanotechnology" OR "nanotechnology sustainability") AND ("life cycle assessment" OR LCA)',
        notes="Captures sustainable nanotechnology assessments with explicit LCA framing.",
    ),
}

DEFAULT_TOP_K = 40
DEFAULT_EXT_K = 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--concept",
        choices=sorted(CORPUS_PRESETS.keys()),
        default="safer",
        help="Concept preset to collect (default: safer).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Number of top results to request from the MCP search tool (default: %(default)s).",
    )
    parser.add_argument(
        "--ext-k",
        type=int,
        default=DEFAULT_EXT_K,
        help="Number of adjacent chunks to include before/after each hit (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".cache/tiangong/corpora/placeholder.json"),
        help="Destination JSON path (default: .cache/tiangong/corpora/<concept>.json).",
    )
    parser.add_argument(
        "--service-name",
        default="tiangong_ai_remote",
        help="MCP service name configured in secrets (default: %(default)s).",
    )
    return parser.parse_args()


def _resolve_output_path(path: Path, concept_id: str) -> Path:
    if path.name == "placeholder.json":
        return path.with_name(f"{concept_id}.json")
    return path


def collect_corpus(config: CorpusConfig, *, service_name: str, top_k: int, ext_k: int, output_path: Path) -> Path:
    secrets = load_secrets(strict=True)
    configs = load_mcp_server_configs(secrets)
    if service_name not in configs:
        raise RuntimeError(f"MCP service '{service_name}' not configured in secrets.")

    mcp_config = configs[service_name]
    with MCPToolClient([mcp_config]) as client:
        payload, attachments = client.invoke_tool(
            mcp_config.service_name,
            "Search_Sci_Tool",
            {
                "query": config.query,
                "topK": max(1, min(top_k, 50)),
                "extK": max(0, min(ext_k, 10)),
            },
        )

    try:
        records = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(f"MCP response was not valid JSON: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_payload: Dict[str, object] = {
        "concept_id": config.concept_id,
        "label": config.label,
        "notes": config.notes,
        "query": config.query,
        "topK": top_k,
        "extK": ext_k,
        "record_count": len(records),
        "records": records,
        "attachments": attachments or [],
    }
    output_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> int:
    args = parse_args()
    preset = CORPUS_PRESETS[args.concept]
    output_path = _resolve_output_path(args.output, preset.concept_id)
    try:
        final_path = collect_corpus(
            preset,
            service_name=args.service_name,
            top_k=args.top_k,
            ext_k=args.ext_k,
            output_path=output_path,
        )
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        print(f"[collect-mcp-corpus] Error: {exc}", file=sys.stderr)
        return 1

    print(f"[collect-mcp-corpus] Saved {preset.label} corpus to {final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
