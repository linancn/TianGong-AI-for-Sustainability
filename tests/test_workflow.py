from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tiangong_ai_for_sustainability.adapters.base import VerificationResult
from tiangong_ai_for_sustainability.core import ExecutionContext, ExecutionOptions
from tiangong_ai_for_sustainability.deep_research import ResearchPrompt
from tiangong_ai_for_sustainability.workflows.citation_template import (
    CitationQuestion,
    CitationWorkflowArtifacts,
    PaperRecord,
    ResearchGap,
    TrendingTopic,
    run_lca_citation_workflow,
)
from tiangong_ai_for_sustainability.workflows.deep_research import run_deep_lca_report
from tiangong_ai_for_sustainability.workflows.metrics import TRENDING_METRIC_CONFIGS, run_trending_metrics_workflow
from tiangong_ai_for_sustainability.workflows.papers import run_paper_search
from tiangong_ai_for_sustainability.workflows.simple import run_simple_workflow
from tiangong_ai_for_sustainability.workflows.synthesize import run_synthesis_workflow


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

    def verify_chart_mcp(self) -> VerificationResult:
        return VerificationResult(success=True, message="ok", details={"endpoint": self.chart_mcp_endpoint()})


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


def test_run_simple_workflow_dry_run(tmp_path, dummy_services):
    report_path = tmp_path / "report.md"
    chart_path = tmp_path / "chart.png"

    context = ExecutionContext.build_default(
        cache_dir=tmp_path / "cache",
        options=ExecutionOptions(dry_run=True),
    )
    dummy_services.context = context

    artifacts = run_simple_workflow(
        dummy_services,
        topic="low-carbon ai",
        report_path=report_path,
        chart_path=chart_path,
    )

    assert not report_path.exists()
    assert artifacts.chart_path is None
    assert "Dry-run" in artifacts.carbon_snapshot.get("note", "")


def test_run_paper_search(tmp_path, dummy_services):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    dummy_services.context = context

    dummy_services._scholar = SimpleNamespace(
        search_papers=lambda topic, limit, fields: {
            "data": [
                {
                    "paperId": "S1",
                    "title": "Semantic Scholar Paper",
                    "year": 2024,
                    "url": "https://example.com/s1",
                    "abstract": "Abstract",
                    "authors": [{"name": "Alice"}],
                }
            ]
        }
    )

    def iterate_works(**kwargs):
        yield {
            "id": "W1",
            "display_name": "OpenAlex Paper",
            "publication_year": 2023,
            "doi": "10.1234/example",
            "cited_by_count": 12,
            "referenced_works": ["W2", "W3"],
            "authorships": [{"author": {"display_name": "Dr. Example"}}],
        }

    dummy_services._openalex = SimpleNamespace(iterate_works=iterate_works)

    artifacts = run_paper_search(
        dummy_services,
        query="ai sustainability",
        sdg_context="Artificial intelligence for sustainability",
        include_openalex=True,
        include_citations=True,
        limit=5,
    )

    assert artifacts.sdg_matches
    assert artifacts.semantic_scholar[0]["paper_id"] == "S1"
    assert artifacts.openalex[0]["id"] == "W1"
    assert artifacts.citation_edges and artifacts.citation_edges[0]["source"] == "W1"


def test_run_paper_search_dry_run(tmp_path, dummy_services):
    context = ExecutionContext.build_default(
        cache_dir=tmp_path / "cache",
        options=ExecutionOptions(dry_run=True),
    )
    dummy_services.context = context

    artifacts = run_paper_search(
        dummy_services,
        query="energy efficiency",
        include_openalex=False,
    )

    assert artifacts.plan
    assert not artifacts.semantic_scholar


