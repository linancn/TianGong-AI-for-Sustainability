"""
HTTP API clients and adapters for external sustainability data sources.

Each submodule exposes two layers:

* ``Client`` classes wrap low-level HTTP calls with retry logic.
* ``Adapter`` classes provide :class:`~tiangong_ai_for_sustainability.adapters.base.DataSourceAdapter`
  implementations suitable for registry verification or higher-level orchestration.
"""

from .arxiv import ArxivAdapter, ArxivAPIError, ArxivClient
from .base import APIError, BaseAPIClient
from .crossref import CrossrefAdapter, CrossrefClient
from .github_topics import GitHubTopicsAdapter, GitHubTopicsClient
from .kaggle import KaggleAdapter, KaggleAPIError, KaggleClient
from .openalex import OpenAlexAdapter, OpenAlexClient
from .osdg import OSDGAdapter, OSDGClient
from .semantic_scholar import SemanticScholarAdapter, SemanticScholarClient
from .un_sdg import UNSDGAdapter, UNSDGClient

__all__ = [
    "ArxivAdapter",
    "ArxivAPIError",
    "ArxivClient",
    "APIError",
    "BaseAPIClient",
    "CrossrefAdapter",
    "CrossrefClient",
    "GitHubTopicsAdapter",
    "GitHubTopicsClient",
    "KaggleAdapter",
    "KaggleAPIError",
    "KaggleClient",
    "OpenAlexAdapter",
    "OpenAlexClient",
    "OSDGAdapter",
    "OSDGClient",
    "SemanticScholarAdapter",
    "SemanticScholarClient",
    "UNSDGAdapter",
    "UNSDGClient",
]
