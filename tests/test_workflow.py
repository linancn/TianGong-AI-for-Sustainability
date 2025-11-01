from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tiangong_ai_for_sustainability.workflows.deep_lca import run_deep_lca_report
from tiangong_ai_for_sustainability.workflows.lca_citations import (
    LCACitationWorkflowArtifacts,
    CitationQuestion,
    PaperRecord,
    ResearchGap,
    TrendingTopic,
    run_lca_citation_workflow,
)
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
            },
            get_paper=lambda paper_id, fields=None: {"citationCount": 160, "url": "https://example.com/enriched"},
        )
        self._openalex = SimpleNamespace(iterate_works=lambda **kwargs: [])

    # Client factories
    def un_sdg_client(self):
        return self._un

    def github_topics_client(self):
        return self._github

    def semantic_scholar_client(self):
        return self._scholar

    def openalex_client(self):
        return self._openalex

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

    def fake_render(endpoint, *, tool_name, arguments, destination, **kwargs):
        destination.write_bytes(b"fake-image")
        return True

    monkeypatch.setattr(
        "tiangong_ai_for_sustainability.workflows.simple.ensure_chart_image",
        fake_render,
    )

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


def test_run_lca_citation_workflow(tmp_path, monkeypatch, dummy_services):
    report_path = tmp_path / "lca.md"
    chart_path = tmp_path / "lca.png"
    raw_path = tmp_path / "lca.json"

    payloads = [
        {
            "id": "https://openalex.org/W1",
            "display_name": "Life cycle assessment integration of planetary boundaries and sustainable development goals",
            "publication_year": 2021,
            "cited_by_count": 150,
            "doi": "10.1111/example1",
            "ids": {"doi": "10.1111/example1"},
            "authorships": [{"author": {"display_name": "Alice Johnson"}}],
            "concepts": [
                {"display_name": "Planetary boundaries", "score": 0.7},
                {"display_name": "Sustainable development goal", "score": 0.6},
            ],
            "abstract_inverted_index": {},
            "primary_location": {"landing_page_url": "https://example.com/paper1"},
            "host_venue": {"display_name": "Journal of LCA"},
        },
        {
            "id": "https://openalex.org/W2",
            "display_name": "Advancing life cycle assessment for planetary boundaries aligned SDGs",
            "publication_year": 2023,
            "cited_by_count": 220,
            "doi": "10.1111/example2",
            "ids": {"doi": "10.1111/example2"},
            "authorships": [{"author": {"display_name": "Bob Smith"}}],
            "concepts": [
                {"display_name": "Planetary boundaries", "score": 0.8},
                {"display_name": "Lifecycle management", "score": 0.3},
            ],
            "abstract_inverted_index": {},
            "primary_location": {"landing_page_url": "https://example.com/paper2"},
            "host_venue": {"display_name": "Sustainability Science"},
        },
        {
            "id": "https://openalex.org/W3",
            "display_name": "Life cycle assessment of biodiversity-safe planetary boundary indicators for SDGs",
            "publication_year": 2024,
            "cited_by_count": 80,
            "doi": "10.1111/example3",
            "ids": {"doi": "10.1111/example3"},
            "authorships": [{"author": {"display_name": "Carol Lee"}}],
            "concepts": [
                {"display_name": "Biodiversity indicators", "score": 0.75},
                {"display_name": "Sustainable development goal", "score": 0.4},
            ],
            "abstract_inverted_index": {},
            "primary_location": {"landing_page_url": "https://example.com/paper3"},
            "host_venue": {"display_name": "Environmental Research Letters"},
        },
    ]

    dummy_services._openalex.iterate_works = lambda **kwargs: iter(payloads)

    def fake_render(endpoint, *, tool_name, arguments, destination, **kwargs):
        destination.write_bytes(b"fake-chart")
        return True

    monkeypatch.setattr(
        "tiangong_ai_for_sustainability.workflows.lca_citations.ensure_chart_image",
        fake_render,
    )

    artifacts = run_lca_citation_workflow(
        dummy_services,
        report_path=report_path,
        chart_path=chart_path,
        raw_data_path=raw_path,
        years=5,
    )

    assert report_path.exists()
    report_text = report_path.read_text("utf-8")
    assert "LCA Citation Intelligence" in report_text
    assert "Top citation questions" in report_text

    assert artifacts.chart_path == chart_path
    assert chart_path.read_bytes() == b"fake-chart"

    assert raw_path.exists()
    payload = json.loads(raw_path.read_text("utf-8"))
    assert len(payload["papers"]) == 3
    assert artifacts.questions
    assert artifacts.trending_topics or artifacts.chart_caption == "Top LCA questions by citation count"


