"""
Adapters for premium scholarly content providers that require API credentials.

These integrations will be fleshed out once licensed access is provisioned.
For now we detect API key configuration to surface clear guidance in the CLI.
"""

from __future__ import annotations

from typing import Optional

from ..base import DataSourceAdapter, VerificationResult


class CredentialPresenceAdapter(DataSourceAdapter):
    """Base adapter that validates the presence of an API key."""

    source_id: str
    display_name: str
    env_var: str

    def __init__(self, *, api_key: Optional[str] = None) -> None:
        self.api_key = api_key

    def _missing_message(self) -> str:
        return f"{self.display_name} API credentials are not configured. Add an [{self.source_id}] api_key " f"entry to .secrets/secrets.toml or set {self.env_var}."

    def verify(self) -> VerificationResult:
        if not self.api_key:
            return VerificationResult(success=False, message=self._missing_message())

        return VerificationResult(
            success=True,
            message=f"{self.display_name} API credentials detected. Licensed data ingestion remains pending.",
            details={"credential_present": True},
        )


class AcmDigitalLibraryAdapter(CredentialPresenceAdapter):
    source_id = "acm_digital_library"
    display_name = "ACM Digital Library"
    env_var = "TIANGONG_ACM_API_KEY"


class ScopusAdapter(CredentialPresenceAdapter):
    source_id = "scopus"
    display_name = "Elsevier Scopus"
    env_var = "TIANGONG_SCOPUS_API_KEY"


class WebOfScienceAdapter(CredentialPresenceAdapter):
    source_id = "web_of_science"
    display_name = "Web of Science"
    env_var = "TIANGONG_WOS_API_KEY"
