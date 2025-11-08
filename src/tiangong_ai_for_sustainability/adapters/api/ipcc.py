"""
Adapter for the IPCC Data Distribution Centre.

The DDC publishes datasets through a dedicated Zenodo community
(`ipcc-ddc`). We use the public Zenodo API to perform a deterministic health
check without downloading large artefacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError
from .zenodo import ZenodoCommunityClient, extract_record_doi


@dataclass(slots=True)
class IPCCDDCAdapter(DataSourceAdapter):
    """Registry adapter for the IPCC DDC source."""

    source_id: str = "ipcc_ddc"
    community_id: str = "ipcc-ddc"
    client: ZenodoCommunityClient = field(default_factory=ZenodoCommunityClient)

    def verify(self) -> VerificationResult:
        try:
            records = self.client.list_recent_records(self.community_id, size=1)
        except APIError as exc:
            return VerificationResult(success=False, message=f"IPCC DDC verification failed: {exc}")

        if not records:
            return VerificationResult(success=False, message="IPCC DDC community returned no records.")

        record: Mapping[str, object] = records[0]
        title = self.client.fetch_latest_title(self.community_id)
        doi = extract_record_doi(record)

        details = {}
        if title:
            details["latest_title"] = title
        if doi:
            details["doi"] = doi

        return VerificationResult(
            success=True,
            message="IPCC DDC community reachable via Zenodo.",
            details=details or None,
        )
