# TianGong Automation Playbook

AI operators must follow this document when working on the TianGong AI for Sustainability repository.

## Mission Brief

- Deliver a spec-driven sustainability research CLI according to the architecture blueprint documented below.
- Keep behaviour aligned with the human-facing README while prioritising deterministic, reproducible workflows.
- Treat the Architecture Blueprint section in this document and `tasks/blueprint.yaml` as authoritative references for scope, module boundaries, and implementation order.

## Required References

| Artifact | Path | Purpose |
|----------|------|---------|
| Architecture Blueprint | `AGENTS.md` (this document) | Ontology, data-source priorities, CLI roadmap, execution strategy. |
| Task Graph | `tasks/blueprint.yaml` | Dependency ordering for major features. |
| Backlog Register | `tasks/backlog.yaml` | Research-gap follow-ups mapped to deterministic adapters and prompt packs. |
| Human Handbook | `README.md` | Public-facing usage instructions; mirror but do not override. |
| System Setup Guide | `SETUP_GUIDE.md` / `SETUP_GUIDE_CN.md` | Platform-specific installation (macOS/Ubuntu), prerequisites, troubleshooting. |
| Visualization Server | `https://github.com/antvis/mcp-server-chart` | Reference for the AntV MCP chart server integration. |
| Prompt Template (AI) | `specs/prompts/default.md` | English-only prompt delivered to Codex via CLI aliases. |
| Prompt Template (CN, human) | `specs/prompts/default_CN.md` | Chinese translation for operators; do not send to Codex. |
| Workflow scripts | `tiangong_ai_for_sustainability/workflows/` | Python workflows (e.g., `run_simple_workflow`) that automate multi-source studies. |
| Study Workspace Guide | `WORKSPACES.md` | Procedures for managing `.cache/tiangong/<STUDY_ID>/` during research workflows. |

Always consult these sources before planning or executing changes.

### Document Roles

- **AGENTS.md** – repository-level architecture, module boundaries, development workflow.
- **WORKSPACES.md** – execution rules for study workspaces under `.cache/tiangong/<STUDY_ID>/`.
- **specs/prompts/default.md** – operational briefing template sent to Codex; references the runbook and workspace artefacts.

## Operating Principles

1. **Spec-First Execution** — verify that requested work aligns with the Architecture Blueprint below. Escalate conflicts instead of improvising.
2. **Deterministic Pipelines** — prefer rule-based adapters for data acquisition and reserve LLM prompting for synthesis as described in the spec.
3. **CLI-First Commands** — invoke `uv run tiangong-research …` subcommands before reading or writing Python modules. Document any fallbacks when the CLI surface is incomplete and create backlog items to expose missing features.
4. **Reversibility** — avoid destructive commands (`git reset --hard`, force pushes, etc.) unless explicitly authorised.
5. **Bilingual Docs** — whenever `README*.md`, `AGENTS*.md`, `WORKSPACES*.md`, or `SETUP_GUIDE*.md` (including the Architecture Blueprint) are modified, update both English and Chinese versions under the same change set.
6. **Tooling Dependencies** — chart-related tasks require Node.js and the AntV MCP chart server. Check for `node`/`npx` availability and surface installation guidance if missing.
7. **Prompt Templates** — LLM-enabled workflows (Deep Research, future `research synthesize`) must load `specs/prompts/default.md` via the registered aliases (`default`, `default-en`, etc.). Keep AI-facing prompts in English only; `specs/prompts/default_CN.md` is for human use. Placeholders use `{{variable}}` syntax populated via CLI flags (`--prompt-template`, `--prompt-language`, `--prompt-variable`).
8. **Study Workspaces** — when executing research workflows inside `.cache/tiangong/<STUDY_ID>/`, follow the operating rules in `WORKSPACES.md`. Keep topic-specific scripts in the workspace, not the repository.

## Architecture Blueprint

### Alignment Principles

