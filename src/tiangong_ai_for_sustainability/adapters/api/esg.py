"""
Adapters for licensed ESG data providers.

These sources require commercial credentials, so verification focuses on
confirming that API keys are configured. This keeps the CLI deterministic while
surfacing clear guidance for operators.
"""

from __future__ import annotations

from typing import Optional

from ..base import DataSourceAdapter, VerificationResult


class LicensedESGAdapter(DataSourceAdapter):
    """Base class for credential-gated ESG data providers."""

    source_id: str
    display_name: str
    env_var: str

    def __init__(self, *, api_key: Optional[str] = None) -> None:
        self.api_key = api_key

    def _missing_credentials_message(self) -> str:
        return (
            f"{self.display_name} credentials are not configured. Add an [" f"{self.source_id}] api_key entry to .secrets/secrets.toml or set " f"{self.env_var} before running this command."
        )

    def verify(self) -> VerificationResult:
        if not self.api_key:
            return VerificationResult(
                success=False,
                message=self._missing_credentials_message(),
            )

        return VerificationResult(
            success=True,
            message=f"{self.display_name} credentials detected; upstream access requires licensed ingestion workflows.",
            details={"credential_present": True},
        )


class CdpClimateAdapter(LicensedESGAdapter):
    source_id = "cdp_climate"
    display_name = "CDP Climate Disclosure Dashboard"
    env_var = "TIANGONG_CDP_API_KEY"


class LsegESGAdapter(LicensedESGAdapter):
    source_id = "lseg_esg"
    display_name = "LSEG Refinitiv ESG Data"
    env_var = "TIANGONG_LSEG_API_KEY"


class MsciESGAdapter(LicensedESGAdapter):
    source_id = "msci_esg"
    display_name = "MSCI ESG Research"
    env_var = "TIANGONG_MSCI_API_KEY"


class SustainalyticsAdapter(LicensedESGAdapter):
    source_id = "sustainalytics"
    display_name = "Sustainalytics ESG Risk Ratings"
    env_var = "TIANGONG_SUSTAINALYTICS_API_KEY"


class SpGlobalESGAdapter(LicensedESGAdapter):
    source_id = "sp_global_esg"
    display_name = "S&P Global Sustainable1"
    env_var = "TIANGONG_SPGLOBAL_API_KEY"


class IssESGAdapter(LicensedESGAdapter):
    source_id = "iss_esg"
    display_name = "ISS ESG Data"
    env_var = "TIANGONG_ISS_API_KEY"
