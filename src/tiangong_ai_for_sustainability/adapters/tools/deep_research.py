"""
Adapter for verifying OpenAI Deep Research availability.

The adapter focuses on static credential checks so that verification remains
deterministic. Actual orchestration is handled by :mod:`tiangong_ai_for_sustainability.llm.openai_deep_research`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import LoggerAdapter

from ...config import OpenAISettings
from ...core.logging import get_logger
from ...llm import DEFAULT_DEEP_RESEARCH_MODEL
from ..base import DataSourceAdapter, VerificationResult


@dataclass(slots=True)
class OpenAIDeepResearchAdapter(DataSourceAdapter):
    """Check whether Deep Research can be invoked with the available secrets."""

    settings: OpenAISettings
    source_id: str = field(init=False, default="openai_deep_research")
    logger: LoggerAdapter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    def verify(self) -> VerificationResult:
        """
        Confirm required credentials for Deep Research are present.

        The adapter does not perform a live API call to keep verification
        deterministic; instead it ensures an API key is configured and surfaces
        the model that will be used by default.
        """

        api_key = self.settings.api_key
        if not api_key:
            self.logger.warning("OpenAI API key missing for Deep Research source")
            return VerificationResult(
                success=False,
                message=(
                    "OpenAI API key is not configured. Populate the [openai] section in " ".secrets/secrets.toml or set OPENAI_API_KEY before enabling the " "'openai_deep_research' source."
                ),
            )

        model = self.settings.resolve_deep_research_model() or DEFAULT_DEEP_RESEARCH_MODEL
        self.logger.debug("Deep Research credentials detected", extra={"model": model})
        return VerificationResult(
            success=True,
            message=f"OpenAI Deep Research ready (model '{model}').",
            details={"model": model},
        )


__all__ = ["OpenAIDeepResearchAdapter"]
