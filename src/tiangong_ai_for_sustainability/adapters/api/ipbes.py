"""
Adapter for the IPBES Knowledge and Data Portal.

IPBES distributes assessment artefacts and supplementary material through the
`ipbes` Zenodo community. The adapter reuses the shared Zenodo client to verify
that recent records are accessible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError
from .zenodo import ZenodoCommunityClient, extract_record_doi


@dataclass(slots=True)
class IPBESAdapter(DataSourceAdapter):
    """Registry adapter for the IPBES data portal."""

    source_id: str = "ipbes_data_portal"
    community_id: str = "ipbes"
    client: ZenodoCommunityClient = field(default_factory=ZenodoCommunityClient)

    def verify(self) -> VerificationResult:
        try:
            records = self.client.list_recent_records(self.community_id, size=1)
        except APIError as exc:
            return VerificationResult(success=False, message=f"IPBES verification failed: {exc}")

        if not records:
            return VerificationResult(success=False, message="IPBES community returned no records.")

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
            message="IPBES community reachable via Zenodo.",
            details=details or None,
        )
