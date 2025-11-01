"""
HTTP API clients and adapters for external sustainability data sources.

Each submodule exposes two layers:

* ``Client`` classes wrap low-level HTTP calls with retry logic.
* ``Adapter`` classes provide :class:`~tiangong_ai_for_sustainability.adapters.base.DataSourceAdapter`
  implementations suitable for registry verification or higher-level orchestration.
"""

from .base import APIError, BaseAPIClient
from .github_topics import GitHubTopicsAdapter, GitHubTopicsClient
from .osdg import OSDGAdapter, OSDGClient
from .semantic_scholar import SemanticScholarAdapter, SemanticScholarClient
from .un_sdg import UNSDGAdapter, UNSDGClient

__all__ = [
    "APIError",
    "BaseAPIClient",
    "GitHubTopicsAdapter",
    "GitHubTopicsClient",
    "OSDGAdapter",
    "OSDGClient",
    "SemanticScholarAdapter",
    "SemanticScholarClient",
    "UNSDGAdapter",
    "UNSDGClient",
]
