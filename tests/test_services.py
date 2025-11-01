from __future__ import annotations

from unittest.mock import MagicMock, patch

from tiangong_ai_for_sustainability.core.context import ExecutionContext, ExecutionOptions
from tiangong_ai_for_sustainability.core.registry import DataSourceRegistry
from tiangong_ai_for_sustainability.services.research import ResearchServices


def _make_services(tmp_path, registry_file, *, dry_run: bool = True) -> ResearchServices:
    registry = DataSourceRegistry.from_yaml(registry_file)
    context = ExecutionContext.build_default(
        cache_dir=tmp_path / "cache",
        options=ExecutionOptions(dry_run=dry_run),
    )
    return ResearchServices(registry=registry, context=context)


def test_research_services_carbon_intensity_dry_run(tmp_path, registry_file):
    services = _make_services(tmp_path, registry_file, dry_run=True)
    payload = services.get_carbon_intensity("CAISO_NORTH")

    assert payload["location"] == "CAISO_NORTH"
    assert "note" in payload


def test_research_services_sdg_goal_map_cached(tmp_path, registry_file):
    services = _make_services(tmp_path, registry_file)
    mock_client = MagicMock()
    mock_client.list_goals.return_value = [
        {"code": "13", "title": "Climate Action"},
        {"code": "7", "title": "Affordable and Clean Energy"},
    ]

    with patch.object(ResearchServices, "un_sdg_client", return_value=mock_client):
        mapping = services.sdg_goal_map()
        assert mapping["13"]["title"] == "Climate Action"
        # second call should use cache
        services.sdg_goal_map()

    mock_client.list_goals.assert_called_once()


def test_research_services_classify_text_dry_run(tmp_path, registry_file):
    services = _make_services(tmp_path, registry_file, dry_run=True)
    payload = services.classify_text_with_osdg("Sustainability matters.")
    assert payload["note"].startswith("Dry-run")
