# TianGong Automation Playbook

AI operators must follow this document when working on the TianGong AI for Sustainability repository.

## Mission Brief

- Deliver a spec-driven sustainability research CLI according to the architecture captured in `specs/`.
- Keep behaviour aligned with the human-facing README while prioritising deterministic, reproducible workflows.
- Treat `specs/architecture.md` and `tasks/blueprint.yaml` as authoritative references for scope, module boundaries, and implementation order.

## Required References

| Artifact | Path | Purpose |
|----------|------|---------|
| Architecture Spec | `specs/architecture.md` | Ontology, data-source priorities, CLI roadmap, execution strategy. |
| Task Graph | `tasks/blueprint.yaml` | Dependency ordering for major features. |
| Human Handbook | `README.md` | Public-facing usage instructions; mirror but do not override. |
| Visualization Server | `https://github.com/antvis/mcp-server-chart` | Reference for the AntV MCP chart server integration. |
| Prompt Templates | `specs/prompts/` | Reusable research prompts (maintain English/Chinese pairs). |
| Workflow scripts | `tiangong_ai_for_sustainability/workflows/` | Python workflows (e.g., `run_simple_workflow`) that automate multi-source studies. |

Always consult these sources before planning or executing changes.

## Operating Principles

1. **Spec-First Execution** — verify that requested work aligns with `specs/architecture.md`. Escalate conflicts instead of improvising.
2. **Deterministic Pipelines** — prefer rule-based adapters for data acquisition and reserve LLM prompting for synthesis as described in the spec.
3. **Reversibility** — avoid destructive commands (`git reset --hard`, force pushes, etc.) unless explicitly authorised.
4. **Bilingual Docs** — whenever `README*.md`, `AGENTS*.md`, or `specs/architecture*.md` are modified, update both English and Chinese versions in the same change set.
5. **Tooling Dependencies** — chart-related tasks require Node.js and the AntV MCP chart server. Check for `node`/`npx` availability and surface installation guidance if missing.

## Development Workflow

1. Synchronise dependencies with `uv sync` when the lock file changes.
2. Write or update tests alongside code modifications.
3. Keep modules within their designated domains (`core`, `adapters`, `services`, `cli`, etc.).
4. Surface configuration requirements (API keys, CLI dependencies, MCP endpoints) via the registry and execution context; do not embed secrets.
5. When visualization features are required, ensure the AntV MCP chart server is running (`npx -y @antv/mcp-server-chart --transport streamable`) and record the endpoint in `.secrets` or `TIANGONG_CHART_MCP_ENDPOINT`.
6. When extending workflows, reuse helpers from `workflows/simple.py` or add new modules under `workflows/`, keeping corresponding tests up to date.

## Verification Checklist

Run the following before handing work back to a human or chaining additional agents:

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
