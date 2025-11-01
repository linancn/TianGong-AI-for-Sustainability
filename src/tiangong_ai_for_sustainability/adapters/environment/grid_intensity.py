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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..base import AdapterError, DataSourceAdapter, VerificationResult


@dataclass(slots=True)
class GridIntensityCLIAdapter(DataSourceAdapter):
    """Minimal subprocess wrapper for ``grid-intensity``."""

    source_id: str = "grid_intensity_cli"
    executable: str = "grid-intensity"

    def verify(self) -> VerificationResult:
        """Check whether the CLI is available on ``PATH``."""

        if shutil.which(self.executable) is None:
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
            raise AdapterError(f"Failed to execute '{self.executable}': {exc}") from exc

        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "Unknown error."
            return VerificationResult(success=False, message=f"{self.executable} returned non-zero exit code: {message}")

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
            raise AdapterError(
                "grid-intensity CLI is required but not installed. "
                "Install it via 'pip install grid-intensity-cli' or follow the upstream documentation."
            )

        command = [self.executable, "--provider", provider, "--location", location, "--json"]
        if extra_args:
            command.extend(extra_args)

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
            raise AdapterError(f"Failed to execute '{self.executable}': {exc}") from exc

        if completed.returncode != 0:
            raise AdapterError(
                f"{self.executable} exited with status {completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}"
            )

        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"Failed to parse grid-intensity output as JSON: {exc}") from exc
