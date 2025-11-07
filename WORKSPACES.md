---
title: Study Workspace Guide
---

# Study Workspace Guide

This document explains how to run TianGong research workflows inside the study cache (`.cache/tiangong/<STUDY_ID>/`). It complements `AGENTS.md`, which covers repository-level development practices, and the Codex briefing template in `specs/prompts/default.md`.

## 1. Workspace Bootstrapping

1. Initialise the workspace:
   ```bash
   uv run python scripts/ops/init_study_workspace.py --study-id <STUDY_ID>
   ```
   This creates the canonical directory layout:
   ```
   .cache/tiangong/<STUDY_ID>/
   ├── acquisition/   # Raw CLI outputs (JSON/CSV)
   ├── processed/     # Normalised datasets & pipeline manifests
   ├── docs/          # Runbook, blueprint, study notes
   ├── models/        # Model inputs/outputs
   ├── figures/       # Charts and visual artefacts
   ├── logs/          # Run history, exceptions, readiness notes
   └── scripts/       # Study-specific helper scripts/notebooks
   ```
2. Populate `docs/runbook.md` with the deterministic command queue (in execution order). Codex and human operators must follow this plan.
3. Record high-level goals and constraints in `docs/study_brief.md`.

## 2. Source of Truth Files

- `config.yaml` – auto-generated; includes `study_id` and `auto_execute`. Update via `init_study_workspace.py --force` if needed.
- `docs/runbook.md` – command queue, cache paths, next actions. Keep it current before executing steps.
- `docs/study_brief.md` – stage goals, prompts, deliverables.
- `logs/run_history.md` – append every executed command with timestamp and output path.
- `logs/exceptions.md` – log rate limits, missing credentials, and retry plans before re-running.
- `docs/gaps.md` – summarise outstanding data gaps or follow-ups.
- `processed/README.md` – maintain a table linking processed artefacts to source scripts/commands.

## 3. Command Execution Rules

1. Stay on the CLI surface:
   ```bash
   uv run tiangong-research <command> [...]
   ```
   Only use study-specific Python scripts when a capability is missing from the CLI; document the fallback in the runbook and add a backlog item to expose it via CLI.
2. Store raw outputs (JSON/Markdown, charts, models) under the relevant subdirectory inside `.cache/tiangong/<STUDY_ID>/`.
3. Never check study-specific scripts or outputs into the repository; keep them under `scripts/` within the workspace.
4. When using LLM synthesis:
   - Default to `specs/prompts/default.md` (alias `default`).
   - Pass prompt variables via CLI flags (`--prompt-template`, `--prompt-language`, `--prompt-variable key=value`).
   - Capture responses (JSON/Markdown) under `docs/` or `processed/` with traceability back to deterministic inputs.

## 4. Dry Run & Observability

- Set `--dry-run` (or `ExecutionOptions.dry_run`) when drafting plans; store the resulting plan in `logs/run_history.md`.
- Use `logs/exceptions.md` to record API rate limits, missing credentials, or degraded behaviour. Include retry/backoff notes.
- Populate `ExecutionOptions.observability_tags` when kicking off complex workflows to align with automation plans.

## 5. Closing a Study

1. Ensure all reports, charts, and datasets referenced in deliverables live under the study workspace.
2. Update `docs/gaps.md` and `tasks/backlog.yaml` (via repository PR) for outstanding work.
3. Promote validated outputs (reports, data) to long-term storage or documentation only after verification.
4. Keep the workspace intact for reproducibility; do not delete intermediate files unless retention policies require it.

## 6. Quick Reference

| Task | Command |
|------|---------|
| Initialise workspace | `uv run python scripts/ops/init_study_workspace.py --study-id <STUDY_ID>` |
| List sources | `uv run tiangong-research sources list` |
| Verify key sources | `uv run tiangong-research sources verify <id>` |
| Run workflow | `uv run tiangong-research research workflow <...>` |
| Compose research prompt | `uv run python scripts/tooling/compose_inline_prompt.py [--emit-inline]` |

For repository-level development guidelines, refer to `AGENTS.md`. This guide focuses exclusively on study workspace operations.
