from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tiangong_ai_for_sustainability.workflows.simple import run_simple_workflow


class DummyServices:
    def __init__(self) -> None:
        self._un = SimpleNamespace(
            list_goals=lambda: [
                {"code": "7", "title": "Affordable and Clean Energy", "description": "Ensure access to affordable, reliable, sustainable and modern energy for all."},
                {"code": "9", "title": "Industry, Innovation and Infrastructure", "description": "Build resilient infrastructure."},
            ]
        )
        self._github = SimpleNamespace(
            search_repositories=lambda topic, per_page: {
                "items": [
                    {"full_name": "demo/a", "stargazers_count": 42, "html_url": "https://github.com/demo/a", "description": "Repo A"},
                    {"full_name": "demo/b", "stargazers_count": 17, "html_url": "https://github.com/demo/b", "description": "Repo B"},
                ]
            }
        )
        self._scholar = SimpleNamespace(
            search_papers=lambda topic, limit, fields: {
                "data": [
                    {"title": "Paper A", "year": 2024, "url": "https://example.com/paper-a", "abstract": "Abstract A", "authors": [{"name": "Alice"}]},
                    {"title": "Paper B", "year": 2023, "url": "https://example.com/paper-b", "abstract": "Abstract B", "authors": [{"name": "Bob"}]},
                ]
            }
        )

    # Client factories
    def un_sdg_client(self):
        return self._un

    def github_topics_client(self):
        return self._github

    def semantic_scholar_client(self):
        return self._scholar

    def osdg_client(self):
        raise RuntimeError("Not used in tests")

    def chart_mcp_endpoint(self) -> str:
        return "http://localhost:1122/mcp"

    def get_carbon_intensity(self, location: str):
        return {"provider": "WattTime", "location": location, "carbon_intensity": 312, "units": "gCO2e/kWh", "datetime": "2025-11-01T07:30:00Z"}


@pytest.fixture()
def dummy_services():
    return DummyServices()


def test_run_simple_workflow(tmp_path, monkeypatch, dummy_services):
    report_path = tmp_path / "report.md"
    chart_path = tmp_path / "chart.png"

    # Avoid real MCP calls by returning a fake image URL
    monkeypatch.setattr(
        "tiangong_ai_for_sustainability.workflows.simple._call_chart_tool",
        lambda endpoint, data, topic: "https://example.com/chart.png",
    )

    class DummyHTTPClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            class DummyPostResponse:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"result": {"content": [{"type": "text", "text": "https://example.com/chart.png"}]}}

            return DummyPostResponse()

        def get(self, url):
            class DummyGetResponse:
                content = b"fake-image"

                def raise_for_status(self):
                    pass

            return DummyGetResponse()

    monkeypatch.setattr("httpx.Client", DummyHTTPClient)

    artifacts = run_simple_workflow(
        dummy_services,
        topic="sustainable software engineering",
        report_path=report_path,
        chart_path=chart_path,
    )

    assert report_path.exists()
    report_text = report_path.read_text("utf-8")
    assert "Sustainability Snapshot" in report_text
    assert "Top repositories chart" in report_text

    assert artifacts.chart_path == chart_path
    assert chart_path.exists()
    assert chart_path.read_bytes() == b"fake-image"

