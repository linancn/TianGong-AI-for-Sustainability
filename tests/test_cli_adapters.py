from __future__ import annotations

from tiangong_ai_for_sustainability.adapters.api.arxiv import ArxivAdapter
from tiangong_ai_for_sustainability.adapters.api.crossref import CrossrefAdapter
from tiangong_ai_for_sustainability.cli.adapters import resolve_adapter
from tiangong_ai_for_sustainability.core.context import ExecutionContext


def test_resolve_adapter_crossref(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("crossref", {})["mailto"] = "research@example.com"

    adapter = resolve_adapter("crossref", context)

    assert isinstance(adapter, CrossrefAdapter)
    assert adapter.client.mailto == "research@example.com"


def test_resolve_adapter_arxiv(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")

    adapter = resolve_adapter("arxiv", context)

    assert isinstance(adapter, ArxivAdapter)