def test_run_trending_metrics_workflow(tmp_path, dummy_services):
    records_map = {
        "resource_scarcity": [
            {
                "display_name": "Evaluating resource scarcity footprints in LCA",
                "publication_year": 2021,
                "cited_by_count": 120,
                "doi": "10.1234/scarcity1",
                "concepts": [
                    {"display_name": "Resource management", "score": 0.6, "level": 1},
                    {"display_name": "Life cycle assessment", "score": 0.7, "level": 1},
                ],
            },
            {
                "display_name": "Critical minerals scarcity assessment via LCA",
                "publication_year": 2023,
                "cited_by_count": 75,
                "doi": "10.1234/scarcity2",
                "concepts": [
                    {"display_name": "Mineral resource", "score": 0.65, "level": 1},
                ],
            },
        ],
        "planetary_footprint": [
            {
                "display_name": "Planetary footprint indicators for consumer products",
                "publication_year": 2022,
                "cited_by_count": 88,
                "doi": "10.1234/footprint1",
                "concepts": [
                    {"display_name": "Planetary boundaries", "score": 0.8, "level": 1},
                    {"display_name": "Sustainability", "score": 0.5, "level": 1},
                ],
            }
        ],
        "biodiversity_loss": [
            {
                "display_name": "Quantifying biodiversity loss in LCA",
                "publication_year": 2024,
                "cited_by_count": 54,
                "doi": "10.1234/biodiversity1",
                "concepts": [
                    {"display_name": "Biodiversity", "score": 0.75, "level": 1},
                ],
            }
        ],
        "sustainable_nanotechnology": [
            {
                "display_name": "Nanotechnology sustainability metrics in life cycle studies",
                "publication_year": 2020,
                "cited_by_count": 66,
                "doi": "10.1234/nano1",
                "concepts": [
                    {"display_name": "Nanotechnology", "score": 0.7, "level": 1},
                ],
            }
        ],
    }

    def iterate_works(**kwargs):
        search = kwargs.get("search", "")
        for config in TRENDING_METRIC_CONFIGS:
            if config["search"] in search or config["id"].split("_")[0] in search:
                return iter(records_map[config["id"]])
        if '"resource scarcity"' in search:
            return iter(records_map["resource_scarcity"])
        if '"planetary boundaries"' in search:
            return iter(records_map["planetary_footprint"])
        if '"biodiversity"' in search:
            return iter(records_map["biodiversity_loss"])
        if '"nanotechnology"' in search:
            return iter(records_map["sustainable_nanotechnology"])
        return iter([])

    dummy_services._openalex.iterate_works = iterate_works

    output_path = tmp_path / "metrics.json"
    artifacts = run_trending_metrics_workflow(
        dummy_services,
        start_year=2020,
        end_year=2024,
        max_records_per_metric=50,
        output_path=output_path,
    )

    assert len(artifacts.metrics) == len(TRENDING_METRIC_CONFIGS)
    scarcity_summary = next(summary for summary in artifacts.metrics if summary.metric_id == "resource_scarcity")
    assert scarcity_summary.total_works == 2
    assert scarcity_summary.total_citations == 195
    assert any(concept["name"] == "Resource management" for concept in scarcity_summary.top_concepts)
    assert artifacts.output_path == output_path
    assert output_path.exists()


def test_run_trending_metrics_workflow_dry_run(tmp_path, dummy_services):
    dummy_services.context = ExecutionContext.build_default(
        cache_dir=tmp_path / "cache",
        options=ExecutionOptions(dry_run=True),
    )
    artifacts = run_trending_metrics_workflow(dummy_services, start_year=2020, end_year=2024)
    assert artifacts.plan is not None
    assert not artifacts.metrics


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
        "tiangong_ai_for_sustainability.workflows.citation_template.ensure_chart_image",
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
    assert "LCA × Planetary Boundaries Citation Intelligence" in report_text
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
        profile=None,
        report_path,
        chart_path,
        raw_data_path=None,
        years=5,
        keyword_overrides=None,
        max_records=200,
    ) -> CitationWorkflowArtifacts:
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

        return CitationWorkflowArtifacts(
            report_path=report_path,
            chart_path=chart_path,
            chart_caption="Top LCA questions by citation count",
            raw_data_path=raw_data_path,
            questions=[question],
            trending_topics=[topic],
            research_gaps=[gap],
            papers=[paper],
        )

    import tiangong_ai_for_sustainability.workflows.deep_research as deep_research_module

    def fake_generate_variants(markdown_path, output_dir):
        return [], ["Pandoc not found"]

    monkeypatch.setattr(deep_research_module, "_generate_document_variants", fake_generate_variants)

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