- **R-Flex (Flexible Data Orchestration)** — every data source is pluggable. Registries declare priority, authentication, and capabilities so new sources can be added or deprecated without code churn.
- **R-Auto (Agent Autonomy)** — expose structured execution contexts, task graphs, and reusable services so Codex-style agents can plan and execute work without ad hoc prompting.
- **R-Robust (Deterministic Foundations)** — deterministic adapters fetch and parse data; LLM-driven reasoning is reserved for synthesis or ambiguity resolution.

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `core.config`, `core.context`, `core.registry` | Secrets loading, execution context, and declarative data-source catalogues. |
| `adapters.api`, `adapters.environment`, `adapters.storage` | Deterministic access to APIs, CLIs, and storage. Each adapter returns structured results and verification metadata. |
| `services.research` | Composes adapters with execution context logic (caching, token lookups, dry-run handling). |
| `cli` | Typer application providing human- and agent-facing commands that mirror the spec roadmap. |
| `domain.*` (future) | Ontology models for GRI/SDG/GHG/LCA once ingestion tasks are complete. |

> **Guidance** — add new features by extending the registry and adapters first, then expose services and CLI commands. This keeps automation predictable.

### Data-Source Strategy

#### Priority Matrix

| Priority | Examples | Status | Notes |
|----------|----------|--------|-------|
| **P0** | `tiangong_ai_remote` MCP knowledge base | Implemented | Primary corpus for sustainability research; use as first-line retrieval with comprehensive query payloads. |
| **P1** | UN SDG API, Semantic Scholar, Crossref, GitHub Topics, Wikidata, grid-intensity CLI, `tiangong_lca_remote` MCP | Implemented | Provide core ontology, general retrieval, and micro-level LCA data when needed. |
| **P1 (bulk)** | arXiv / Kaggle dumps | Partial | arxiv.py client now handles API search; bulk download and vector indexing remain planned. |
| **P2** | Scopus, Web of Science, WattTime (via grid-intensity), AntV MCP chart server, Tavily Web MCP, OpenAI Deep Research | Conditional | Enable only when credentials, runtime dependencies (Node.js), or API quotas are available. |
| **P3** | GRI taxonomy XLSX/XBRL, GHG protocol workbooks, Open Sustainable Tech CSV, life cycle assessment inventories (e.g., openLCA datasets) | Rolling | Parse via shared file ingestion layer. |
| **P4** | Google Scholar, ACM Digital Library | Blocked | Enforce alternatives (Semantic Scholar, Crossref). |

#### Adapter Rules

1. All sources register metadata in `resources/datasources/*.yaml`.
2. HTTP adapters use `httpx` with Tenacity-backed retry logic; they must emit `AdapterError` on failures.
3. CLI and MCP adapters should provide actionable install or access guidance when missing (e.g., `grid-intensity`, `mcp-server-chart --transport streamable`, MCP endpoints/API keys).
4. Caching is deferred to services (e.g., storing SDG goals in DuckDB/Parquet) to keep adapters stateless.

> **MCP Usage Notes** — The `tiangong_ai_remote` MCP delivers the most authoritative sustainability literature coverage (≈70M chunks, 70B tokens). Always formulate queries with complete context so the hybrid retriever can yield high-quality passages. The `Search_*` tools (including `Search_Sci_Tool`) return a JSON string—decode it with `json.loads` before accessing fields and keep `topK` ≤ 50 to avoid oversized responses. Rate-limit follow-up enrichment calls (e.g., Semantic Scholar) or switch to `OpenAlex` when 429 throttling occurs. The `tiangong_lca_remote` MCP focuses on life-cycle assessment datasets; reserve it for micro-level LCA case studies or detailed footprint comparisons, and skip it for macro literature scans where `tiangong_ai_remote` and other P1 sources suffice. Use `tavily_web_mcp` when you need general web or news coverage that is outside the curated TianGong corpus, remembering that the Tavily server expects `Authorization: Bearer <API_KEY>`. When invoking TianGong search tools, set `extK` to control how many neighbouring chunks are returned (default `extK=2`, increase only when additional local context is required). Treat `openai_deep_research` as an analysis source triggered after deterministic evidence collection; ensure the OpenAI API key and the deep research model are configured before enabling it in workflows.

