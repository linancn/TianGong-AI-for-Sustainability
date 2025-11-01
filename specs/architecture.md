# TianGong Sustainability Research CLI — Architecture Blueprint

Authoritative specification for automation agents working on this repository. It distils the multi-part sustainability requirements into implementable guidance while preserving adaptability, autonomy, and robustness.

## 1. Alignment Principles

- **R-Flex (Flexible Data Orchestration)** — every data source is pluggable. Registries declare priority, authentication, and capabilities so new sources can be added or deprecated without code churn.
- **R-Auto (Agent Autonomy)** — expose structured execution contexts, task graphs, and reusable services so Codex-style agents can plan and execute work without ad hoc prompting.
- **R-Robust (Deterministic Foundations)** — deterministic adapters fetch and parse data; LLM-driven reasoning is reserved for synthesis or ambiguity resolution.

## 2. Module Responsibilities

| Module | Purpose |
|--------|---------|
| `core.config`, `core.context`, `core.registry` | Secrets loading, execution context, and declarative data-source catalogues. |
| `adapters.api`, `adapters.environment`, `adapters.storage` | Deterministic access to APIs, CLIs, and storage. Each adapter returns structured results and verification metadata. |
| `services.research` | Composes adapters with execution context logic (caching, token lookups, dry-run handling). |
| `cli` | Typer application providing human- and agent-facing commands that mirror the spec roadmap. |
| `domain.*` (future) | Ontology models for GRI/SDG/GHG/SCI once ingestion tasks are complete. |

> **Guidance** — add new features by extending the registry and adapters first, then expose services and CLI commands. This keeps automation predictable.

## 3. Data-Source Strategy

### 3.1 Priority Matrix

| Priority | Examples | Status | Notes |
|----------|----------|--------|-------|
| **P1** | UN SDG API, Semantic Scholar, GitHub Topics, Wikidata, grid-intensity CLI | Implemented | Provide core ontology and retrieval. |
| **P1 (bulk)** | arXiv S3 / Kaggle dumps | Planned | Download + vector indexing once storage constraints are resolved. |
| **P2** | Scopus, Web of Science, WattTime (via grid-intensity), AntV MCP chart server | Conditional | Enable only when credentials or runtime dependencies (Node.js) are available. |
| **P3** | GRI taxonomy XLSX/XBRL, GHG protocol workbooks, Open Sustainable Tech CSV, Awesome Green Software list | Rolling | Parse via shared file ingestion layer. |
| **P4** | Google Scholar, ACM Digital Library | Blocked | Enforce alternatives (Semantic Scholar, Crossref). |

### 3.2 Adapter Rules

1. All sources register metadata in `resources/datasources/*.yaml`.
2. HTTP adapters use `httpx` with Tenacity-backed retry logic; they must emit `AdapterError` on failures.
3. CLI adapters shell out via subprocess and should provide actionable install guidance when missing (e.g., `grid-intensity`, `mcp-server-chart --transport streamable`).
4. Caching is deferred to services (e.g., storing SDG goals in DuckDB/Parquet) to keep adapters stateless.

## 4. Ontology & Data Models

Target entities (to be represented via Pydantic or SQLAlchemy models once parsers exist):

- **GRI** — `GRIStandard`, `GRIDisclosure`, `GRIIndicator`.
- **SDG** — `SDGGoal`, `SDGTarget`, `SDGIndicator`.
- **GHG Protocol** — `GHGScope`, `EmissionFactor`, `CalculationLogic`.
- **Green Software (SCI)** — `SCIMetric`, `SCIParameter`.
- **Top-level categories** — `SoftwareSustainability_Longevity`, `SoftwareSustainability_Environmental`.

Services should normalise these entities into graph-friendly structures (NetworkX, RDF) for future synthesis.

## 5. CLI Roadmap

| Command | Phase | Description & Current Status |
|---------|-------|------------------------------|
| `research map-sdg` | Phase 1 | Calls OSDG API and reconciles results with local SDG ontology. **Implemented** (requires JSON-capable OSDG endpoint/token). |
| `research find-code` | Phase 1 | Combines seed lists and GitHub Topics to discover repositories. **Implemented** (seed list ingestion pending). |
| `research get-carbon-intensity` | Phase 1 | Invokes `grid-intensity` CLI and reformats output. **Implemented** (depends on CLI installation). |
| `research query-kg` | Phase 1 | Planned wrapper around `wdq`/`wikidata-dl` for SPARQL queries. |
| `research find-papers` | Phase 1 | Planned aggregator across Semantic Scholar, arXiv index (when available), Scopus fallback. |
| `research map-gri` | Phase 2 | Parse reports with PDF extractors, align against GRI ontology, optionally delegate to LLM scoring. |
| `research synthesize` | Phase 3 | LLM controller orchestrating other commands according to user prompts. |
| `research visuals verify` | Phase 2 | Confirms AntV MCP chart server availability prior to visualization workflows. **Implemented**. |

Phase progression must honour dependencies encoded in `tasks/blueprint.yaml`.

## 6. Automation Guidance

1. **Execution Context** — use `ExecutionContext.build_default()` to obtain cache paths, enabled sources, and secrets. Respect `dry_run` and `background_tasks`.
2. **Task Graph** — before implementing a feature, consult `tasks/blueprint.yaml` to ensure prerequisites are met (e.g., ontology ingestion before map-gri).
3. **Dry-Run Support** — services and CLI commands should surface dry-run plans rather than performing side effects when `context.options.dry_run` is true.
4. **Missing Dependencies** — if a command depends on external binaries or credentials (e.g., OSDG token, `grid-intensity` CLI, Node.js for the chart server), surface clear instructions rather than failing silently.

## 7. Testing Strategy

- Unit tests should isolate adapters using mocks for network calls.
- Service-level tests must verify caching and dry-run behaviour.
- CLI tests rely on `typer.testing.CliRunner` with patched services to avoid real network calls.
- Maintain high coverage for spec-driven logic; add regression tests for every bug fix.

## 8. Governance & Evolution

- Track lifecycle via `DataSourceStatus` (`active`, `trial`, `deprecated`, `blocked`); blocked entries require a reason.
- Version ontology datasets (GRI taxonomy, SDG lists) when upstream providers release updates.
- Keep README focused on human operators; use `AGENTS.md` and this specification for automation directives.
- Document any additions to the spec under `specs/` to maintain a single source of truth for AI collaborators.

## 9. Current Progress Snapshot

- Registry, execution context, and verification commands are live.
- Implemented Phase 1 commands: `research map-sdg`, `research find-code`, `research get-carbon-intensity`.
- Test suite (`uv run pytest`) covers core modules and CLI operations.
- Next priorities: ingest SDG/GRI ontologies into structured storage, implement remaining Phase 1 commands, and broaden citation/graph tooling.