def test_run_deep_lca_report_applies_prompt_template(tmp_path, dummy_services, monkeypatch):
    output_dir = tmp_path / "output"
    template_path = tmp_path / "custom_template.md"
    template_path.write_text("Summarise findings for {{topic}}", encoding="utf-8")

    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.options.prompt_variables = {"topic": "LCA digitisation"}
    dummy_services.context = context

    def fake_runner(
        services,
        *,
        profile=None,
        report_path,
        chart_path,
        raw_data_path=None,
        years=5,
        keyword_overrides=None,
        max_records=200,
    ) -> CitationWorkflowArtifacts:
        report_path.write_text("Sample citation report", encoding="utf-8")
        chart_path.write_bytes(b"fake-chart")
        questions = [
            CitationQuestion(
                question="Question?",
                citation_count=10,
                publication_year=2024,
                paper_title="Paper",
                journal="Journal",
                doi="10.1/abc",
                url="https://example.com",
                authors=["Author"],
                keyword_hits={},
            )
        ]
        return CitationWorkflowArtifacts(
            report_path=report_path,
            chart_path=chart_path,
            chart_caption=None,
            raw_data_path=raw_data_path,
            questions=questions,
            trending_topics=[],
            research_gaps=[],
            papers=[],
        )

    import tiangong_ai_for_sustainability.workflows.deep_research as deep_research_module

    def fake_variants(markdown_path, output_dir):
        return [], []

    captured = {}

    def fake_run(*, profile, citation_artifacts, years, prompt_override, instructions_override):
        captured["instructions"] = instructions_override
        captured["profile"] = profile.slug

        class DummyResult:
            output_text = "Deep summary"

            def to_dict(self):
                return {"output": self.output_text}

        return DummyResult()

    def fake_load_prompt(template, language=None):
        assert template == str(template_path)
        return SimpleNamespace(
            identifier="custom",
            path=template_path,
            language=language or "en",
            render=lambda variables: template_path.read_text("utf-8").replace("{{topic}}", variables.get("topic", "")),
        )

    dummy_services.load_prompt_template = fake_load_prompt

    monkeypatch.setattr(deep_research_module, "_generate_document_variants", fake_variants)
    monkeypatch.setattr(deep_research_module, "_run_deep_research", fake_run)

    artifacts = run_deep_lca_report(
        dummy_services,
        output_dir=output_dir,
        prompt_template=str(template_path),
        prompt_language="en",
        lca_runner=fake_runner,
    )

    assert captured["instructions"] == "Summarise findings for LCA digitisation"
    assert captured["profile"] == "lca"
    assert artifacts.prompt_template_path == template_path
    assert artifacts.prompt_template_identifier == "custom"
    assert artifacts.deep_research_summary == "Deep summary"
    assert artifacts.doc_variants == []
    assert artifacts.conversion_warnings == []


def test_run_synthesis_workflow_dry_run(tmp_path, dummy_services):
    context = ExecutionContext.build_default(
        cache_dir=tmp_path / "cache",
        options=ExecutionOptions(dry_run=True),
    )
    dummy_services.context = context

    artifacts = run_synthesis_workflow(
        dummy_services,
        question="How can AI reduce supply-chain emissions?",
        report_path=tmp_path / "synthesis.md",
        topic="ai sustainability",
        carbon_location="CAISO_NORTH",
    )

    assert artifacts.plan
    assert "Match SDG goals" in artifacts.plan[0]
    assert not artifacts.report_path.exists()


def test_run_synthesis_workflow_with_llm(tmp_path, dummy_services, monkeypatch):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    context.options.prompt_variables = {"audience": "engineers"}
    dummy_services.context = context

    template_path = tmp_path / "template.md"
    template_path.write_text("Summarise for {{topic}}", encoding="utf-8")

    captured = {}

    class FakeResult:
        output_text = "LLM summary"

        def to_dict(self):
            return {"output": self.output_text}

    class FakeClient:
        def run(self, prompt, instructions=None, max_tool_calls=None):
            captured["prompt"] = prompt
            captured["instructions"] = instructions
            return FakeResult()

    def fake_load_prompt(template, language=None):
        assert template == "custom"
        return SimpleNamespace(
            identifier="custom",
            path=template_path,
            language=language or "en",
            render=lambda variables: template_path.read_text("utf-8").replace("{{topic}}", variables.get("topic", "")),
        )

    dummy_services.load_prompt_template = fake_load_prompt
    monkeypatch.setattr(
        "tiangong_ai_for_sustainability.workflows.synthesize.DeepResearchClient",
        lambda: FakeClient(),
    )

    artifacts = run_synthesis_workflow(
        dummy_services,
        question="How can AI reduce supply-chain emissions?",
        report_path=tmp_path / "synthesis.md",
        topic="green software",
        carbon_location="CAISO_NORTH",
        prompt_template="custom",
        prompt_language="en",
    )

    assert artifacts.llm_summary == "LLM summary"
    assert artifacts.report_path.exists()
    assert artifacts.llm_response_path and artifacts.llm_response_path.exists()
    assert artifacts.prompt_template_path == template_path
    assert captured["instructions"] == "Summarise for green software"
    assert isinstance(captured["prompt"], ResearchPrompt)


def test_run_synthesis_workflow_skip_llm(tmp_path, dummy_services, monkeypatch):
    context = ExecutionContext.build_default(cache_dir=tmp_path / "cache")
    dummy_services.context = context

    monkeypatch.setattr(
        "tiangong_ai_for_sustainability.workflows.synthesize.DeepResearchClient",
        lambda: (_ for _ in ()).throw(AssertionError("LLM should not run")),
    )

    artifacts = run_synthesis_workflow(
        dummy_services,
        question="How can AI reduce supply-chain emissions?",
        report_path=tmp_path / "synthesis.md",
        skip_llm=True,
    )

    assert artifacts.llm_summary is None
    assert artifacts.report_path.exists()
