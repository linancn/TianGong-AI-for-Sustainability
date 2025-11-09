"""
Adapter for the Google Earth Engine CLI.

The Earth Engine platform requires credential provisioning, but the official
``earthengine`` CLI is available for metadata lookups and script execution.
This adapter focuses on deterministic availability checks so workflows can
surface actionable guidance when the CLI is missing or not authenticated.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from logging import LoggerAdapter
from typing import Optional

from ...core.logging import get_logger
from ..base import AdapterError, DataSourceAdapter, VerificationResult


@dataclass(slots=True)
class GoogleEarthEngineCLIAdapter(DataSourceAdapter):
    """Minimal subprocess wrapper for the ``earthengine`` CLI."""

    source_id: str = "google_earth_engine"
    executable: str = "earthengine"
    logger: LoggerAdapter = field(init=False, repr=False)

    CLI_ENV_VAR = "EARTHENGINE_CLI"

    def __post_init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        override = self._environment_override()
        if override:
            self.executable = override
            self.logger.debug(
                "Using Google Earth Engine CLI override from environment",
                extra={"executable": self.executable},
            )

    def _environment_override(self) -> Optional[str]:
        from os import environ

        value = environ.get(self.CLI_ENV_VAR)
        if value:
            return value
        return None

    def verify(self) -> VerificationResult:
        """
        Check whether the Earth Engine CLI is available on ``PATH``.

        The command does not attempt authenticated calls. Operators will still
        need to run ``earthengine authenticate`` separately when credentials are
        required for API access.
        """

        if shutil.which(self.executable) is None:
            self.logger.warning("earthengine CLI missing from PATH")
            return VerificationResult(
                success=False,
                message=(
                    "earthengine CLI is not installed or discoverable on PATH. Install the "
                    "official Earth Engine Python package (`pip install earthengine-api`), run "
                    "`earthengine authenticate`, and ensure the executable is available on PATH or "
                    f"set {self.CLI_ENV_VAR} to its location."
                ),
            )

        try:
            completed = subprocess.run(
                [self.executable, "--help"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
        except OSError as exc:  # pragma: no cover - depends on runtime environment
            self.logger.error("Failed to execute earthengine CLI", extra={"error": str(exc)})
            raise AdapterError(f"Failed to execute '{self.executable}': {exc}") from exc

        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "Unknown error."
            self.logger.warning(
                "earthengine CLI returned non-zero exit code",
                extra={"exit_code": completed.returncode, "message": message},
            )
            return VerificationResult(
                success=False,
                message=f"{self.executable} returned non-zero exit code: {message}",
            )

        self.logger.debug("earthengine CLI verification succeeded")
        return VerificationResult(
            success=True,
            message="earthengine CLI is available. Run `earthengine authenticate` if API access is required.",
        )
