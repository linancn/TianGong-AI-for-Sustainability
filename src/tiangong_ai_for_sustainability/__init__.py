"""
Convenience utilities for orchestrating LLM-assisted research workflows.

The :mod:`tiangong_ai_for_sustainability.llm.openai_deep_research` module exposes strongly typed
helpers that wrap the OpenAI Responses API and provide optional Model Context Protocol
integration hooks. Import ``DeepResearchClient`` for the main developer-facing surface.

The :mod:`tiangong_ai_for_sustainability.llm.gemini_deep_research` module offers a
minimal client for Gemini Deep Research via the Interactions API.
"""

from .llm import (
    DeepResearchClient,
    DeepResearchConfig,
    DeepResearchResult,
    GeminiDeepResearchClient,
    GeminiDeepResearchError,
    MCPServerConfig,
    ResearchPrompt,
)

__all__ = [
    "DeepResearchClient",
    "DeepResearchConfig",
    "DeepResearchResult",
    "GeminiDeepResearchClient",
    "GeminiDeepResearchError",
    "MCPServerConfig",
    "ResearchPrompt",
]
