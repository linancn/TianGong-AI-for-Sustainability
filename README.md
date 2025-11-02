# TianGong AI for Sustainability CLI

Welcome to the TianGong sustainability research CLI. This README is a single place for anyone—especially first‑time users—to install the tool, verify the environment, and run the first workflow.

## Start in One Command

1. Open a terminal and change to the project directory:
   ```bash
   cd /path/to/TianGong-AI-for-Sustainability
   ```
2. Run the installer that matches your operating system.

### macOS

```bash
bash install_macos.sh
```

### Ubuntu / Debian

```bash
bash install_ubuntu.sh
```

During the interactive run you can accept the defaults or opt into extras (charts, PDF export, carbon metrics). To skip the prompts:

- Full feature set: `bash install_<os>.sh --full`
- Core only: `bash install_<os>.sh --minimal`
- Pick features: `bash install_<os>.sh --with-charts --with-pdf --with-carbon`

## What the Installer Checks

- Python 3.12+ and the [uv](https://docs.astral.sh/uv/) package manager
- Git and project dependencies (`uv sync`)
- Optional tooling when requested:
  - Node.js 22+ for AntV chart workflows (the script now verifies existing installations and offers to install or upgrade)
  - Pandoc 3+ and LaTeX for PDF/DOCX export
  - `grid-intensity` CLI for carbon metrics

At the end you will see a summary of what succeeded and anything that still needs attention.

## After Installation

Run everything inside the managed environment with `uv run`.

```bash
uv run tiangong-research --help
uv run tiangong-research sources list
uv run tiangong-research sources verify un_sdg_api
uv run tiangong-research research workflow simple --topic "life cycle assessment"
```

Need charts? Start the AntV MCP chart server first, then rerun the workflow with `--chart-output visuals/snapshot.png`.

### Verify Optional Features

- Charts: `node --version` and `npx -y @antv/mcp-server-chart --transport streamable --version`
- PDF export: `pandoc --version` and `pdflatex --version`
- Carbon metrics: `grid-intensity --help`

If any command is missing, rerun the installer with the matching `--with-*` flag or follow the guidance printed by the script.

## Manual Setup (Optional)

If you prefer to configure everything yourself:

1. Install Python 3.12+, Git, and uv.
2. (Recommended) Create a virtual environment with Python 3.12.
3. From the project root, install dependencies:
   ```bash
   uv sync
   ```
4. Run the CLI with `uv run tiangong-research …`.

Detailed troubleshooting for macOS and Ubuntu is documented in `SETUP_GUIDE.md` (English) and `SETUP_GUIDE_CN.md` (中文).

## Common Commands

- `uv run tiangong-research sources list` — inspect the data-source registry.
- `uv run tiangong-research sources verify <id>` — confirm connectivity/config for a specific source.
- `uv run tiangong-research research find-code "<topic>" --limit 5 --json` — discover sustainability repositories.
- `uv run tiangong-research research map-sdg <file>` — map a document to SDG goals (requires OSDG access).
- `uv run tiangong-research research get-carbon-intensity <location>` — fetch grid-intensity metrics (requires `grid-intensity` CLI).
- `uv run tiangong-research research visuals verify` — confirm the AntV MCP chart server is reachable.

## Need Help?

- **Setup guides**: `SETUP_GUIDE.md`, `SETUP_GUIDE_CN.md`
- **Architecture**: `specs/architecture.md`
- **Agent ops**: `AGENTS.md`
- **Prompt templates**: `specs/prompts/`

When optional dependencies are unavailable, the CLI falls back gracefully (e.g., text-only output when charts are disabled). Remember to keep environment variables or `.secrets/secrets.toml` up to date with any API tokens you need.
