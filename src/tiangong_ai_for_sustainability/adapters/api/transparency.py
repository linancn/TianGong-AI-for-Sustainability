"""
Adapter for Transparency International's Corruption Perceptions Index.

Transparency International publishes historic CPI scores as an openly licensed
CSV on DataHub. The adapter downloads the dataset header and first record to
confirm availability.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Dict

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://raw.githubusercontent.com"
DATASET_PATH = "/datasets/corruption-perceptions-index/master/data/cpi.csv"


class TransparencyCPIClient(BaseAPIClient):
    """Client for the mirrored Transparency International CPI dataset."""

    def __init__(self, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0) -> None:
        headers = {"User-Agent": "tiangong-ai-sustainability-cli"}
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def fetch_sample_row(self) -> Dict[str, str]:
        response = self._request("GET", DATASET_PATH)
        text = response.text
        stream = io.StringIO(text)
        reader = csv.DictReader(stream)
        try:
            row = next(reader)
        except StopIteration as exc:
            raise APIError("Transparency International CPI dataset returned no rows.") from exc
        if not isinstance(row, dict):
            raise APIError("Unexpected row structure in CPI dataset.")
        return row


@dataclass(slots=True)
class TransparencyCPIAdapter(DataSourceAdapter):
    """Registry adapter for the Transparency International CPI."""

    source_id: str = "transparency_international_cpi"
    client: TransparencyCPIClient = field(default_factory=TransparencyCPIClient)

    def verify(self) -> VerificationResult:
        try:
            row = self.client.fetch_sample_row()
        except APIError as exc:
            return VerificationResult(success=False, message=f"Transparency International CPI verification failed: {exc}")

        country = row.get("country") or row.get("Country")
        sample_year = None
        for key in ("2023", "2022", "2021", "2020"):
            if key in row and row[key]:
                sample_year = key
                break

        details = {}
        if country:
            details["sample_country"] = country
        if sample_year:
            details["sample_year"] = sample_year
            details["sample_score"] = row[sample_year]

        return VerificationResult(
            success=True,
            message="Transparency International CPI dataset reachable (DataHub mirror).",
            details=details or None,
        )
