"""
Helpers for orchestrating Gemini Deep Research interactions.

The Gemini Interactions API exposes a Deep Research agent that can be launched
asynchronously and polled for completion. This module wraps the relevant REST
endpoints with small ergonomic helpers and avoids network calls at import time
so it can be used safely in tooling and tests without configured credentials.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Optional, Sequence

import httpx

from ..config import DEFAULT_GEMINI_AGENT, DEFAULT_GEMINI_ENDPOINT, GeminiSettings, SecretsBundle, load_secrets
from ..core.logging import get_logger

__all__ = ["GeminiDeepResearchClient", "GeminiDeepResearchError"]


class GeminiDeepResearchError(RuntimeError):
    """Raised when Gemini Deep Research calls fail."""


@dataclass(slots=True)
class GeminiDeepResearchClient:
    """Lightweight wrapper around the Gemini Deep Research Interactions API."""

    settings: Optional[GeminiSettings] = None
    secrets: Optional[SecretsBundle] = None
    http_client: Optional[httpx.Client] = None
    timeout: float = 30.0
    logger: Any = field(init=False, repr=False)
    _config: GeminiSettings = field(init=False, repr=False)
    _base_url: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        resolved_secrets = self.secrets or load_secrets()
        settings = self.settings or getattr(resolved_secrets, "gemini", None) or GeminiSettings()

        api_key = settings.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise GeminiDeepResearchError(
                "Gemini API key is not configured. Add a [gemini] section to .secrets/secrets.toml " "or set GOOGLE_API_KEY/GEMINI_API_KEY before enabling the 'gemini_deep_research' source."
            )

        agent = settings.agent or DEFAULT_GEMINI_AGENT
        base_url = (settings.api_endpoint or DEFAULT_GEMINI_ENDPOINT).rstrip("/")
        object.__setattr__(self, "_config", GeminiSettings(api_key=api_key, agent=agent, api_endpoint=base_url))
        object.__setattr__(self, "_base_url", base_url)
        object.__setattr__(self, "secrets", resolved_secrets)

    def start_research(
        self,
        prompt: str,
        *,
        agent: str | None = None,
        file_search_stores: Sequence[str] | None = None,
        include_thinking_summaries: bool = True,
    ) -> Mapping[str, Any]:
        """
        Launch a Deep Research interaction in the background.

        The Interactions API requires both ``background`` and ``store`` to be
        ``True`` when launching asynchronous Deep Research runs.
        """

        if not prompt or not str(prompt).strip():
            raise GeminiDeepResearchError("Prompt cannot be empty.")

        payload: MutableMapping[str, Any] = {
            "input": prompt,
            "agent": agent or self._config.agent or DEFAULT_GEMINI_AGENT,
            "background": True,
            "store": True,
        }
        if file_search_stores:
            payload["tools"] = [
                {
                    "type": "file_search",
                    "file_search_store_names": list(file_search_stores),
                }
            ]
        if include_thinking_summaries:
            payload["agent_config"] = {
                "type": "deep-research",
                "thinking_summaries": "auto",
            }

        self.logger.debug("Starting Gemini Deep Research interaction", extra={"agent": payload.get("agent")})
        response = self._post(self._interactions_url(), headers=self._headers(), json=payload)
        interaction = self._parse_json_response(response)
        return {
            "interaction": interaction,
            "interaction_id": interaction.get("id"),
            "status": interaction.get("status"),
        }

    def get_interaction(self, interaction_id: str) -> Mapping[str, Any]:
        """Fetch the latest state for a Deep Research interaction."""

        if not interaction_id or not str(interaction_id).strip():
            raise GeminiDeepResearchError("Interaction ID cannot be empty.")

        url = f"{self._interactions_url()}/{interaction_id}"
        response = self._get(url, headers=self._headers())
        interaction = self._parse_json_response(response)
        return {
            "interaction": interaction,
            "interaction_id": interaction.get("id") or interaction_id,
            "status": interaction.get("status"),
        }

    def poll_until_complete(
        self,
        interaction_id: str,
        *,
        interval: float = 10.0,
        max_attempts: int = 360,
    ) -> Mapping[str, Any]:
        """
        Poll an interaction until it completes or fails.

        Raises:
            GeminiDeepResearchError: when the interaction fails or the attempt
            limit is exceeded.
        """

        attempts = 0
        while True:
            attempts += 1
            interaction = self.get_interaction(interaction_id)
            status = str(interaction.get("status") or "").lower()
            if status == "completed":
                return interaction
            if status == "failed":
                error_detail = interaction.get("interaction", {}).get("error") or interaction.get("error") or {}
                raise GeminiDeepResearchError(f"Interaction {interaction_id} failed: {error_detail}")
            if attempts >= max_attempts:
                raise GeminiDeepResearchError(f"Interaction {interaction_id} did not complete after {attempts} polls.")
            time.sleep(interval)

    # ------------------------------------------------------------------ internals

    def _headers(self) -> Mapping[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self._config.api_key or "",
        }

    def _interactions_url(self) -> str:
        return f"{self._base_url}/v1beta/interactions"

    def _parse_json_response(self, response: httpx.Response) -> Mapping[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self.logger.exception("Gemini Deep Research request failed")
            raise GeminiDeepResearchError(f"HTTP error calling Gemini Interactions API: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive fallback
            raise GeminiDeepResearchError("Gemini Interactions API returned invalid JSON.") from exc

    def _post(self, url: str, *, headers: Mapping[str, str], json: Mapping[str, Any]) -> httpx.Response:
        if self.http_client is not None:
            return self.http_client.post(url, headers=headers, json=json, timeout=self.timeout)
        return httpx.post(url, headers=headers, json=json, timeout=self.timeout)

    def _get(self, url: str, *, headers: Mapping[str, str]) -> httpx.Response:
        if self.http_client is not None:
            return self.http_client.get(url, headers=headers, timeout=self.timeout)
        return httpx.get(url, headers=headers, timeout=self.timeout)
