"""
Kaggle dataset API client and registry adapter.

The Kaggle platform hosts a significant catalogue of sustainability-related
datasets. The client wrapper keeps interactions deterministic while allowing
credentials to be sourced from the execution context or the standard
``~/.kaggle/kaggle.json`` file.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Tuple

from ..base import AdapterError, DataSourceAdapter, VerificationResult


class KaggleAPIError(AdapterError):
    """Raised when Kaggle API calls fail or the SDK is unavailable."""


@dataclass(slots=True)
class KaggleClient:
    """
    Lightweight Kaggle API client with explicit authentication handling.

    Parameters
    ----------
    username:
        Optional Kaggle username. When provided the value seeds the
        ``KAGGLE_USERNAME`` environment variable prior to authentication.
    key:
        Optional Kaggle API key used to seed ``KAGGLE_KEY``.
    """

    username: Optional[str] = None
    key: Optional[str] = None
    _api: Optional[Any] = field(default=None, init=False, repr=False)
    _authenticated: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        # Deferred import keeps module importable even when kaggle credentials are absent.
        self._api = None

    def authenticate(self) -> None:
        """Authenticate against the Kaggle API if not already done."""

        if self._authenticated:
            return
        api = self._ensure_api()
        try:
            api.authenticate()
        except Exception as exc:  # pragma: no cover - library raises rich error types
            raise KaggleAPIError(f"Failed to authenticate with Kaggle API: {exc}") from exc
        self._authenticated = True

    def dataset_status(self, dataset_ref: str) -> str:
        """Return the status string for a dataset identified by ``owner/dataset``."""

        self.authenticate()
        api = self._ensure_api()
        try:
            status = api.dataset_status(dataset_ref)
        except Exception as exc:
            raise KaggleAPIError(f"Failed to retrieve status for Kaggle dataset '{dataset_ref}': {exc}") from exc

        return status if isinstance(status, str) else str(status)

    def dataset_overview(self, dataset_ref: str) -> Optional[Any]:
        """
        Best-effort metadata lookup for a dataset.

        The Kaggle SDK does not expose a dedicated ``dataset_view`` helper, so
        we query ``dataset_list`` and reconcile the entry manually.
        """

        self.authenticate()
        api = self._ensure_api()
        owner_slug, dataset_slug = self._split_dataset_ref(dataset_ref)
        try:
            results = api.dataset_list(search=dataset_slug, user=owner_slug)
        except Exception as exc:
            raise KaggleAPIError(f"Failed to search Kaggle dataset '{dataset_ref}': {exc}") from exc

        if not results:
            return None

        for entry in results:
            ref, _ = _extract_dataset_details(entry)
            if ref == dataset_ref:
                return entry

        return None

    def list_datasets(
        self,
        *,
        search: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        page_size: int = 20,
    ) -> Any:
        """List datasets matching optional filters."""

        self.authenticate()
        api = self._ensure_api()
        params: dict[str, Any] = {"page_size": max(1, min(page_size, 100))}
        if search:
            params["search"] = search
        if tags:
            params["tag_ids"] = list(tags)
        try:
            return api.dataset_list(**params)
        except Exception as exc:
            raise KaggleAPIError(f"Failed to list Kaggle datasets: {exc}") from exc

    def _apply_credentials(self) -> None:
        if self.username:
            os.environ["KAGGLE_USERNAME"] = self.username
        if self.key:
            os.environ["KAGGLE_KEY"] = self.key

    @staticmethod
    def _split_dataset_ref(dataset_ref: str) -> Tuple[str, str]:
        if "/" not in dataset_ref:
            raise KaggleAPIError("Dataset reference must be in the form 'owner/dataset'.")
        owner, dataset = dataset_ref.split("/", 1)
        if not owner or not dataset:
            raise KaggleAPIError("Dataset reference must include both owner and dataset slugs.")
        return owner, dataset

    def _ensure_api(self) -> Any:
        if self._api is not None:
            return self._api
        self._apply_credentials()
        try:
            module = importlib.import_module("kaggle.api.kaggle_api_extended")
        except ImportError as exc:  # pragma: no cover - depends on runtime environment
            raise KaggleAPIError("kaggle package is not installed. Install it with 'uv add kaggle==1.7.4.5'.") from exc
        except Exception as exc:  # pragma: no cover - e.g. missing credentials during import
            raise KaggleAPIError(f"Failed to import Kaggle API module: {exc}") from exc

        api_cls = getattr(module, "KaggleApi", None)
        if api_cls is None:
            raise KaggleAPIError("Installed kaggle package does not expose KaggleApi class.")

        try:
            api = api_cls()
        except Exception as exc:  # pragma: no cover - instantiation errors are upstream-specific
            raise KaggleAPIError(f"Failed to initialise Kaggle API client: {exc}") from exc

        self._api = api
        return api


def _extract_dataset_details(payload: Any) -> tuple[Optional[str], Optional[str]]:
    ref: Optional[str] = None
    title: Optional[str] = None

    if isinstance(payload, dict):
        ref = payload.get("ref") or payload.get("id")
        raw_title = payload.get("title") or payload.get("name")
        if isinstance(raw_title, str) and raw_title:
            title = raw_title
    else:
        ref = getattr(payload, "ref", None) or getattr(payload, "id", None)
        raw_title = getattr(payload, "title", None) or getattr(payload, "name", None)
        if isinstance(raw_title, str) and raw_title:
            title = raw_title

    return ref, title


@dataclass(slots=True)
class KaggleAdapter(DataSourceAdapter):
    """Adapter used for registry verification and metadata checks."""

    source_id: str = "kaggle"
    client: KaggleClient = field(default_factory=KaggleClient)
    verification_dataset: str = "zynicide/wine-reviews"

    def verify(self) -> VerificationResult:
        try:
            payload = self.client.dataset_overview(self.verification_dataset)
        except KaggleAPIError as exc:
            return VerificationResult(
                success=False,
                message=f"Kaggle API verification failed: {exc}",
            )

        if not payload:
            return VerificationResult(
                success=False,
                message=("Kaggle API verification failed: dataset '" f"{self.verification_dataset}' not found or inaccessible."),
            )

        dataset_ref, dataset_title = _extract_dataset_details(payload)
        details = {"dataset": dataset_ref or self.verification_dataset}
        if dataset_title:
            details["title"] = dataset_title

        try:
            status = self.client.dataset_status(self.verification_dataset)
        except KaggleAPIError as exc:
            details["status_error"] = str(exc)
        else:
            details["status"] = status

        if dataset_ref and dataset_ref != self.verification_dataset:
            details["dataset"] = dataset_ref

        return VerificationResult(
            success=True,
            message="Kaggle API reachable.",
            details=details,
        )