### Ontology & Data Models

Target entities (to be represented via Pydantic or SQLAlchemy models once parsers exist):

- **GRI** — `GRIStandard`, `GRIDisclosure`, `GRIIndicator`.
- **SDG** — `SDGGoal`, `SDGTarget`, `SDGIndicator`.
- **GHG Protocol** — `GHGScope`, `EmissionFactor`, `CalculationLogic`.
- **Life Cycle Assessment (LCA)** — `LCAScenario`, `LCAImpactCategory`.
- **Top-level categories** — `SoftwareSustainability_Longevity`, `SoftwareSustainability_Environmental`.

Services should normalise these entities into graph-friendly structures (NetworkX, RDF) for future synthesis.

### CLI Roadmap

| Command | Phase | Description & Current Status |
|---------|-------|------------------------------|
| `research map-sdg` | Phase 1 | Calls OSDG API and reconciles results with local SDG ontology. **Implemented** (requires JSON-capable OSDG endpoint/token). |
| `research find-code` | Phase 1 | Combines seed lists and GitHub Topics to discover repositories. **Implemented** (seed list ingestion pending). |
| `research get-carbon-intensity` | Phase 1 | Invokes `grid-intensity` CLI and reformats output. **Implemented** (depends on CLI installation). |
| `research query-kg` | Phase 1 | Planned wrapper around `wdq`/`wikidata-dl` for SPARQL queries. |
| `research find-papers` | Phase 1 | Aggregates Semantic Scholar (default) with optional OpenAlex enrichment and citation graph export. |
| `research map-gri` | Phase 2 | Parse reports with PDF extractors, align against GRI ontology, optionally delegate to LLM scoring. |
| `research synthesize` | Phase 3 | LLM controller orchestrating other commands according to user prompts. **Implemented** (template-aware). |
| `research visuals verify` | Phase 2 | Confirms AntV MCP chart server availability prior to visualization workflows. **Implemented**. |
| `research workflow simple` | Phase 2 | Automates a compact multi-source study (SDG matches, repos, papers, carbon snapshot, AntV chart). **Implemented**. |
| `research workflow citation-scan --profile <slug>` | Phase 2 | Deterministic citation workflow templated by profile metadata (default `lca`). **Implemented**. |
| `research workflow deep-report --profile <slug>` | Phase 3 | Extends the citation template with Deep Research synthesis; LCA profile ships first, additional profiles plug into the same scaffold. **Implemented**. |

Phase progression must honour dependencies encoded in `tasks/blueprint.yaml`.

### Automation Guidance

