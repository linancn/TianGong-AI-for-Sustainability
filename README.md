# TianGong AI for Sustainability

Human-readable handbook for the TianGong sustainability research CLI.

## Project Overview

The repository delivers a spec-driven command line interface that investigates sustainability literature, standards, code artefacts, and carbon data. Core capabilities include:

- Maintaining a declarative registry of data sources (UN SDG API, Semantic Scholar, GitHub Topics, OSDG, grid-intensity CLI, etc.).
- Providing Typer-based commands to list/verify sources, search sustainability codebases, map documents to SDG goals, and query carbon intensity.
- Exposing adapters and services that separate deterministic API access from LLM-assisted reasoning so automation agents can orchestrate reliable research workflows.

## 🚀 Quick Navigation

| Want to... | Read... |
|-----------|---------|
| **Get started immediately** | [QUICKSTART.md](./QUICKSTART.md) — 5 min setup |
| **Understand the project** | [README.md](./README.md) — This page |
| **Detailed installation** | [SETUP_GUIDE.md](./SETUP_GUIDE.md) — Platform-specific guide |
| **Technical architecture** | [specs/architecture.md](./specs/architecture.md) — For developers |
| **中文用户请看** | [QUICKSTART_CN.md](./QUICKSTART_CN.md) — 快速入门 |

## Getting Started

### ⚡ Quick Start (One-Click Setup)

**For macOS:**
```bash
bash install_macos.sh
```

**For Ubuntu/Debian:**
```bash
bash install_ubuntu.sh
```

These scripts will guide you through interactive setup with options for optional components.

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) for environment and packaging management
- Node.js 22+ (only required when using the AntV MCP chart server for visualization)
- Optional (for exporting reports as PDF/DOCX via workflows):
  - [Pandoc](https://pandoc.org/) 3.0+
  - A LaTeX engine such as TeX Live when PDF output is desired

**For detailed platform-specific setup instructions, see:**
- **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** — macOS and Ubuntu complete installation guides
- **[SETUP_GUIDE_CN.md](./SETUP_GUIDE_CN.md)** — 中文版本（macOS 和 Ubuntu 完整安装指南）

### Manual Installation

If you prefer manual setup, run:

```bash
uv sync
```

### CLI Usage

The CLI is installed as `tiangong-research`. Run any command through `uv run` to stay inside the managed environment:

```bash
uv run tiangong-research --help
```

Helpful entry points:

- `uv run tiangong-research sources list` — inspect the data source catalogue.
- `uv run tiangong-research sources verify <id>` — check connectivity or configuration for a specific source.
- `uv run tiangong-research research find-code life-cycle-assessment --limit 5 --json` — discover GitHub repositories tagged with life cycle assessment topics.
- `uv run tiangong-research research map-sdg <file>` — classify a text or PDF via the OSDG API (requires a working JSON endpoint or token).
- `uv run tiangong-research research get-carbon-intensity <location>` — fetch grid intensity metrics through the upstream CLI (ensure `grid-intensity` is installed on `PATH`).
- `uv run tiangong-research research visuals verify` — confirm the AntV MCP chart server is reachable (requires Node.js and `npx -y @antv/mcp-server-chart --transport streamable`).
- `uv run tiangong-research research workflow simple --topic "<query>" --report-output reports/snapshot.md --chart-output visuals/snapshot.png` — run the end-to-end workflow that gathers data, writes a Markdown report, and renders an AntV chart.

Refer to the AI-oriented specifications in `specs/` for deeper architectural detail.

### Chart Visualization Support

To render charts via [AntV's MCP chart server](https://github.com/antvis/mcp-server-chart):

1. Install Node.js and the server package (either globally or via `npx`).
2. Launch the server locally, for example `npx -y @antv/mcp-server-chart --transport streamable` (default endpoint `http://127.0.0.1:1122/mcp`).
3. Optionally set `TIANGONG_CHART_MCP_ENDPOINT` or `.secrets` → `[chart_mcp] endpoint` if you use a custom host/port.
4. Use `uv run tiangong-research research visuals verify` to ensure the CLI can reach the server before triggering visualization workflows.

## Repository Layout

- `src/tiangong_ai_for_sustainability/` — application code (core registry/context modules, API adapters, services, CLI).
- `specs/` — specification documents supporting AI-driven development.
- `tests/` — pytest suite covering context, registry, services, and CLI behaviour.
- `tasks/blueprint.yaml` — declarative dependency graph for automation agents.

## Development Workflow

1. Install dependencies with `uv sync`.
2. Make changes inside `src/` and add or update tests in `tests/`.
3. Run the test suite (see below) and address any formatting or lint issues before submitting work.

## Testing

Run the full test suite locally with:

```bash
uv run pytest
```

Optional linting/formatting helpers:

```bash
uv run ruff check
uv run black .
```
