"""
Shared HTTP utilities for API adapters.

The helper provides a thin HTTPX wrapper with retry logic tuned for
specification-driven automation: it keeps the code synchronous, avoids global
state, and surfaces rich error messages when endpoints fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import LoggerAdapter
from typing import Any, Mapping, MutableMapping, Optional

import httpx
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ...core.logging import get_logger
from ..base import AdapterError

DEFAULT_TIMEOUT = 15.0


class APIError(AdapterError):
    """Raised when an HTTP API call fails."""


@dataclass(slots=True)
class BaseAPIClient:
    """
    Base synchronous HTTP client with retry support.

    Parameters
    ----------
    base_url:
        Root URL for the upstream service.
    timeout:
        Request timeout in seconds.
    default_headers:
        Headers automatically attached to every request.
    """

    base_url: str
    timeout: float = DEFAULT_TIMEOUT
    default_headers: MutableMapping[str, str] = field(default_factory=dict)
    logger: LoggerAdapter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.logger = get_logger(
            f"{self.__class__.__module__}.{self.__class__.__name__}",
            extra={"base_url": self.base_url},
        )

    def _build_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=dict(self.default_headers),
            follow_redirects=True,
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - library-provided
            raise APIError(f"HTTP {exc.response.status_code} error for {exc.request.method} {exc.request.url}: {exc.response.text}") from exc

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        self.logger.debug(
            "HTTP request",
            extra={
                "method": method,
                "url": url,
                "params": kwargs.get("params"),
            },
        )

        @retry(
            retry=retry_if_exception_type(httpx.HTTPError),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            stop=stop_after_attempt(3),
            reraise=True,
        )
        def _send() -> httpx.Response:
            with self._build_client() as client:
                return client.request(method, url, **kwargs)

        try:
            response = _send()
        except RetryError as exc:
            self.logger.error(
                "HTTP request failed after retries",
                extra={"method": method, "url": url, "error": str(exc)},
            )
            raise APIError(f"Failed to call {method} {url} after multiple attempts: {exc}") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - retry handles most
            self.logger.error(
                "HTTP error during request",
                extra={"method": method, "url": url, "error": str(exc)},
            )
            raise APIError(f"HTTP error while calling {method} {url}: {exc}") from exc

        self._raise_for_status(response)
        self.logger.debug(
            "HTTP response",
            extra={
                "status_code": response.status_code,
                "url": str(response.url),
            },
        )
        return response

    def _get_json(self, url: str, *, params: Optional[Mapping[str, Any]] = None) -> Any:
        response = self._request("GET", url, params=params)
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - depends on upstream
            raise APIError(f"Failed to decode JSON from {response.url}: {exc}") from exc

    def _post_json(
        self,
        url: str,
        *,
        json_body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        merged_headers: MutableMapping[str, str] = dict(self.default_headers)
        if headers:
            merged_headers.update(headers)
        response = self._request("POST", url, json=json_body, headers=merged_headers)
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - depends on upstream
            raise APIError(f"Failed to decode JSON from {response.url}: {exc}") from exc
