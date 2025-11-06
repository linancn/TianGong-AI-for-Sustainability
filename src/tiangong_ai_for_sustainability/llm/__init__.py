"""
LLM-related helpers and clients used by TianGong automation workflows.

The ``openai_deep_research`` module exposes ``DeepResearchClient`` and supporting
dataclasses that wrap the OpenAI Deep Research Responses API.
"""

from .openai_deep_research import (
    DEFAULT_DEEP_RESEARCH_MODEL,
    DeepResearchClient,
    DeepResearchConfig,
    DeepResearchResult,
    FileSearchConfig,
    MCPServerConfig,
    ResearchPrompt,
)

__all__ = [
    "DEFAULT_DEEP_RESEARCH_MODEL",
    "DeepResearchClient",
    "DeepResearchConfig",
    "DeepResearchResult",
    "FileSearchConfig",
    "MCPServerConfig",
    "ResearchPrompt",
]
