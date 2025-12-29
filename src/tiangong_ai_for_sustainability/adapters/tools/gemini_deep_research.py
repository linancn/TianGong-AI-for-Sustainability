"""
Adapter for verifying Gemini Deep Research availability.

The adapter performs static credential checks to keep verification
deterministic. Actual orchestration is handled by
``tiangong_ai_for_sustainability.llm.gemini_deep_research``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from logging import LoggerAdapter

from ...config import DEFAULT_GEMINI_AGENT, DEFAULT_GEMINI_ENDPOINT, GeminiSettings
from ...core.logging import get_logger
from ..base import DataSourceAdapter, VerificationResult


@dataclass(slots=True)
class GeminiDeepResearchAdapter(DataSourceAdapter):
    """Check whether Gemini Deep Research can be invoked with available secrets."""

    settings: GeminiSettings | None = None
    source_id: str = field(init=False, default="gemini_deep_research")
    logger: LoggerAdapter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    def verify(self) -> VerificationResult:
        """
        Confirm required credentials for Gemini Deep Research are present.

        Verification avoids live network calls and instead checks for an API
        key plus the configured agent identifier.
        """

        settings = self.settings or GeminiSettings()
        api_key = settings.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.logger.warning("Gemini API key missing for Deep Research source")
            return VerificationResult(
                success=False,
                message=(
                    "Gemini API key is not configured. Populate the [gemini] section in .secrets/secrets.toml "
                    "or set GOOGLE_API_KEY/GEMINI_API_KEY before enabling the 'gemini_deep_research' source."
                ),
            )

        agent = settings.agent or DEFAULT_GEMINI_AGENT
        endpoint = (settings.api_endpoint or DEFAULT_GEMINI_ENDPOINT).rstrip("/")
        self.logger.debug("Gemini Deep Research credentials detected", extra={"agent": agent, "endpoint": endpoint})
        return VerificationResult(
            success=True,
            message=f"Gemini Deep Research ready (agent '{agent}').",
            details={"agent": agent, "endpoint": endpoint},
        )


__all__ = ["GeminiDeepResearchAdapter"]