1. **Execution Context** — use `ExecutionContext.build_default()` to obtain cache paths, enabled sources, and secrets. Respect `dry_run` and `background_tasks`.
2. **Task Graph** — before implementing a feature, consult `tasks/blueprint.yaml` to ensure prerequisites are met (e.g., ontology ingestion before map-gri).
3. **Dry-Run Support** — services and CLI commands should surface dry-run plans rather than performing side effects when `context.options.dry_run` is true.
4. **Missing Dependencies** — if a command depends on external binaries or credentials (e.g., OSDG token, `grid-intensity` CLI, Node.js for the chart server), surface clear instructions rather than failing silently.
5. **Prompt Templates** — default to `specs/prompts/default.md` when no explicit instructions are provided. The loader resolves aliases through `ResearchServices.load_prompt_template`, supports `{{placeholder}}` substitution from `ExecutionOptions.prompt_variables`, and is configured via CLI flags (`--prompt-template`, `--prompt-language`, `--prompt-variable`). The Chinese file `specs/prompts/default_CN.md` is for humans only and must not be routed to Codex.
6. **Workflow Profiles** — reusable templates power both citation scans and deep-report orchestration. Add new domains by registering a `CitationProfile`/`DeepResearchProfile` (see `workflows/profiles.py`) and rely on `--profile <slug>` without forking CLI commands.
7. **Study Workspace Discipline** — all study-specific artefacts (helper scripts, notebooks, interim datasets, drafts) must live inside `.cache/tiangong/<STUDY_ID>/` in their respective subdirectories (`acquisition/`, `processed/`, `docs/`, `models/`, `figures/`, `scripts/`, `logs/`). Do not add topic-specific code or data to the repository; promote general-purpose logic into `services`, `workflows`, or CLI modules only when it benefits every study.
8. **Runbook as Source of Truth** — edit `<study>/docs/runbook.md` to queue commands, cache paths, and retry guidance. Codex must follow that queue; impromptu commands are discouraged unless first documented in the runbook.
9. **Pipeline & Traceability** — store pipeline manifests, metric tables, and reference indexes under `<study>/processed/` and reference them from deliverables. Each conclusion must point back to deterministic artefacts within the study cache.
10. **Exception Logging** — record rate limits, credential issues, or fallback usage in `<study>/logs/exceptions.md` (and summarise in `docs/gaps.md`) before rerunning commands. Prefer deterministic retries or alternative data sources instead of bespoke script logic.

### Testing Strategy

- Unit tests should isolate adapters using mocks for network calls.
- Service-level tests must verify caching and dry-run behaviour.
- CLI tests rely on `typer.testing.CliRunner` with patched services to avoid real network calls.
- Maintain high coverage for spec-driven logic; add regression tests for every bug fix.

### Governance & Evolution

- Track lifecycle via `DataSourceStatus` (`active`, `trial`, `deprecated`, `blocked`); blocked entries require a reason.
- Version ontology datasets (GRI taxonomy, SDG lists) when upstream providers release updates.
- Keep README focused on human operators; use this document for automation directives.
- Document any additions to the architecture under the Architecture Blueprint to maintain a single source of truth for AI collaborators.

### Current Progress Snapshot

- Registry, execution context, and verification commands are live.
- Implemented Phase 1 commands: `research map-sdg`, `research find-code`, `research get-carbon-intensity`.
- Phase 1 `research find-papers` now aggregates Semantic Scholar with optional OpenAlex enrichment and citation graph export.
- Test suite (`uv run pytest`) covers core modules and CLI operations.
- Next priorities: ingest SDG/GRI ontologies into structured storage, implement remaining Phase 1 commands, and broaden citation/graph tooling.
- Phase 3 synthesis command now available with prompt template support.

## Environment & System Requirements

Before executing automated tasks, verify the deployment environment meets these criteria:

### Core Requirements (Mandatory)
- **Python 3.12+** — Verify with `python3 --version` (required for all operations)
- **uv package manager** — Verify with `uv --version` (required for dependency management)
- **Git** — Verify with `git --version` (required for repository operations)

### Runtime Dependencies (By Feature)
| Feature | Dependency | Check Command | Impact |
|---------|-----------|---|---------|
| Chart visualization | Node.js 22+ | `node --version` | Required for AntV MCP chart server |
| PDF/DOCX export | Pandoc 3.0+ | `pandoc --version` | Required for report format conversion |
| PDF generation | LaTeX (TeX Live) | `pdflatex --version` | Required when PDF output is desired |
| Carbon metrics | `grid-intensity` CLI | `grid-intensity --help` | Required for carbon intensity queries |

### Environment Setup for Agents

1. **Activate Project Environment**: Always run commands via `uv run` to ensure managed environment:
   ```bash
   uv run <command>
   ```

2. **Verify Data Sources**: Before executing workflows, check data source availability:
   ```bash
   uv run tiangong-research sources list
   uv run tiangong-research sources verify <source_id>
   uv run tiangong-research sources audit [--json] [--show-blocked] [--no-fail-on-error]
   ```
   - `--json` emits the aggregated report as JSON (useful for CI pipelines).
   - `--show-blocked` includes sources marked as `blocked` in the registry so operators can review their reasons.
   - `--no-fail-on-error` keeps the CLI exit code at zero even when failures occur (handy for exploratory audits).

