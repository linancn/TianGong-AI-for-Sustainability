from __future__ import annotations

import logging

import pytest

from tiangong_ai_for_sustainability.core.context import ExecutionContext, ExecutionOptions
from tiangong_ai_for_sustainability.core.logging import StructuredLogFormatter, configure_logging, get_logger, log_progress, log_separator


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


@pytest.fixture
def reset_logging_handlers():
    root = logging.getLogger()
    existing_handlers = list(root.handlers)
    yield
    root.handlers = existing_handlers


class _ListHandler(logging.Handler):
    def __init__(self, formatter: logging.Formatter):
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.setFormatter(formatter)

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - trivial
        self.records.append(record)


def test_structured_formatter_appends_extras():
    formatter = StructuredLogFormatter(use_color=False)
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=42,
        msg="Fetching dataset",
        args=(),
        exc_info=None,
    )
    record.phase = "acquisition"
    record.status = "running"
    record.tags = ("workflow.simple",)

    formatted = formatter.format(record)

    assert "Fetching dataset" in formatted
    assert "phase=acquisition" in formatted
    assert "status=running" in formatted
    assert "tags=[workflow.simple]" in formatted


def test_configure_logging_installs_structured_formatter():
    root = logging.getLogger()
    existing_handlers = list(root.handlers)
    try:
        configure_logging(force=True)
        assert root.handlers, "expected at least one handler configured"
        formatter = root.handlers[0].formatter
        assert isinstance(formatter, StructuredLogFormatter)
    finally:
        root.handlers = existing_handlers


def test_log_progress_populates_record_extras(reset_logging_handlers):
    configure_logging(force=True)
    logger = get_logger("test.progress")
    root = logging.getLogger()
    collector = _ListHandler(root.handlers[0].formatter)
    root.addHandler(collector)
    try:
        log_progress(logger, "Downloading", phase="fetch", step="http", status="started", result="pending")
    finally:
        root.removeHandler(collector)

    assert collector.records, "log_progress should emit a record"
    record = collector.records[0]
    assert getattr(record, "phase") == "fetch"
    assert getattr(record, "step") == "http"
    assert getattr(record, "status") == "started"
    assert getattr(record, "result") == "pending"
    formatted = collector.format(record)
    assert "phase=fetch" in formatted
    assert "status=started" in formatted


def test_log_separator_emits_visual_line(reset_logging_handlers):
    configure_logging(force=True)
    logger = get_logger("test.separator")
    root = logging.getLogger()
    collector = _ListHandler(root.handlers[0].formatter)
    root.addHandler(collector)
    try:
        log_separator(logger, title="Pipeline", char="-", width=30)
    finally:
        root.removeHandler(collector)
    assert collector.records
    record = collector.records[0]
    assert getattr(record, "separator") == "Pipeline"
    message = record.getMessage()
    assert "Pipeline" in message
    assert set(message) <= {"-", " ", "P", "i", "p", "e", "l", "n"}
