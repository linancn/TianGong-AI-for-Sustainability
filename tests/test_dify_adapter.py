from __future__ import annotations

from unittest.mock import MagicMock

from tiangong_ai_for_sustainability.adapters.api import APIError
from tiangong_ai_for_sustainability.adapters.api.dify import DifyKnowledgeBaseAdapter


def test_dify_adapter_success():
    client = MagicMock()
    client.api_key = "secret-token"
    client.retrieve.return_value = {
        "query": {"content": "climate"},
        "records": [
            {"segment": {"content": "Chunk text", "document": {"name": "Doc 1"}}},
        ],
    }
    adapter = DifyKnowledgeBaseAdapter(client=client, dataset_id="dataset-123", test_query="climate")

    result = adapter.verify()

    assert result.success is True
    assert result.details["record_count"] == 1
    assert result.details["dataset_id"] == "dataset-123"
    assert result.details["sample_content"].startswith("Chunk text")
    assert result.details["sample_document"] == "Doc 1"
    client.retrieve.assert_called_once_with(dataset_id="dataset-123", query="climate", retrieval_model=None)


def test_dify_adapter_missing_api_key():
    client = MagicMock()
    client.api_key = None
    adapter = DifyKnowledgeBaseAdapter(client=client, dataset_id="dataset-123")

    result = adapter.verify()

    assert result.success is False
    assert "api key" in result.message.lower()


def test_dify_adapter_missing_dataset():
    client = MagicMock()
    client.api_key = "secret-token"
    adapter = DifyKnowledgeBaseAdapter(client=client, dataset_id=None)

    result = adapter.verify()

    assert result.success is False
    assert "dataset_id" in result.message


def test_dify_adapter_api_error():
    client = MagicMock()
    client.api_key = "secret-token"
    client.retrieve.side_effect = APIError("boom")
    adapter = DifyKnowledgeBaseAdapter(client=client, dataset_id="dataset-123")

    result = adapter.verify()

    assert result.success is False
    assert "verification failed" in result.message.lower()
