from __future__ import annotations

from tiangong_ai_for_sustainability.core.registry import DataSourcePriority, DataSourceRegistry


def test_registry_load_core_sources(registry_file):
    registry = DataSourceRegistry.from_yaml(registry_file)

    un_sdg = registry.require("un_sdg_api")
    assert un_sdg.priority == DataSourcePriority.P1
    github = registry.require("github_topics")
    assert "repository" in github.tags
    crossref = registry.require("crossref")
    assert crossref.priority == DataSourcePriority.P1
    blocked = registry.require("google_scholar")
    assert blocked.status.name == "BLOCKED"
