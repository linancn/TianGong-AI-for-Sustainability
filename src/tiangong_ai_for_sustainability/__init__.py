"""
Convenience utilities for orchestrating OpenAI Deep Research workflows.

The :mod:`tiangong_ai_for_sustainability.deep_research` module exposes strongly typed
helpers that wrap the OpenAI Responses API and provide optional Model Context Protocol
integration hooks. Import ``DeepResearchClient`` for the main developer-facing surface.
"""

from .deep_research import DeepResearchClient, DeepResearchConfig, MCPServerConfig, ResearchPrompt

__all__ = ["DeepResearchClient", "DeepResearchConfig", "MCPServerConfig", "ResearchPrompt"]
