from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "integrations" / "collect_mcp_corpus.py"
SPEC = importlib.util.spec_from_file_location("collect_mcp_corpus", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - defensive
    raise RuntimeError(f"Unable to load collect_mcp_corpus module from {SCRIPT_PATH}")
corpus_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = corpus_module
SPEC.loader.exec_module(corpus_module)

CORPUS_PRESETS = corpus_module.CORPUS_PRESETS
collect_corpus = corpus_module.collect_corpus


class DummyMCPClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def invoke_tool(self, service_name, tool_name, arguments):
        payload = json.dumps(
            [
                {
                    "content": "Example SAFER aligned abstract text.",
                    "source": "[Sample SAFER Paper](https://doi.org/10.1234/demo)",
                }
            ]
        )
        attachments = [{"type": "text/csv", "description": "Example attachment"}]
        return payload, attachments


@pytest.fixture(autouse=True)
def patch_mcp(monkeypatch):
    dummy_config = SimpleNamespace(service_name="tiangong_ai_remote")

    def fake_load_secrets(strict=True):
        return SimpleNamespace(data={}, openai=None, source_path=None)

    def fake_load_configs(_secrets):
        return {"tiangong_ai_remote": dummy_config}

    monkeypatch.setattr(corpus_module, "load_secrets", fake_load_secrets)
    monkeypatch.setattr(corpus_module, "load_mcp_server_configs", fake_load_configs)
    monkeypatch.setattr(corpus_module, "MCPToolClient", DummyMCPClient)


def test_collect_corpus_writes_file(tmp_path):
    preset = CORPUS_PRESETS["safer"]
    output_path = tmp_path / "corpus.json"

    result_path = collect_corpus(
        preset,
        service_name="tiangong_ai_remote",
        top_k=10,
        ext_k=1,
        output_path=output_path,
    )

    assert result_path == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text("utf-8"))
    assert payload["concept_id"] == preset.concept_id
    assert payload["record_count"] == 1
    assert payload["records"][0]["content"].startswith("Example SAFER")
