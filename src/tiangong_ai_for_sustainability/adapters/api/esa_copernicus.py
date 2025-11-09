"""
Copernicus Data Space Ecosystem metadata adapter.

The Dataspace RESTO API supersedes the legacy SciHub endpoints and provides
anonymous access to catalogue metadata. This adapter issues a lightweight
search to confirm availability; authenticated downloads can be layered on top
when operator credentials are configured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://catalogue.dataspace.copernicus.eu/resto"


class CopernicusDataspaceClient(BaseAPIClient):
    """Client for Copernicus Dataspace RESTO metadata search."""

    def __init__(self, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 20.0) -> None:
        headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def search_collection(
        self,
        *,
        collection: str,
        product_type: Optional[str] = None,
        max_records: int = 5,
    ) -> Dict[str, Any]:
        """
        Query a specific collection via the RESTO search API.

        Parameters
        ----------
        collection:
            Collection identifier such as ``Sentinel2``.
        product_type:
            Optional product type filter (e.g. ``S2MSI1C``).
        max_records:
            Maximum results to return (bounded between 1 and 100).
        """

        params: Dict[str, Any] = {"maxRecords": max(1, min(max_records, 100))}
        if product_type:
            params["productType"] = product_type
        path = f"/api/collections/{collection}/search.json"
        payload = self._get_json(path, params=params)
        if not isinstance(payload, dict):
            raise APIError("Unexpected response type from Copernicus Dataspace search.")
        return payload


def _extract_first_feature(payload: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """Return the first GeoJSON feature from a RESTO payload, if available."""

    features = payload.get("features")
    if isinstance(features, list):
        for feature in features:
            if isinstance(feature, Mapping):
                return feature
    return None


@dataclass(slots=True)
class CopernicusDataspaceAdapter(DataSourceAdapter):
    """Adapter used for registry verification of the Copernicus catalogue."""

    source_id: str = "esa_copernicus"
    client: CopernicusDataspaceClient = field(default_factory=CopernicusDataspaceClient)
    verification_collection: str = "Sentinel2"
    verification_product_type: str = "S2MSI1C"

    def verify(self) -> VerificationResult:
        try:
            payload = self.client.search_collection(
                collection=self.verification_collection,
                product_type=self.verification_product_type,
                max_records=1,
            )
        except APIError as exc:
            return VerificationResult(
                success=False,
                message=f"Copernicus Dataspace verification failed: {exc}",
            )

        feature = _extract_first_feature(payload)
        if feature is None:
            return VerificationResult(
                success=False,
                message="Copernicus Dataspace verification failed: search returned no features.",
            )

        properties = feature.get("properties")
        details: Dict[str, Any] = {}
        if isinstance(properties, Mapping):
            product_identifier = properties.get("productIdentifier")
            product_type = properties.get("productType")
            if isinstance(product_identifier, str):
                details["product_identifier"] = product_identifier
            if isinstance(product_type, str):
                details["product_type"] = product_type

        return VerificationResult(
            success=True,
            message="Copernicus Dataspace RESTO catalogue reachable.",
            details=details or None,
        )
