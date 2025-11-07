# TianGong Default Research Prompt (English)

This template is the only prompt file that should be delivered to Codex. It provides the full study briefing scaffold, stage plan, and CLI quick reference in English so executions stay deterministic. A Chinese translation for human operators is available at `specs/prompts/default_CN.md`; do **not** feed that file to the AI.

## How to Use
- Initialise (or reuse) a study workspace before drafting the prompt: `uv run python scripts/ops/init_study_workspace.py --study-id <STUDY_ID>`. This provisions `.cache/tiangong/<STUDY_ID>/` along with editable `docs/runbook.md` and `docs/study_brief.md`. For workspace operating rules see `WORKSPACES.md` / `WORKSPACES_CN.md`.
- Update the generated runbook/blueprint files with the study-specific command queue, cache locations, and whether Codex should continue automatically after blueprint confirmation (`auto_execute: true|false`).
- Copy the Markdown skeleton below and replace every placeholder (`<...>`) with concrete details about your study, referencing the prepared runbook where helpful.
- Save customised prompts and intermediate planning artefacts inside the study workspace (for example `.cache/tiangong/<STUDY_ID>/docs/`). Treat `user_prompts/_markdown_prompt.md` and `_inline_prompt.txt` as immutable templates; do **not** overwrite them with study-specific content.
- Check environment readiness (data-source credentials, AntV chart server, `grid-intensity`, cache paths) before sending the prompt.
- List the CLI commands in the order they must run. Codex should remain on the `uv run tiangong-research ...` interface unless you explicitly authorise a deterministic Python fallback.
- Store raw outputs under `.cache/tiangong/<STUDY_ID>/` (or another declared path) for reproducibility.

## Prompt Skeleton (Copy & Edit)
```markdown
# TianGong Research Plan - Default Template

## 0. Workspace Bootstrap (pre-prompt)
- Study ID: `<STUDY_ID>`
- Workspace init command: `uv run python scripts/ops/init_study_workspace.py --study-id <STUDY_ID>` *(skip if already provisioned)*
- Blueprint sources: `.cache/tiangong/<STUDY_ID>/docs/runbook.md`, `.cache/tiangong/<STUDY_ID>/docs/study_brief.md`
- Auto execute after blueprint confirmation: `<true|false>` *(Codex proceeds immediately when true; otherwise pause for human sign-off)*

## 1. Environment & Readiness
- [ ] Run `uv run tiangong-research sources list` and confirm availability.
- [ ] Verify essential sources (`<SOURCE_IDS>`) via `uv run tiangong-research sources verify <id>`.
- [ ] If charts are required, run `uv run tiangong-research research visuals verify`.
- [ ] Missing tooling or credentials: <MISSING_ITEMS_AND_REMEDIATION>

## 2. Study Context
- Primary objective: <PRIMARY_OBJECTIVE>
- Scope / subtopics: <SUBTOPICS>
- Geography or sector focus: <GEOGRAPHY>
- Constraints or policies: <CONSTRAINTS>
- Expected deliverables: <DATASETS_REPORTS_VISUALS>

## 3. Stage Plan (CLI-First)
### Stage 0 - Spec Alignment
- Purpose: confirm alignment with `AGENTS.md` and `tasks/blueprint.yaml`.
- CLI commands: `uv run tiangong-research sources list`, `uv run tiangong-research sources verify <id>`
- Auto-execution guard: confirm `<true|false>` setting from workspace blueprint and state whether Codex should continue without further confirmation.
- Outputs: readiness notes, blocked sources, escalation items.

### Stage 1 - Deterministic Acquisition
- Purpose: gather SDG matches, repositories, literature, carbon metrics, or KG data.
- CLI commands (select as needed):
  - `uv run tiangong-research research map-sdg <PATH_OR_TEXT>`
  - `uv run tiangong-research research find-code "<KEYWORDS>"`
  - `uv run tiangong-research research find-papers "<QUERY>"`
  - `uv run --group 3rd tiangong-research research get-carbon-intensity <GRID_ID>`
  - `uv run tiangong-research research query-kg --query <PATH_OR_QUERY>` *(when available)*
- Outputs: store JSON/Markdown under `.cache/tiangong/<STUDY_ID>/acquisition`.

### Stage 2 - Evidence Consolidation
- Purpose: normalise, deduplicate, and compute key metrics.
- Tooling: reuse cached CLI outputs; document any scripts invoked.
- Outputs: summary tables, merged datasets, cache paths.

### Stage 3 - Synthesis & Visualisation
- Purpose: translate deterministic evidence into insights or charts.
- CLI commands:
  - `uv run tiangong-research research synthesize "<QUESTION>" --prompt-template default --prompt-language en -P key=value`
  - `uv run tiangong-research research visuals verify`
  - `npx -y @antv/mcp-server-chart --transport streamable --spec <SPEC_PATH>` *(optional charts)*
- Outputs: synthesis report path, chart assets, traceability notes.

### Stage 4 - Wrap-up
- Purpose: record outcomes, blockers, follow-ups.
- Actions: archive outputs, update `tasks/backlog.yaml` when new work arises.
- Outputs: final summary, backlog entries, environment issues.

## 4. Deterministic Command Queue
1. `<CLI_COMMAND>` - purpose, key flags, expected output path.
2. `<CLI_COMMAND>` - purpose, key flags, expected output path.
3. *(Extend as required; keep order deterministic.)*

## 5. Reporting & Observability
- Output formats: <MARKDOWN_JSON_PDF>
- Observability tags: <TAG_LIST>
- Dry run mode: <true|false>
- Cache directory override (optional): <CACHE_PATH>
- Traceability: link each conclusion to the corresponding CLI output at `<OUTPUT_PATH>`.

## 6. Optional Extensions
- Deep Research trigger: enable only after deterministic evidence exists; specify scope and limits (<ITERATION_LIMIT>/<BUDGET>).
- AntV chart specification: <CHART_DESCRIPTION_AND_DESTINATION>
- Custom prompt packs or variables: <TEMPLATE_PATHS_AND_VALUES>

## 7. Fallbacks & Blockers
- Missing CLI capability -> deterministic Python fallback (`tiangong_ai_for_sustainability.<MODULE>.<FUNCTION>`) plus TODO to expose via CLI.
- External blockers (rate limits, missing credentials) -> <REMEDIATION_PLAN>.
- Escalation contact / next steps: <STAKEHOLDER_ACTIONS>.

## 8. Deliverable Checklist
- [ ] Structured summary covering objectives, methods, results, next steps.
- [ ] Stored CLI outputs (JSON/Markdown) at `<CACHE_PATH>`.
- [ ] Visualization assets referenced in the report.
- [ ] Backlog or TODO updates for identified gaps.
- [ ] Notes on rate limits, missing data, or dependency failures.
```

