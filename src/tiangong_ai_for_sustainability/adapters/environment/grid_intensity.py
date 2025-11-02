"""
Adapter for the grid-intensity CLI wrapper.

The tool proxies providers such as WattTime and Electricity Maps. We interact
with it via subprocess calls to avoid re-implementing API auth flows. The
adapter focuses on basic presence checks and invoking the CLI with JSON output
enabled.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from logging import LoggerAdapter
from typing import Any, Dict, List, Optional

from ..base import AdapterError, DataSourceAdapter, VerificationResult
from ...core.logging import get_logger


@dataclass(slots=True)
class GridIntensityCLIAdapter(DataSourceAdapter):
    """Minimal subprocess wrapper for ``grid-intensity``."""

    source_id: str = "grid_intensity_cli"
    executable: str = "grid-intensity"
    logger: LoggerAdapter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    def verify(self) -> VerificationResult:
        """Check whether the CLI is available on ``PATH``."""

        if shutil.which(self.executable) is None:
            self.logger.warning("grid-intensity CLI missing from PATH")
            return VerificationResult(
                success=False,
                message=(
                    "grid-intensity CLI is not installed or not discoverable on PATH. "
                    "Install it from https://github.com/thegreenwebfoundation/grid-intensity-CLI "
                    "or via pip install grid-intensity-cli."
                ),
            )

        try:
            completed = subprocess.run(
                [self.executable, "--help"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
        except OSError as exc:  # pragma: no cover - depends on environment
            self.logger.error("Failed to execute grid-intensity during verification", extra={"error": str(exc)})
            raise AdapterError(f"Failed to execute '{self.executable}': {exc}") from exc

        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "Unknown error."
            self.logger.warning(
                "grid-intensity verification returned non-zero exit code",
                extra={"exit_code": completed.returncode, "message": message},
            )
            return VerificationResult(success=False, message=f"{self.executable} returned non-zero exit code: {message}")

        self.logger.debug("grid-intensity CLI verification succeeded")
        return VerificationResult(success=True, message="grid-intensity CLI is available.")

    def query(self, location: str, provider: str = "WattTime", extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute the CLI and parse JSON output.

        Parameters
        ----------
        location:
            Provider specific location identifier, e.g. ``CAISO_NORTH``.
        provider:
            CLI provider argument, defaults to ``WattTime`` as suggested by the
            specification.
        extra_args:
            Optional additional command line arguments.
        """

        if shutil.which(self.executable) is None:
            self.logger.error("grid-intensity CLI required but not installed", extra={"location": location, "provider": provider})
            raise AdapterError("grid-intensity CLI is required but not installed. " "Install it via 'pip install grid-intensity-cli' or follow the upstream documentation.")

        command = [self.executable, "--provider", provider, "--location", location, "--json"]
        if extra_args:
            command.extend(extra_args)

        self.logger.info(
            "Running grid-intensity CLI",
            extra={"command": command},
        )
        try:
            completed = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
        except OSError as exc:  # pragma: no cover - system specific
            self.logger.error("Failed to execute grid-intensity CLI", extra={"error": str(exc)})
            raise AdapterError(f"Failed to execute '{self.executable}': {exc}") from exc

        if completed.returncode != 0:
            self.logger.error(
                "grid-intensity CLI returned non-zero exit code",
                extra={"exit_code": completed.returncode, "stderr": completed.stderr.strip()},
            )
            raise AdapterError(f"{self.executable} exited with status {completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}")

        try:
            data = json.loads(completed.stdout)
            self.logger.debug("grid-intensity CLI response parsed", extra={"keys": list(data.keys())})
            return data
        except json.JSONDecodeError as exc:
            self.logger.error("Failed to parse grid-intensity CLI output", extra={"error": str(exc)})
            raise AdapterError(f"Failed to parse grid-intensity output as JSON: {exc}") from exc
