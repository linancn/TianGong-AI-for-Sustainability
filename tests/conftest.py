from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tiangong_ai_for_sustainability.cli.main import app


@pytest.fixture(scope="session")
def registry_file() -> Path:
    datasources_pkg = "tiangong_ai_for_sustainability.resources.datasources"
    with resources.as_file(resources.files(datasources_pkg) / "core.yaml") as ref:
        return Path(ref)


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def cli_app():
    return app
