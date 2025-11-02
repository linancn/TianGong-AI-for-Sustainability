from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from typer.testing import CliRunner

from tiangong_ai_for_sustainability.adapters.base import VerificationResult
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