3. **Check Optional Features**: Detect installed optional dependencies:
   ```bash
   # Charts support
   npx -y @antv/mcp-server-chart --transport streamable --version

   # PDF support
   pandoc --version && pdflatex --version

   # Carbon metrics
   grid-intensity --help
   ```

4. **Configuration Files**: Respect these configuration sources (in order of precedence):
   - Environment variables (e.g., `TIANGONG_CHART_MCP_ENDPOINT`, API keys)
   - `.secrets/secrets.toml` — secrets bundle (API keys, auth tokens)
   - `.env` — local environment overrides
   - `config.py` — default application settings

5. **Automated Setup**: Use provided installation scripts for consistent environment provisioning:
   - **macOS**: `bash install_macos.sh --full` (installs all optional components)
   - **Ubuntu**: `bash install_ubuntu.sh --full` (installs all optional components)

### Execution Context

All operations must respect the `ExecutionContext` settings:
- **enabled_sources**: Set of data sources available for use
- **dry_run**: Planning mode (no side effects, e.g., no external API calls)
- **background_tasks**: Support for async/deferred operations
- **cache_dir**: Local cache for results

### Observability & Logging

- Obtain loggers via `tiangong_ai_for_sustainability.core.logging.get_logger` or `ExecutionContext.get_logger` so output shares the standard format and observability tags.
- Pass structured context through the `extra` argument instead of interpolating JSON into message strings; this keeps downstream log parsing deterministic.
- Control verbosity with `TIANGONG_LOG_LEVEL` (defaults to `INFO`); raise to `DEBUG` for troubleshooting and reduce to `WARNING` for low-noise batch runs.
- Populate `ExecutionOptions.observability_tags` when spawning work so log streams can be correlated with automation plans.

### Graceful Degradation

When optional dependencies are unavailable:
- **Charts**: If AntV server unavailable, workflows should complete with text-only output
- **PDF export**: If Pandoc/LaTeX missing, fall back to Markdown or JSON output
- **Carbon metrics**: If `grid-intensity` unavailable, workflows should skip carbon calculations
- **Rate-limited APIs**: Implement exponential backoff and checkpoint mechanisms

## Development Workflow

1. Synchronise dependencies with `uv sync` when the lock file changes.
2. Write or update tests alongside code modifications.
3. Keep modules within their designated domains (`core`, `adapters`, `services`, `cli`, etc.).
4. Surface configuration requirements (API keys, CLI dependencies, MCP endpoints) via the registry and execution context; do not embed secrets.
5. When visualization features are required, ensure the AntV MCP chart server is running (`npx -y @antv/mcp-server-chart --transport streamable`) and record the endpoint in `.secrets` or `TIANGONG_CHART_MCP_ENDPOINT`.
6. When extending workflows, reuse helpers from `workflows/simple.py` or add new modules under `workflows/`, keeping corresponding tests up to date.
7. Instrument new services and workflows with the centralized logging helper and add regression tests when behaviour depends on specific log outputs.
8. Shared helper scripts live under `scripts/ops/`, `scripts/integrations/`, `scripts/tooling/`, and `scripts/examples/`; keep study-specific scripts inside `.cache/tiangong/<STUDY_ID>/scripts/` as outlined in `WORKSPACES.md`.

## Verification Checklist

Run the following after every code change:

```bash
uv run black .
uv run ruff check
uv run pytest
```

If Python modules were added or modified, also ensure they compile cleanly:

```bash
uv run python -m compileall src scripts
```

## Communication Rules

- Summarise changes with file references and line numbers where possible.
- Highlight residual risks (e.g., external APIs requiring credentials, sandbox limitations).
- When blocking on missing tools (e.g., `grid-intensity` CLI or OSDG API token), document the exact prerequisite so humans can resolve it quickly.
