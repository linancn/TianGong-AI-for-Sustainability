"""
Adapter interfaces for external data sources and storage backends.

Concrete adapters live in submodules keyed by data source type. Each adapter is
responsible for a small, deterministic surface that can be composed by the
service layer.
"""

from .base import AdapterError, DataSourceAdapter, VerificationResult
from .tools import ChartMCPAdapter, OpenAIDeepResearchAdapter, RemoteMCPAdapter

__all__ = [
    "AdapterError",
    "DataSourceAdapter",
    "VerificationResult",
    "ChartMCPAdapter",
    "RemoteMCPAdapter",
    "OpenAIDeepResearchAdapter",
]
