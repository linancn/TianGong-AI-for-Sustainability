"""
Centralised logging helpers for TianGong sustainability tooling.

The helpers provide a thin wrapper over :mod:`logging` that keeps configuration
deterministic while allowing callers to attach observability tags taken from the
execution context. Modules should obtain loggers via :func:`get_logger` instead
of instantiating their own handlers to ensure consistent formatting.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from copy import copy
from functools import lru_cache
from logging import Logger, LoggerAdapter
from typing import Any, Iterable, Mapping, MutableMapping, Optional, Sequence

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LEVEL = "INFO"
_ENV_LEVEL = "TIANGONG_LOG_LEVEL"
_ENV_COLOR = "TIANGONG_LOG_COLOR"
_EXTRA_FOCUS_ORDER: Sequence[str] = (
    "phase",
    "step",
    "status",
    "result",
    "outcome",
    "duration",
    "tags",
    "method",
    "url",
    "status_code",
    "attempt",
    "cache",
    "transport",
)

_LEVEL_STYLES = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[95m",  # Bright magenta
}
_RESET = "\033[0m"

_RESERVED_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


def _resolve_level(level: Optional[int | str]) -> int:
    if isinstance(level, int):
        return level
    candidate = (level or os.getenv(_ENV_LEVEL) or DEFAULT_LEVEL).upper()
    return logging.getLevelName(candidate) if isinstance(candidate, str) else logging.INFO


def _coerce_bool(value: str) -> Optional[bool]:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on", "enabled"}:
        return True
    if lowered in {"0", "false", "no", "off", "disabled"}:
        return False
    return None


def _supports_color(stream: Any) -> bool:
    preference = os.getenv(_ENV_COLOR)
    if preference:
        resolved = _coerce_bool(preference)
        if resolved is not None:
            return resolved
        if preference.strip().lower() == "auto":
            return hasattr(stream, "isatty") and bool(stream.isatty())
    return hasattr(stream, "isatty") and bool(stream.isatty())


def _iter_extras(record: logging.LogRecord) -> Iterable[tuple[str, Any]]:
    payload = {key: value for key, value in record.__dict__.items() if key not in _RESERVED_ATTRS and not key.startswith("_") and value is not None}

    for key in _EXTRA_FOCUS_ORDER:
        if key in payload:
            yield key, payload.pop(key)

    for key in sorted(payload):
        yield key, payload[key]


def _format_extra_value(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return "[" + ", ".join(_format_extra_value(item) for item in value) + "]"
    if isinstance(value, Mapping):
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            return repr(dict(value))
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


class StructuredLogFormatter(logging.Formatter):
    """Formatter that appends structured extras and supports optional colour output."""

    def __init__(self, *, use_color: bool = False) -> None:
        super().__init__(DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        working = copy(record)
        if self.use_color:
            working.levelname = self._colourise_level(working.levelname)
        base = super().format(working)
        extras = " ".join(f"{key}={_format_extra_value(value)}" for key, value in _iter_extras(record))
        if extras:
            return f"{base} | {extras}"
        return base

    @staticmethod
    def _colourise_level(levelname: str) -> str:
        style = _LEVEL_STYLES.get(levelname.strip().upper())
        if not style:
            return levelname
        return f"{style}{levelname}{_RESET}"


@lru_cache(maxsize=1)
def _base_logger_configured() -> bool:
    return False


def _build_handler(level: Optional[int | str]) -> logging.Handler:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(_resolve_level(level))
    formatter = StructuredLogFormatter(use_color=_supports_color(handler.stream))
    handler.setFormatter(formatter)
    return handler


def _set_base_config(level: Optional[int | str] = None) -> None:
    if _base_logger_configured.cache_info().currsize == 0:
        handler = _build_handler(level)
        logging.basicConfig(level=_resolve_level(level), handlers=[handler])
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
        handler = _build_handler(level)
        logging.basicConfig(level=_resolve_level(level), handlers=[handler], force=True)
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


def _emit_with_extra(
    logger: LoggerAdapter | Logger,
    level: int,
    message: str,
    payload: Optional[Mapping[str, object]],
) -> None:
    if isinstance(logger, LoggerAdapter):
        merged: MutableMapping[str, object] = {}
        if isinstance(logger.extra, Mapping):
            merged.update({key: value for key, value in logger.extra.items() if value is not None})
        if payload:
            merged.update(payload)
        if merged:
            logger.logger.log(level, message, extra=merged)
        else:
            logger.logger.log(level, message)
        return
    if payload:
        logger.log(level, message, extra=dict(payload))
    else:
        logger.log(level, message)


def log_progress(
    logger: LoggerAdapter | Logger,
    message: str,
    *,
    phase: Optional[str] = None,
    step: Optional[str] = None,
    status: Optional[str] = None,
    result: Optional[str] = None,
    level: int = logging.INFO,
    extra: Optional[Mapping[str, object]] = None,
) -> None:
    """
    Emit a progress log with structured metadata so downstream observers can
    easily identify the current step and outcome.
    """

    payload: MutableMapping[str, object] = {}
    if extra:
        payload.update(extra)
    if phase:
        payload["phase"] = phase
    if step:
        payload["step"] = step
    if status:
        payload["status"] = status
    if result:
        payload["result"] = result
    _emit_with_extra(logger, level, message, payload or None)


def log_separator(
    logger: LoggerAdapter | Logger,
    *,
    title: Optional[str] = None,
    level: int = logging.INFO,
    char: str = "─",
    width: int = 72,
) -> None:
    """
    Emit a visual separator to improve readability when running multi-step workflows.
    """

    width = max(16, width)
    body = char * width
    if title:
        clean = title.strip()
        padded = f" {clean} "
        if len(padded) < width:
            side = (width - len(padded)) // 2
            body = f"{char * side}{padded}{char * (width - len(padded) - side)}"
        else:
            body = padded
    payload: Mapping[str, object] | None = {"separator": title} if title else {"separator": True}
    _emit_with_extra(logger, level, body, payload)
