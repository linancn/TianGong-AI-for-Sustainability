"""
UN SDG API client and adapter.

Documentation: https://unstats.un.org/SDGAPI/swagger/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://unstats.un.org/SDGAPI/v1"


class UNSDGClient(BaseAPIClient):
    """Lightweight wrapper around the UNSD SDG v1 API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 20.0) -> None:
        super().__init__(base_url=base_url, timeout=timeout)

    def list_goals(self) -> List[Dict[str, Any]]:
        data = self._get_json("/sdg/Goal/List")
        if not isinstance(data, list):
            raise APIError("Unexpected payload format for Goal/List.")
        return data

    def list_targets(self, goal_code: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"goal": goal_code} if goal_code else None
        data = self._get_json("/sdg/Target/List", params=params)
        if not isinstance(data, list):
            raise APIError("Unexpected payload format for Target/List.")
        return data

    def list_indicators(self, target_code: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"target": target_code} if target_code else None
        data = self._get_json("/sdg/Indicator/List", params=params)
        if not isinstance(data, list):
            raise APIError("Unexpected payload format for Indicator/List.")
        return data


@dataclass(slots=True)
class UNSDGAdapter(DataSourceAdapter):
    """Adapter used for registry verification."""

    source_id: str = "un_sdg_api"
    client: UNSDGClient = field(default_factory=UNSDGClient)

    def verify(self) -> VerificationResult:
        try:
            goals = self.client.list_goals()
        except APIError as exc:
            return VerificationResult(success=False, message=f"UN SDG API verification failed: {exc}")

        if not goals:
            return VerificationResult(success=False, message="UN SDG API returned an empty goal list.")

        sample_goal = goals[0]
        code = sample_goal.get("code", "unknown")
        title = sample_goal.get("title", "N/A")
        return VerificationResult(
            success=True,
            message=f"UN SDG API reachable. Sample goal {code}: {title}",
            details={"goal_count": len(goals)},
        )
