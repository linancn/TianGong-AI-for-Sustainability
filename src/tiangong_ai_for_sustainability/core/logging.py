"""
Centralised logging helpers for TianGong sustainability tooling.

The helpers provide a thin wrapper over :mod:`logging` that keeps configuration
deterministic while allowing callers to attach observability tags taken from the
execution context. Modules should obtain loggers via :func:`get_logger` instead
of instantiating their own handlers to ensure consistent formatting.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from logging import Logger, LoggerAdapter
from typing import Mapping, MutableMapping, Optional, Sequence

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_LEVEL = "INFO"
_ENV_LEVEL = "TIANGONG_LOG_LEVEL"


def _resolve_level(level: Optional[int | str]) -> int:
    if isinstance(level, int):
        return level
    candidate = (level or os.getenv(_ENV_LEVEL) or DEFAULT_LEVEL).upper()
    return logging.getLevelName(candidate) if isinstance(candidate, str) else logging.INFO


@lru_cache(maxsize=1)
def _base_logger_configured() -> bool:
    return False


def _set_base_config(level: Optional[int | str] = None) -> None:
    if _base_logger_configured.cache_info().currsize == 0:
        logging.basicConfig(level=_resolve_level(level), format=DEFAULT_FORMAT)
        _base_logger_configured.cache_clear()
        _base_logger_configured()


def configure_logging(level: Optional[int | str] = None, *, force: bool = False) -> None:
    """
    Configure root logging handlers unless already initialised.

    Parameters
    ----------
    level:
        Optional logging level override. Falls back to ``TIANGONG_LOG_LEVEL`` or ``INFO``.
    force:
        When ``True`` the configuration is reapplied even if previously initialised.
    """

    if force:
        logging.basicConfig(level=_resolve_level(level), format=DEFAULT_FORMAT, force=True)
        _base_logger_configured.cache_clear()
        _base_logger_configured()
        return
    _set_base_config(level)


def _merge_extra(
    *,
    tags: Optional[Sequence[str]],
    extra: Optional[Mapping[str, object]],
) -> MutableMapping[str, object]:
    payload: MutableMapping[str, object] = {}
    if tags:
        payload["tags"] = tuple(tags)
    if extra:
        payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def get_logger(
    name: str,
    *,
    level: Optional[int | str] = None,
    tags: Optional[Sequence[str]] = None,
    extra: Optional[Mapping[str, object]] = None,
) -> LoggerAdapter:
    """
    Return a configured :class:`logging.LoggerAdapter` instance.

    Parameters
    ----------
    name:
        Logger namespace, typically ``__name__`` or a structured label.
    level:
        Optional per-logger level override.
    tags:
        Optional observability tags attached to the ``extra`` payload.
    extra:
        Additional structured metadata recorded with each log entry.
    """

    configure_logging(level)
    base: Logger = logging.getLogger(name)
    if level is not None:
        base.setLevel(_resolve_level(level))
    adapter_extra = _merge_extra(tags=tags, extra=extra)
    if adapter_extra:
        return LoggerAdapter(base, adapter_extra)
    return LoggerAdapter(base, {})  # type: ignore[arg-type]


def bind_tags(logger: LoggerAdapter, tags: Sequence[str]) -> LoggerAdapter:
    """
    Create a child logger with additional observability tags.

    The helper avoids mutating the original adapter to keep log context immutable.
    """

    current = dict(logger.extra) if isinstance(logger.extra, Mapping) else {}
    merged_tags = tuple({*(current.get("tags", ())), *tags})
    new_extra = dict(current)
    new_extra["tags"] = merged_tags
    return LoggerAdapter(logger.logger, new_extra)
