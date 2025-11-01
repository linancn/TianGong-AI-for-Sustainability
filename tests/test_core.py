from __future__ import annotations

from tiangong_ai_for_sustainability.core.context import ExecutionContext, ExecutionOptions


def test_execution_context_build_default(tmp_path):
    cache_dir = tmp_path / "cache"
    context = ExecutionContext.build_default(cache_dir=cache_dir, enabled_sources=["alpha", "beta"])

    assert context.cache_dir == cache_dir
    assert context.cache_dir.exists()
    assert context.is_enabled("alpha")
    assert context.is_enabled("beta")
    assert not context.is_enabled("gamma")

    context.enable("gamma")
    assert context.is_enabled("gamma")
    context.disable("gamma")
    assert not context.is_enabled("gamma")

    assert isinstance(context.options, ExecutionOptions)
