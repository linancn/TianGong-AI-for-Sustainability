"""
Core infrastructure modules shared across TianGong sustainability tooling.

This package intentionally stays lightweight and dependency-free apart from the
standard library and the project-wide configuration helpers. It exposes
registries, execution context management, and utility protocols used by higher
level services.
"""

from .context import ExecutionContext, ExecutionOptions
from .logging import bind_tags, configure_logging, get_logger, log_progress, log_separator
from .registry import (
    DataSourceDescriptor,
    DataSourcePriority,
    DataSourceRegistry,
    DataSourceStatus,
    RegistryLoadError,
)

__all__ = [
    "ExecutionContext",
    "ExecutionOptions",
    "DataSourceDescriptor",
    "DataSourcePriority",
    "DataSourceRegistry",
    "DataSourceStatus",
    "RegistryLoadError",
    "get_logger",
    "configure_logging",
    "bind_tags",
    "log_progress",
    "log_separator",
]
