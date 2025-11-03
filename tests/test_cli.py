from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from typer.testing import CliRunner

from tiangong_ai_for_sustainability.adapters.base import AdapterError, VerificationResult
from tiangong_ai_for_sustainability.cli.main import app


def invoke(cli_runner: CliRunner, args: list[str]):
    return cli_runner.invoke(app, args)


def test_sources_list(cli_runner, registry_file):
    result = invoke(cli_runner, ["--registry", str(registry_file), "sources", "list"])
    assert result.exit_code == 0
    assert "un_sdg_api" in result.stdout


def test_sources_verify_uses_stub(cli_runner, registry_file):
    with (
        patch(
            "tiangong_ai_for_sustainability.cli.main.resolve_adapter",
            return_value=None,
        ),
        patch(
            "tiangong_ai_for_sustainability.cli.main.ResearchServices.verify_source",
            return_value=VerificationResult(success=True, message="OK", details={"status": "active"}),
        ),
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "sources", "verify", "un_sdg_api"],
        )
    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_sources_verify_reports_failure(cli_runner, registry_file):
    with (
        patch(
            "tiangong_ai_for_sustainability.cli.main.resolve_adapter",
            return_value=None,
        ),
        patch(
            "tiangong_ai_for_sustainability.cli.main.ResearchServices.verify_source",
            return_value=VerificationResult(success=False, message="API key missing", details={"reason": "credentials"}),
        ),
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "sources", "verify", "osdg_api"],
        )

    assert result.exit_code == 1
    assert "API key missing" in result.stdout


def test_sources_audit_success(cli_runner, registry_file):
    with (
        patch(
            "tiangong_ai_for_sustainability.cli.main.resolve_adapter",
            return_value=None,
        ),
        patch(
            "tiangong_ai_for_sustainability.cli.main.ResearchServices.verify_source",
            return_value=VerificationResult(success=True, message="OK", details={"status": "active"}),
        ),
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "sources", "audit"],
        )

    assert result.exit_code == 0
    assert "Audit complete" in result.stdout
    assert "0 failed" in result.stdout.splitlines()[-1]


def test_sources_audit_failure_sets_exit_code(cli_runner, registry_file):
    with (
        patch(
            "tiangong_ai_for_sustainability.cli.main.resolve_adapter",
            return_value=None,
        ),
        patch(
            "tiangong_ai_for_sustainability.cli.main.ResearchServices.verify_source",
            return_value=VerificationResult(success=False, message="Down", details=None),
        ),
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "sources", "audit"],
        )

    assert result.exit_code == 1
    assert "failed" in result.stdout


def test_sources_describe_cli_json(cli_runner, registry_file):
    result = invoke(
        cli_runner,
        ["--registry", str(registry_file), "sources", "describe", "un_sdg_api", "--json"],
    )

    assert result.exit_code == 0
    assert '"un_sdg_api"' in result.stdout


def test_research_get_carbon_intensity_cli(cli_runner, registry_file):
    with patch(
        "tiangong_ai_for_sustainability.cli.main.ResearchServices.get_carbon_intensity",
        return_value={"provider": "WattTime", "location": "CAISO_NORTH", "carbon_intensity": 123, "units": "gCO2e/kWh"},
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "research", "get-carbon-intensity", "CAISO_NORTH"],
        )
    assert result.exit_code == 0
    assert "WattTime" in result.stdout


def test_research_get_carbon_intensity_cli_failure(cli_runner, registry_file):
    with patch(
        "tiangong_ai_for_sustainability.cli.main.ResearchServices.get_carbon_intensity",
        side_effect=AdapterError("grid-intensity CLI missing"),
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "research", "get-carbon-intensity", "CAISO_NORTH"],
        )

    assert result.exit_code == 1
    assert "grid-intensity CLI missing" in result.stderr


