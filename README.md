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
uv run tiangong-research sources audit
uv run tiangong-research sources verify un_sdg_api
uv run tiangong-research research workflow simple --topic "life cycle assessment"
```

If you enabled charts, start the AntV MCP chart server before running workflows with `--chart-output`.

### Optional Feature Checks

- Charts: `node --version` and `npx -y @antv/mcp-server-chart --transport streamable --version`
- PDF export: `pandoc --version` and `pdflatex --version`
- Carbon metrics: `uv run --group 3rd uk-grid-intensity --help`

Missing a feature? Just re-run your installer (`install_macos.sh`, `install_ubuntu.sh`, or `install_windows.ps1`) with the matching `--with-*` flag.

## Codex Docker Workflow

- Build the container with Codex enabled: `docker build -t tiangong-ai-codex .` (toggle extras with `--build-arg INSTALL_CODEX=false`, `INSTALL_NODE=false`, etc. if you need leaner images).
- Mount the repository when running so Codex can see your files: `docker run --rm -v "$(pwd):/workspace" tiangong-ai-codex codex`.
- Use `codex exec --json "<prompt>"` for unattended tasks; watch for `turn.completed` in the stream to detect success or `turn.failed`/`error` when human intervention is required. Pair with `--ask-for-approval never` to avoid interactive pauses.
- Keep CLI access available by overriding the entrypoint when necessary: `docker run --rm --entrypoint uv tiangong-ai-codex run tiangong-research --help`.
- Persist Codex state across runs by mounting a volume to `/workspace/.codex` (for example `-v codex_state:/workspace/.codex`).

## Most-Used CLI Commands

- `uv run tiangong-research sources list` — browse the registered data sources.
- `uv run tiangong-research sources verify <id>` — confirm credentials/connectivity.
- `uv run tiangong-research research find-code "<topic>" --limit 5 --json` — discover sustainability repositories.
- `uv run tiangong-research research map-sdg <file>` — align a document with SDG goals (requires OSDG access).
- `uv run tiangong-research research find-papers "<keywords>" --openalex --arxiv --scopus --citation-graph --limit 10 --json` — aggregate Semantic Scholar plus optional OpenAlex/arXiv/Scopus enrichment.
- `uv run --group 3rd tiangong-research research get-carbon-intensity <location>` — fetch grid intensity metrics (set the `GRID_INTENSITY_CLI` env var if you use a non-default executable).
- `uv run tiangong-research research synthesize "<question>" --output reports/synthesis.md` — orchestrate SDG, code, literature, carbon checks, then compile an LLM-guided summary.
- `uv run tiangong-research research visuals verify` — make sure the AntV MCP chart server is reachable.

## Prompt Templates & Deep Research

- Global flags `--prompt-template`, `--prompt-language` (use `en`), and `--prompt-variable key=value` control which Markdown template feeds LLM synthesis steps (Deep Research workflows and `research synthesize`).
- Built-in aliases: `default`, `default-en`, and `en` (all point to the same English template). When no `--prompt-template` is provided, the CLI falls back to `default`. You can also pass an absolute or project-relative path to a custom template.
- Copy the default prompt scaffold at `specs/prompts/default.md` (AI-facing, English) and customise it before briefing Codex; use `specs/prompts/default_CN.md` only as a human-readable translation.
- Follow the CLI-first rule: run `uv run tiangong-research …` subcommands before reading or writing Python. Escalate only when a capability lacks a CLI wrapper.
- Templates accept simple placeholders such as `{{topic}}`; combine multiple `--prompt-variable` arguments to substitute values.
- Example:
  ```bash
  uv run tiangong-research --prompt-template default --prompt-variable topic="urban climate resilience" research workflow deep-report --profile lca --years 3
  ```
- `--deep-prompt` and `--deep-instructions` remain available for one-off overrides; templates apply only when instructions are omitted.

## Inline Prompt Composer

- Generate the Markdown research brief that references the staged workflow instructions: `uv run python scripts/tooling/compose_inline_prompt.py`
- Pass `--emit-inline` to also save the single-line prompt (defaults to Markdown output only).
- Override inputs when necessary:
  - `--user-prompt path/to/file.md` selects an alternate study brief.
  - `--spec path/to/workflow.md` (alias `--template`) points at a different staged workflow spec.
  - `--markdown-output path/to/prompt.md` rewrites the Markdown destination; pair with `--inline-output` when emitting the inline string.
- Without flags the script writes the Markdown prompt to `user_prompts/_markdown_prompt.md` and prints the same content to stdout. Inline output is created only when requested.
- The Markdown prompt cites the canonical specs instead of inlining them. Fill the “Study-Specific Notes” and “Workspace Notes” blocks before handing the prompt to Codex.

```bash
uv run python scripts/tooling/compose_inline_prompt.py --user-prompt user_prompts/example.md
``` 

## Need Advanced Control?

Power users who prefer to manage Python environments manually or run the CLI on atypical platforms should read:

- `SETUP_GUIDE.md` (English)
- `SETUP_GUIDE_CN.md` (中文)

Everyone else can simply rely on the platform installers—`install_macos.sh`, `install_ubuntu.sh`, or `install_windows.ps1`—for installation, updates, and optional feature management.

## More References

- Architecture overview — `AGENTS.md` (Architecture Blueprint)
- Automation agent handbook — `AGENTS.md`
- Prompt template — `specs/prompts/default.md` (AI) / `specs/prompts/default_CN.md` (human reference)

Optional components degrade gracefully (for example, workflows fall back to text when charts are unavailable). Keep any required API keys in environment variables or `.secrets/secrets.toml` so the CLI can access protected sources.

## Codex
```bash
# Dangerous: bypass approvals and sandboxing for quick tests
codex exec --dangerously-bypass-approvals-and-sandbox "$(cat user_prompts/_inline_prompt.txt)"
```