## Alignment Checklist
- Confirm the request is within the architecture blueprint and respects dependency ordering.
- Flag features outside current phases before running commands.
- Document which ontology datasets or registries the study touches to keep automation reproducible.

## Evidence & Traceability
- Require deterministic outputs (JSON/Markdown) stored under declared paths.
- Maintain explicit references from each insight back to acquisition outputs or MCP tool invocations.
- Log missing data or retries so future runs understand prior constraints.

## Optional Extensions & Degradation
- Only enable `--deep-research` after deterministic steps succeed and credentials are configured.
- Provide clear installation guidance when optional tooling (AntV chart server, `grid-intensity`, PDF stack) is missing; allow graceful degradation.

## CLI Quick Reference
| Command | Purpose | Common Flags / Notes |
|---------|---------|----------------------|
| `uv run tiangong-research research map-sdg <PATH_OR_TEXT>` | Map narratives to SDG taxonomy. | `--json`, optional `--prompt-language en`, `--prompt-variable key=value` |
| `uv run tiangong-research research find-code "<KEYWORDS>"` | Discover implementation references. | `--limit <N>`, `--json`, `--topics-cache <PATH>` |
| `uv run tiangong-research research find-papers "<QUERY>"` | Aggregate scholarly literature. | `--limit <N>`, `--openalex/--no-openalex`, `--citation-graph`, `--arxiv` |
| `uv run --group 3rd tiangong-research research get-carbon-intensity <GRID_ID>` | Fetch carbon-intensity data. | `--json`, `--as-of <TIMESTAMP>`, `--timezone <TZ>` |
| `uv run tiangong-research research query-kg --query <PATH_OR_QUERY>` | Planned SPARQL/MCP query. | `--json`, custom headers when available. |
| `uv run tiangong-research research synthesize "<QUESTION>"` | Generate evidence-backed synthesis. | `--prompt-template default`, optional `--prompt-language en`, repeatable `-P key=value`, `--deep-research`. |
| `uv run tiangong-research research visuals verify` | Check AntV MCP chart readiness. | Pair with `npx -y @antv/mcp-server-chart --transport streamable --version` for diagnostics. |
| `uv run tiangong-research research workflow simple --topic "<TOPIC>"` | Execute the Phase 2 workflow. | `--report-output <PATH>`, `--chart-output <PATH>`, optional `--prompt-language en`. |
| `uv run tiangong-research research workflow deep-report --profile lca --prompt-template default` | Run the deep research workflow for the LCA profile. | Repeatable `-P key=value`, optional `--prompt-language en`, capture synthesis path. |

---

Maintain this file as the single source of truth for AI-facing prompts. Keep all additions in English and mirror updates to `default_CN.md` for human-friendly guidance.
