"""
Adapter for the Wikidata SPARQL endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

from ..base import DataSourceAdapter, VerificationResult
from .base import APIError, BaseAPIClient

DEFAULT_BASE_URL = "https://query.wikidata.org"
SAMPLE_QUERY = """
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q6256 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 1
"""


class WikidataClient(BaseAPIClient):
    """HTTP client for the Wikidata SPARQL endpoint."""

    def __init__(self, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 20.0) -> None:
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "tiangong-ai-sustainability-cli",
        }
        super().__init__(base_url=base_url, timeout=timeout, default_headers=headers)

    def run_query(self, query: str) -> List[Mapping[str, Any]]:
        payload = self._get_json(
            "/sparql",
            params={
                "format": "json",
                "query": query,
            },
        )
        if not isinstance(payload, Mapping):
            raise APIError("Unexpected payload from Wikidata SPARQL endpoint.")
        results = payload.get("results")
        if not isinstance(results, Mapping):
            raise APIError("Wikidata SPARQL payload missing 'results' section.")
        bindings = results.get("bindings")
        if not isinstance(bindings, list):
            raise APIError("Wikidata SPARQL payload missing 'bindings' list.")
        normalised: List[Mapping[str, Any]] = []
        for entry in bindings:
            if isinstance(entry, Mapping):
                normalised.append(entry)
        return normalised


@dataclass(slots=True)
class WikidataAdapter(DataSourceAdapter):
    """Registry adapter for the Wikidata SPARQL endpoint."""

    source_id: str = "wikidata"
    client: WikidataClient = field(default_factory=WikidataClient)
    sample_query: str = SAMPLE_QUERY.strip()

    def verify(self) -> VerificationResult:
        try:
            bindings = self.client.run_query(self.sample_query)
        except APIError as exc:
            return VerificationResult(success=False, message=f"Wikidata verification failed: {exc}")

        if not bindings:
            return VerificationResult(success=False, message="Wikidata SPARQL query returned no results.")

        record = bindings[0]
        item_label = self._extract_value(record, "itemLabel")
        item_value = self._extract_value(record, "item")

        details = {}
        if item_value:
            details["sample_item"] = item_value
        if item_label:
            details["sample_label"] = item_label

        return VerificationResult(
            success=True,
            message="Wikidata SPARQL endpoint reachable.",
            details=details or None,
        )

    @staticmethod
    def _extract_value(binding: Mapping[str, Any], key: str) -> Optional[str]:
        slot = binding.get(key)
        if isinstance(slot, Mapping):
            value = slot.get("value")
            if isinstance(value, str):
                return value
        return None
