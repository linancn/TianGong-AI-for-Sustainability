#!/usr/bin/env python3
"""
Convenience wrapper for ``tiangong-research sources audit``.

This script exists for operators who prefer invoking a Python entry point via
``uv run python scripts/ops/audit_sources.py``. All arguments are forwarded to the
CLI command so flags like ``--json`` or ``--no-fail-on-error`` can be used
verbatim.
"""

from __future__ import annotations

import sys

from typer.main import get_command

from tiangong_ai_for_sustainability.cli.main import app


def main(argv: list[str] | None = None) -> int:
    command = get_command(app)
    args = ["tiangong-research", "sources", "audit", *(argv or sys.argv[1:])]
    try:
        command.main(args=args, standalone_mode=True)
    except SystemExit as exc:  # pragma: no cover - exercised via integration
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
