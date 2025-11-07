from __future__ import annotations

from unittest.mock import patch

from tiangong_ai_for_sustainability.adapters.api.arxiv import ArxivAdapter
from tiangong_ai_for_sustainability.adapters.api.crossref import CrossrefAdapter
from tiangong_ai_for_sustainability.adapters.api.kaggle import KaggleAdapter
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


def test_resolve_adapter_kaggle(tmp_path):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.secrets.data.setdefault("kaggle", {})["username"] = "researcher"
    context.secrets.data["kaggle"]["key"] = "secret"

    with patch("tiangong_ai_for_sustainability.cli.adapters.KaggleClient") as mock_client:
        client_instance = object()
        mock_client.return_value = client_instance
        adapter = resolve_adapter("kaggle", context)

    assert isinstance(adapter, KaggleAdapter)
    assert adapter.client is client_instance
    mock_client.assert_called_once_with(username="researcher", key="secret")