def test_research_map_sdg_cli(cli_runner, registry_file, tmp_path):
    sample_text = tmp_path / "sample.txt"
    sample_text.write_text("Sample sustainability text for SDG alignment.", encoding="utf-8")

    sample_payload = {
        "classification": [
            {"goal": {"code": "13", "title": "Climate Action"}, "score": 0.92},
        ]
    }

    with (
        patch(
            "tiangong_ai_for_sustainability.cli.main.ResearchServices.classify_text_with_osdg",
            return_value=sample_payload,
        ),
        patch(
            "tiangong_ai_for_sustainability.cli.main.ResearchServices.sdg_goal_map",
            return_value={"13": {"title": "Climate Action"}},
        ),
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "research", "map-sdg", str(sample_text)],
        )

    assert result.exit_code == 0
    assert "SDG 13" in result.stdout


def test_research_workflow_simple_cli(cli_runner, registry_file, tmp_path):
    report_path = tmp_path / "report.md"
    chart_path = tmp_path / "chart.png"
    artifacts = SimpleNamespace(report_path=report_path, chart_path=chart_path, carbon_snapshot={})

    with patch(
        "tiangong_ai_for_sustainability.cli.main.run_simple_workflow",
        return_value=artifacts,
    ):
        result = invoke(
            cli_runner,
            [
                "--registry",
                str(registry_file),
                "research",
                "workflow",
                "simple",
                "sustainable software",
                "--report-output",
                str(report_path),
                "--chart-output",
                str(chart_path),
            ],
        )

    assert result.exit_code == 0
    assert f"Report written to {report_path}" in result.stdout
    assert f"Chart saved to {chart_path}" in result.stdout


def test_research_find_code_cli(cli_runner, registry_file):
    stub_client = SimpleNamespace(
        search_repositories=lambda topic, per_page: {
            "total_count": 1,
            "items": [
                {
                    "full_name": "demo/lca-toolkit",
                    "stargazers_count": 42,
                    "html_url": "https://github.com/demo/lca-toolkit",
                    "description": "Life cycle assessment toolkit.",
                }
            ],
        }
    )

    with patch(
        "tiangong_ai_for_sustainability.cli.main.ResearchServices.github_topics_client",
        return_value=stub_client,
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "research", "find-code", "life-cycle-assessment", "--limit", "1"],
        )

    assert result.exit_code == 0
    assert "demo/lca-toolkit" in result.stdout


def test_research_metrics_trending_cli(cli_runner, registry_file):
    metrics = [
        SimpleNamespace(
            metric_id="resource_scarcity",
            label="Resource Scarcity Footprint",
            total_works=2,
            total_citations=195,
            citation_trend={2021: 120, 2023: 75},
            top_works=[{"title": "Evaluating resource scarcity footprints in LCA", "year": 2021, "cited_by_count": 120, "doi": "10.1234/scarcity1"}],
            top_concepts=[{"name": "Resource management", "weighted_citations": 120.0}],
        )
    ]
    artifacts = SimpleNamespace(metrics=metrics, raw_records={}, plan=None, output_path=None)

    with patch(
        "tiangong_ai_for_sustainability.cli.main.run_trending_metrics_workflow",
        return_value=artifacts,
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "research", "metrics-trending", "--start-year", "2020"],
        )

    assert result.exit_code == 0
    assert "Resource Scarcity Footprint" in result.stdout
    assert "Works analysed: 2" in result.stdout


def test_research_metrics_trending_cli_dry_run(cli_runner, registry_file):
    artifacts = SimpleNamespace(metrics=[], raw_records={}, plan=["Step 1", "Step 2"], output_path=None)

    with patch(
        "tiangong_ai_for_sustainability.cli.main.run_trending_metrics_workflow",
        return_value=artifacts,
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "research", "metrics-trending"],
        )

    assert result.exit_code == 0
    assert "Dry-run plan" in result.stdout


