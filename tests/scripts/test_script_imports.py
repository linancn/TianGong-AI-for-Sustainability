from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "scripts"


@pytest.mark.parametrize(
    "relative_path",
    [
        Path("ops/init_study_workspace.py"),
        Path("ops/audit_sources.py"),
        Path("tooling/compose_inline_prompt.py"),
        Path("examples/run_deep_research.py"),
    ],
)
def test_script_loads_without_errors(relative_path: Path) -> None:
    """Ensure relocated helper scripts still import successfully."""

    script_path = SCRIPTS_ROOT / relative_path
    assert script_path.exists(), f"Script not found: {script_path}"

    module_name = f"tiangong_script_smoke_{relative_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec and spec.loader, f"Unable to build import spec for {script_path}"

    module = importlib.util.module_from_spec(spec)
    assert module is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
