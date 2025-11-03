"""
Execution context primitives shared across CLI commands and Codex automations.

The intent is to give Codex a structured object describing which data sources,
credentials, cache directories, and runtime behaviours are currently enabled.
This keeps orchestration code declarative and makes it easier to adapt when new
sources are added or removed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import LoggerAdapter
from pathlib import Path
from typing import Mapping, MutableSet, Optional, Sequence

from ..config import SecretsBundle, load_secrets
from .logging import get_logger as _get_logger


@dataclass(slots=True)
class ExecutionOptions:
    """
    Flags controlling how commands behave at runtime.

    Attributes
    ----------
    dry_run:
        When ``True`` commands should only emit their execution plan without
        performing network calls or file writes.
    background_tasks:
        Enables scheduling of long-running tasks in the background. Commands
        should surface job identifiers instead of blocking.
    observability_tags:
        Additional tags surfaced in logs and telemetry. Useful for downstream
        pipelines, e.g. when Codex wants to attribute work to a parent plan.
    prompt_template:
        Optional alias or filesystem path pointing to a reusable prompt template
        under ``specs/prompts``. Shared by LLM-enabled commands to keep prompt
        selection deterministic.
    prompt_language:
        Preferred language for prompt templates. Used to pick between English
        and Chinese defaults when the caller does not provide a specific path.
    prompt_variables:
        Arbitrary placeholders that commands can apply when rendering prompts.
        Each command decides how to interpret these variables.
    """

    dry_run: bool = False
    background_tasks: bool = False
    observability_tags: Sequence[str] = field(default_factory=tuple)
    prompt_template: Optional[str] = None
    prompt_language: Optional[str] = None
    prompt_variables: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionContext:
    """
    Shared execution context across CLI commands.

    Attributes
    ----------
    enabled_sources:
        IDs of data sources that are currently enabled. Commands should treat
        this as the authoritative allowlist.
    cache_dir:
        Root directory for caches, downloaded assets, and generated artefacts.
    secrets:
        Bundled secret values loaded from ``.secrets``. Commands can opt-in to
        specific credentials rather than attempting to parse files directly.
    options:
        Auxiliary execution flags toggled by the caller or environment.
    extra:
        Free-form slot for additional metadata. Use sparingly and prefer
        well-defined attributes when possible.
    """

    enabled_sources: MutableSet[str]
    cache_dir: Path
    secrets: SecretsBundle
    options: ExecutionOptions = field(default_factory=ExecutionOptions)
    extra: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def build_default(
        cls,
        *,
        cache_dir: Optional[Path] = None,
        enabled_sources: Optional[Sequence[str]] = None,
        options: Optional[ExecutionOptions] = None,
        secrets: Optional[SecretsBundle] = None,
    ) -> "ExecutionContext":
        """
        Construct a context using sensible defaults.

        Parameters
        ----------
        cache_dir:
            Base directory for caches. Defaults to ``.cache/tiangong`` relative
            to the current working directory.
        enabled_sources:
            Optional iterable used to seed the allowlist. When omitted all
            sources are implicitly enabled until a registry is consulted.
        options:
            Optional execution flags. When omitted :class:`ExecutionOptions`
            defaults are used.
        secrets:
            Preloaded secret bundle. When omitted the helper calls
            :func:`load_secrets`.
        """

        resolved_cache = cache_dir or Path.cwd() / ".cache" / "tiangong"
        resolved_cache.mkdir(parents=True, exist_ok=True)
        resolved_secrets = secrets or load_secrets(strict=False)
        resolved_options = options or ExecutionOptions()
        allowlist: MutableSet[str] = set(enabled_sources or [])
        return cls(
            enabled_sources=allowlist,
            cache_dir=resolved_cache,
            secrets=resolved_secrets,
            options=resolved_options,
        )

    def is_enabled(self, source_id: str) -> bool:
        """
        Check whether a data source is enabled in the current context.

        When no allowlist has been declared the function defaults to ``True`` to
        preserve backward compatibility.
        """

        if not self.enabled_sources:
            return True
        return source_id in self.enabled_sources

    def enable(self, source_id: str) -> None:
        """Enable a data source for subsequent calls."""

        self.enabled_sources.add(source_id)

    def disable(self, source_id: str) -> None:
        """Disable a data source for subsequent calls."""

        self.enabled_sources.discard(source_id)

    def get_logger(self, name: str, *, extra: Optional[Mapping[str, object]] = None) -> LoggerAdapter:
        """Return a logger adapter enriched with execution context observability tags."""

        tags = tuple(self.options.observability_tags)
        return _get_logger(name, tags=tags if tags else None, extra=extra)