def test_run_deep_lca_report(tmp_path, dummy_services, monkeypatch):
    output_dir = tmp_path / "output"

    def fake_runner(
        services,
        *,
        report_path,
        chart_path,
        raw_data_path=None,
        years=5,
        keyword_overrides=None,
        max_records=200,
    ) -> LCACitationWorkflowArtifacts:
        report_path.write_text("Sample citation report", encoding="utf-8")
        chart_path.write_bytes(b"fake-chart")
        if raw_data_path:
            raw_data_path.write_text("{}", encoding="utf-8")

        question = CitationQuestion(
            question="What is the impact of sample research on sustainability outcomes?",
            citation_count=120,
            publication_year=2022,
            paper_title="Sample Research Paper",
            journal="Journal of LCA",
            doi="10.1234/example",
            url="https://example.com/paper",
            authors=["Researcher A"],
            keyword_hits={"life cycle assessment": 2},
        )
        topic = TrendingTopic(
            topic="Circular systems",
            trend_score=1.5,
            citation_growth=12.0,
            recent_share=0.42,
            coverage_years=(2019, 2023),
            top_papers=["Sample Research Paper"],
        )
        gap = ResearchGap(
            topic="Plant-based plastics",
            paper_count=2,
            avg_citations=95.0,
            recent_papers=0,
            representative_title="Sample Research Paper",
            supporting_doi="10.1234/example",
            rationale="Only two studies but high average citations, indicating demand for deeper exploration.",
        )
        paper = PaperRecord(
            source_id="openalex",
            work_id="https://openalex.org/W1",
            title="Sample Research Paper",
            year=2022,
            citation_count=120,
            doi="10.1234/example",
            url="https://example.com/paper",
            journal="Journal of LCA",
            authors=["Researcher A"],
            abstract="Sample abstract",
            concepts=[],
            keyword_hits={"life cycle assessment": 2},
            extra={},
        )

        return LCACitationWorkflowArtifacts(
            report_path=report_path,
            chart_path=chart_path,
            chart_caption="Top LCA questions by citation count",
            raw_data_path=raw_data_path,
            questions=[question],
            trending_topics=[topic],
            research_gaps=[gap],
            papers=[paper],
        )

    import tiangong_ai_for_sustainability.workflows.deep_lca as deep_lca_module

    def fake_generate_variants(markdown_path, output_dir):
        return [], ["Pandoc not found"]

    monkeypatch.setattr(deep_lca_module, "_generate_document_variants", fake_generate_variants)

    artifacts = run_deep_lca_report(
        dummy_services,
        output_dir=output_dir,
        deep_research=False,
        lca_runner=fake_runner,
    )

    assert artifacts.final_report_path.exists()
    report_text = artifacts.final_report_path.read_text("utf-8")
    assert "Top Citation Questions" in report_text
    assert "Circular systems" in report_text
    assert "Plant-based plastics" in report_text
    assert "lca_trends.png" in report_text
    assert artifacts.citation_report_path.parent == output_dir
    assert not artifacts.doc_variants
    assert artifacts.conversion_warnings
