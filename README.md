# TianGong AI for Sustainability CLI

English | [中文](https://github.com/linancn/TianGong-AI-for-Sustainability/blob/main/README_CN.md)

This README is the quick start for everyone. Run the setup script, follow the prompts, and you will be ready to use the TianGong research CLI in a few minutes.

## Quick Install (Recommended)

1. Open a terminal and clone the repository:
   ```bash
   git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
   ```
2. Change into the project directory:
   ```bash
   cd TianGong-AI-for-Sustainability
   ```
3. Launch the installer for your operating system:

   **macOS**
   ```bash
   bash install_macos.sh
   ```

   **Ubuntu / Debian**
   ```bash
   bash install_ubuntu.sh
   ```

   **Windows (PowerShell, run as Administrator)**
   ```powershell
   PowerShell -ExecutionPolicy Bypass -File .\install_windows.ps1
   ```

The script checks Python 3.12+, uv, Git, and project dependencies. It also offers optional extras—charts (Node.js 22+), PDF export (Pandoc + LaTeX), and carbon metrics (`uk-grid-intensity`). Accept the defaults or answer **yes** when the script asks which features you want.

> **Update or change features later?** Rerun the same script. You can add `--full`, `--minimal`, or any `--with-*` flag to skip the interactive questions.

## After the Script Finishes

Use `uv run` for every CLI command so you stay inside the managed environment:

```bash
uv run tiangong-research --help
uv run tiangong-research sources list
uv run tiangong-research sources verify un_sdg_api
uv run tiangong-research research workflow simple --topic "life cycle assessment"
```

If you enabled charts, start the AntV MCP chart server before running workflows with `--chart-output`.

### Optional Feature Checks

- Charts: `node --version` and `npx -y @antv/mcp-server-chart --transport streamable --version`
- PDF export: `pandoc --version` and `pdflatex --version`
- Carbon metrics: `uv run --group 3rd uk-grid-intensity --help`

Missing a feature? Just re-run your installer (`install_macos.sh`, `install_ubuntu.sh`, or `install_windows.ps1`) with the matching `--with-*` flag.

## Most-Used CLI Commands

- `uv run tiangong-research sources list` — browse the registered data sources.
- `uv run tiangong-research sources verify <id>` — confirm credentials/connectivity.
- `uv run tiangong-research research find-code "<topic>" --limit 5 --json` — discover sustainability repositories.
- `uv run tiangong-research research map-sdg <file>` — align a document with SDG goals (requires OSDG access).
- `uv run --group 3rd tiangong-research research get-carbon-intensity <location>` — fetch grid intensity metrics (set the `GRID_INTENSITY_CLI` env var if you use a non-default executable).
- `uv run tiangong-research research visuals verify` — make sure the AntV MCP chart server is reachable.

## Need Advanced Control?

Power users who prefer to manage Python environments manually or run the CLI on atypical platforms should read:

- `SETUP_GUIDE.md` (English)
- `SETUP_GUIDE_CN.md` (中文)

Everyone else can simply rely on the platform installers—`install_macos.sh`, `install_ubuntu.sh`, or `install_windows.ps1`—for installation, updates, and optional feature management.

## More References

- Architecture overview — `specs/architecture.md`
- Automation agent handbook — `AGENTS.md`
- Prompt templates — `specs/prompts/`

Optional components degrade gracefully (for example, workflows fall back to text when charts are unavailable). Keep any required API keys in environment variables or `.secrets/secrets.toml` so the CLI can access protected sources.
