"""
Adapter for the ILOSTAT SDMX API.

The public SDMX endpoint exposes a catalogue of datasets that can be requested
without credentials. The adapter performs a lightweight catalogue fetch and
reports the first dataset identifier to confirm availability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://www.ilo.org/ilostat/sdmx/ws/public/sdmxapi/rest/v2"


class ILOSTATClient(BaseAPIClient):
    """Client for the ILOSTAT SDMX REST API."""

    def __init__(self, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0) -> None:
        headers = {
            "Accept": "application/json",
            "User-Agent": "tiangong-ai-sustainability-cli",
        }
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def list_datasets(self) -> List[Mapping[str, Any]]:
        response = self._request("GET", "/catalogue/datasets", params={"format": "json"})
        try:
            payload = response.json()
        except ValueError as exc:
            body = response.text
            if "Just a moment" in body:
                raise APIError("ILOSTAT responded with a Cloudflare challenge; access requires manual verification.") from exc
            raise APIError(f"Failed to decode ILOSTAT dataset catalogue: {exc}") from exc

        datasets: Optional[List[Any]] = None
        if isinstance(payload, Mapping):
            maybe_list = payload.get("datasets") or payload.get("value")
            if isinstance(maybe_list, list):
                datasets = maybe_list
        elif isinstance(payload, list):
            datasets = payload

        if not datasets:
            raise APIError("ILOSTAT catalogue response did not include any datasets.")

        results: List[Mapping[str, Any]] = []
        for entry in datasets:
            if isinstance(entry, Mapping):
                results.append(entry)

        if not results:
            raise APIError("ILOSTAT catalogue returned no structured dataset entries.")
        return results


def _dataset_identifier(entry: Mapping[str, Any]) -> Optional[str]:
    for key in ("id", "datasetCode", "datasetID", "code", "Identifier"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _dataset_label(entry: Mapping[str, Any]) -> Optional[str]:
    for key in ("name", "description", "Title", "title"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


@dataclass(slots=True)
class ILOSTATAdapter(DataSourceAdapter):
    """Registry adapter for the ILOSTAT API."""

    source_id: str = "ilostat"
    client: ILOSTATClient = field(default_factory=ILOSTATClient)

    def verify(self) -> VerificationResult:
        try:
            datasets = self.client.list_datasets()
        except APIError as exc:
            return VerificationResult(success=False, message=f"ILOSTAT verification failed: {exc}")

        sample = datasets[0]
        identifier = _dataset_identifier(sample)
        label = _dataset_label(sample)

        details = {}
        if identifier:
            details["dataset_id"] = identifier
        if label:
            details["dataset_label"] = label

        return VerificationResult(
            success=True,
            message="ILOSTAT SDMX catalogue reachable.",
            details=details or None,
        )
