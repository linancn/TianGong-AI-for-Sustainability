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
    parser = argparse.ArgumentParser(description="Create a study workspace with generic planning artefacts.")
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
├── processed/     # Normalised datasets & pipeline manifests
├── docs/          # Blueprint, drafts, evidence tables
├── models/        # Model inputs/outputs
├── figures/       # Charts and visual artefacts
├── logs/          # Readiness notes, execution logs
└── scripts/       # Study-specific helpers kept inside the cache
```

## Execution Flags
- Auto execute after blueprint confirmation: {{auto_execute}}
- Blueprint confirmation log: `.cache/tiangong/{study_id}/logs/readiness.md`

## Deterministic Command Queue
1. `uv run tiangong-research sources list`
2. `uv run tiangong-research sources verify <source_id>`
3. Acquisition commands (e.g., `uv run tiangong-research research find-papers ... --json --output .cache/tiangong/{study_id}/acquisition/<slug>.json`)
4. Deterministic transformations executed from the study cache (e.g., `uv run python .cache/tiangong/{study_id}/scripts/<script>.py`)
5. Modelling / visualisation steps with outputs under `.cache/tiangong/{study_id}/models/` or `figures/`
6. Synthesis (`uv run tiangong-research research synthesize ...`) only after deterministic evidence is collected
7. Wrap-up, backlog updates, and promotion of validated artefacts

## Traceability Notes
- Record every command invocation and output path in `logs/run_history.md`.
- Log rate limits or external blockers in `logs/exceptions.md` before retrying.
- Reference cache artefacts when drafting documents inside `docs/`.
- Store pipeline manifests and metric tables in `processed/` for reproducibility.
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
- Capture rate limits or gaps in `logs/exceptions.md` and summarise in `docs/gaps.md`

## Stage 2 — Evidence Consolidation
- Normalisation scripts / notebooks stored under `.cache/tiangong/{study_id}/scripts/`
- Output targets and pipeline manifests in `.cache/tiangong/{study_id}/processed/`

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


def build_run_history_content() -> str:
    return dedent(
        """\
# Command Run History

> Append each executed command with timestamp, operator, and primary output path.
>
> Example:
> - 2024-01-01T10:00Z — `uv run tiangong-research sources list` → logs/sources_list.txt
        """
    )


def build_exceptions_content() -> str:
    return dedent(
        """\
# Exceptions & Rate Limits Log

| Timestamp | Command / Source | Error | Retry Plan | Status |
|-----------|-----------------|-------|------------|--------|
|           |                 |       |            |        |
        """
    )


def build_gaps_content(study_id: str) -> str:
    return dedent(
        f"""\
# Evidence Gaps – {study_id}

- Pending metrics:
- Missing datasets:
- Follow-up actions:
        """
    )


def build_processed_readme_content(study_id: str) -> str:
    return dedent(
        f"""\
# Processed Artefacts Registry – {study_id}

| File | Description | Source Command / Script |
|------|-------------|-------------------------|
|      |             |                         |

Maintain this table to keep deterministic traceability between inputs and
processed outputs stored in this directory.
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

    logs_dir = workspace / "logs"
    write_file(logs_dir / "run_history.md", build_run_history_content(), args.force)
    write_file(logs_dir / "exceptions.md", build_exceptions_content(), args.force)

    write_file(docs_dir / "gaps.md", build_gaps_content(study_id), args.force)

    processed_dir = workspace / "processed"
    write_file(processed_dir / "README.md", build_processed_readme_content(study_id), args.force)


if __name__ == "__main__":
    main()