def test_research_find_papers_cli(cli_runner, registry_file):
    artifacts = SimpleNamespace(
        query="ai sustainability",
        sdg_matches=[{"code": "7", "title": "Affordable and Clean Energy", "score": 2}],
        semantic_scholar=[{"title": "Paper A", "year": 2024, "authors": ["Alice"], "url": "https://example.com"}],
        arxiv=[],
        scopus=[],
        openalex=[],
        notes=[],
        citation_edges=None,
        plan=None,
    )

    with patch(
        "tiangong_ai_for_sustainability.cli.main.run_paper_search",
        return_value=artifacts,
    ) as mocked:
        result = invoke(
            cli_runner,
            [
                "--registry",
                str(registry_file),
                "research",
                "find-papers",
                "ai sustainability",
            ],
        )

    assert result.exit_code == 0
    assert "Semantic Scholar results" in result.stdout
    assert mocked.call_count == 1
    _, kwargs = mocked.call_args
    assert kwargs["query"] == "ai sustainability"


def test_research_synthesize_cli(cli_runner, registry_file, tmp_path):
    report_path = tmp_path / "synthesis.md"
    llm_path = tmp_path / "synthesis.llm.json"
    artifacts = SimpleNamespace(
        report_path=report_path,
        sdg_matches=[],
        repositories=[],
        papers=[],
        semantic_scholar=[],
        openalex=[],
        carbon_snapshot=None,
        llm_summary="Summary",
        llm_response_path=llm_path,
        prompt_template_identifier="custom",
        prompt_template_path=tmp_path / "template.md",
        prompt_language="en",
        plan=None,
        notes=[],
        citation_edges=None,
    )

    with patch(
        "tiangong_ai_for_sustainability.cli.main.run_synthesis_workflow",
        return_value=artifacts,
    ) as mocked:
        result = invoke(
            cli_runner,
            [
                "--registry",
                str(registry_file),
                "research",
                "synthesize",
                "How can AI reduce supply-chain emissions?",
                "--output",
                str(report_path),
            ],
        )

    assert result.exit_code == 0
    assert str(report_path) in result.stdout
    assert mocked.call_count == 1
    _, kwargs = mocked.call_args
    assert kwargs["question"] == "How can AI reduce supply-chain emissions?"


def test_research_workflow_lca_deep_report_prompt_template(cli_runner, registry_file, tmp_path):
    template_path = tmp_path / "template.md"
    template_path.write_text("Instructions", encoding="utf-8")

    artifacts = SimpleNamespace(
        final_report_path=tmp_path / "deep_report.md",
        citation_report_path=tmp_path / "citations.md",
        chart_path=None,
        chart_caption=None,
        raw_data_path=None,
        deep_research_summary="Deep summary",
        deep_research_response_path=None,
        doc_variants=[],
        conversion_warnings=[],
        lca_artifacts=None,
        prompt_template_identifier="custom",
        prompt_template_path=template_path,
        prompt_language="en",
    )

    with patch(
        "tiangong_ai_for_sustainability.cli.main.run_deep_lca_report",
        return_value=artifacts,
    ) as mocked:
        result = invoke(
            cli_runner,
            [
                "--registry",
                str(registry_file),
                "research",
                "workflow",
                "lca-deep-report",
                "--prompt-template",
                str(template_path),
            ],
        )

    assert result.exit_code == 0
    assert str(template_path) in result.stdout
    assert mocked.call_count == 1
    _, kwargs = mocked.call_args
    assert kwargs["prompt_template"] == str(template_path)


def test_research_visuals_verify_cli(cli_runner, registry_file):
    with patch(
        "tiangong_ai_for_sustainability.cli.main.ResearchServices.verify_chart_mcp",
        return_value=VerificationResult(success=True, message="OK", details={"endpoint": "http://127.0.0.1:1122/mcp"}),
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "research", "visuals", "verify"],
        )

    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_research_visuals_verify_cli_failure(cli_runner, registry_file):
    failure = VerificationResult(success=False, message="Node.js not installed", details={"requirement": "nodejs"})
    with patch(
        "tiangong_ai_for_sustainability.cli.main.ResearchServices.verify_chart_mcp",
        return_value=failure,
    ):
        result = invoke(
            cli_runner,
            ["--registry", str(registry_file), "research", "visuals", "verify"],
        )

    assert result.exit_code == 1
    assert "Node.js not installed" in result.stdout
    assert "Hint" in result.stdout or "Hint" in result.stderr
