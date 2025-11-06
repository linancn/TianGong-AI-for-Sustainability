"""
Initialise a study workspace under .cache/tiangong/<study_id>/.

The workspace hosts deterministic artefacts (acquisition outputs, processed
datasets, drafts). Generic runbook and study brief files are generated so each
study can refine them without relying on topic-specific templates.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent
from typing import Iterable

DEFAULT_STUDY_ID = "study"
DEFAULT_CACHE_ROOT = Path(".cache/tiangong")
DIRECTORIES: tuple[str, ...] = (
    "acquisition",
    "processed",
    "docs",
    "models",
    "figures",
    "logs",
    "scripts",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a study workspace with generic planning artefacts."
    )
    parser.add_argument(
        "--study-id",
        default=DEFAULT_STUDY_ID,
        help="Study identifier. Workspace will be created under .cache/tiangong/<study-id>/",
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=DEFAULT_CACHE_ROOT,
        help="Root directory for cached studies (default: .cache/tiangong).",
    )
    parser.add_argument(
        "--auto-execute",
        action="store_true",
        help="Mark the workspace config with auto_execute: true so Codex continues after blueprint confirmation.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing generated files if they already exist.",
    )
    return parser.parse_args()


def create_directories(base: Path, subdirs: Iterable[str]) -> None:
    for name in subdirs:
        (base / name).mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.write_text(content)


def build_config_content(study_id: str, auto_execute: bool) -> str:
    return dedent(
        f"""\
        study_id: {study_id}
        auto_execute: {'true' if auto_execute else 'false'}
        """
    )


def build_runbook_content(study_id: str) -> str:
    return dedent(
        f"""\
        # Study Runbook – {study_id}

        ## Workspace Layout
        ```
        .cache/tiangong/{study_id}/
        ├── acquisition/   # Raw CLI outputs (JSON/CSV)
        ├── processed/     # Normalised datasets
        ├── docs/          # Blueprint, drafts, evidence tables
        ├── models/        # Model inputs/outputs
        ├── figures/       # Charts and visual artefacts
        ├── logs/          # Readiness notes, execution logs
        └── scripts/       # Study-specific helper scripts (optional)
        ```

        ## Execution Flags
        - Auto execute after blueprint confirmation: {{auto_execute}}
        - Blueprint confirmation log: `.cache/tiangong/{study_id}/logs/readiness.md`

        ## Deterministic Command Queue
        1. `uv run tiangong-research sources list`
        2. `uv run tiangong-research sources verify <source_id>`
        3. Populate acquisition commands (e.g., `tiangong-research research find-papers ... --json > acquisition/<slug>.json`)
        4. Transformation scripts (`uv run python scripts/<script>.py --study-id {study_id}`)
        5. Modelling / visualisation steps
        6. Synthesis (`tiangong-research research synthesize ...`) *(optional)*
        7. Wrap-up and backlog updates

        ## Traceability Notes
        - Record every command invocation and output path in `logs/run_history.md`.
        - Reference cache artefacts when drafting documents inside `docs/`.
        - Promote final deliverables to a versioned `reports/<slug>/` directory only after validation.

        ## TODO Log
        - [ ] Pending data sources
        - [ ] Missing credentials / tooling
        - [ ] Candidate backlog entries
        """
    )


def build_study_brief_content(study_id: str) -> str:
    return dedent(
        f"""\
        # Study Blueprint – {study_id}

        ## Stage 0 — Environment & Alignment
        - Verify sources: `uv run tiangong-research sources list`
        - Validate critical sources: `uv run tiangong-research sources verify <id>`
        - Missing tooling / credentials: <document remediation>

        ## Stage 1 — Deterministic Acquisition
        - Command list and expected cache outputs under `.cache/tiangong/{study_id}/acquisition/`
        - Capture rate limits or gaps in `docs/gaps.md`

        ## Stage 2 — Evidence Consolidation
        - Normalisation scripts / notebooks
        - Output targets in `.cache/tiangong/{study_id}/processed/`

        ## Stage 3 — Analysis & Modelling
        - Key metrics / models to compute
        - Store inputs/outputs under `.cache/tiangong/{study_id}/models/`

        ## Stage 4 — Visualisation & Synthesis
        - Charts / tables planned (store under `figures/` or `docs/`)
        - Synthesis command and prompt variables

        ## Stage 5 — Wrap-up
        - Deliverables to promote outside cache
        - Follow-up actions / backlog candidates

        Fill each section as the study progresses. Reference `.cache/tiangong/{study_id}/config.yaml`
        for the auto-execution flag when preparing prompts from `specs/prompts/default.md`.
        """
    )


def main() -> None:
    args = parse_args()
    cache_root: Path = args.cache_root
    study_id: str = args.study_id

    workspace = cache_root / study_id
    workspace.mkdir(parents=True, exist_ok=True)

    create_directories(workspace, DIRECTORIES)

    config_path = workspace / "config.yaml"
    write_file(config_path, build_config_content(study_id, args.auto_execute), args.force)

    docs_dir = workspace / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    auto_flag = "true" if args.auto_execute else "false"
    runbook = build_runbook_content(study_id).replace("{auto_execute}", auto_flag)
    study_brief = build_study_brief_content(study_id)

    write_file(docs_dir / "runbook.md", runbook, args.force)
    write_file(docs_dir / "study_brief.md", study_brief, args.force)


if __name__ == "__main__":
    main()
