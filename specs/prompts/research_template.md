# TianGong Research Prompt Template (English)

Use this template when instructing an automation agent to run a compact, end-to-end sustainability study that touches multiple data sources and concludes with an AntV visualization.

## 0. Preconditions

- Dependencies: `uv sync`, Node.js 22+, `npx -y @antv/mcp-server-chart --transport streamable` running locally.
- Secrets: populate `.secrets/secrets.toml` with required API tokens (Semantic Scholar optional, osdg optional).
- CLI: `tiangong-research` available via `uv run`.

## 1. Environment Checks

1. `uv run tiangong-research sources list`
2. `uv run tiangong-research sources verify un_sdg_api`
3. `uv run tiangong-research sources verify semantic_scholar`
4. `uv run tiangong-research sources verify github_topics`
5. `uv run tiangong-research research visuals verify`

If any step fails, capture the error, provide remediation, and pause the workflow.

## 2. Data Collection

1. **SDG Ontology Snapshot**
   ```bash
   uv run tiangong-research research map-sdg path/to/input.txt --json
   ```
   - Use short text (>=50 words) describing the research topic.
   - If OSDG API is unavailable, note the limitation and continue with other sources.

2. **Code Discovery**
   ```bash
   uv run tiangong-research research find-code sustainability --limit 5 --json
   ```
   - Filter repositories relevant to the topic; highlight stars and descriptions.

3. **Literature Query**
   ```bash
   uv run tiangong-research research find-papers "<keywords>" --json
   ```
   - Optional flags: `--openalex/--no-openalex`, `--arxiv/--no-arxiv`, `--scopus/--no-scopus`, `--citation-graph`, `--limit`.
   - Results default to Semantic Scholar; when OpenAlex is enabled, the CLI enriches with cited-by counts and limited references.
   - Local arXiv and Scopus exports are read from `TIANGONG_ARXIV_INDEX` / `TIANGONG_SCOPUS_INDEX` (or `.cache/tiangong/<source>/index.jsonl`).
   - When using `tiangong_ai_remote` directly, remember each `Search_*` tool returns a JSON string. Decode it first:
     ```python
     payload, _ = client.invoke_tool("tiangong_ai_remote", "Search_Sci_Tool", {...})
     records = json.loads(payload)
     ```
   - Prefer `httpx` (already in the project dependencies) for any follow-up API calls and respect 429 throttling with exponential backoff or by falling back to `OpenAlex`.
   - Reserve `tiangong_lca_remote` for micro-level LCA case studies or detailed footprint comparisons; macro literature sweeps should stay with `tiangong_ai_remote` and the other P1 sources to keep the workflow deterministic.
   - When invoking TianGong MCP search tools, explicitly set `extK` to control how many neighbouring chunks are returned (default `extK=2`); raise it only when additional local context is truly required.
   - Reach for `tavily_web_mcp` when you need broad web/news coverage beyond the TianGong corpus—remember to supply `Authorization: Bearer <API_KEY>` in the secrets bundle.

4. **Carbon Intensity Context**
   ```bash
   uv run tiangong-research research get-carbon-intensity CAISO_NORTH --json
   ```
   - Replace `CAISO_NORTH` with a grid location relevant to the study.

## 3. Analysis Summary

Synthesize the findings in a structured note:

- Topic definition and SDG alignment (from map-sdg).
- Key codebases and their roles.
- Notable papers and cited frameworks.
- Carbon intensity snapshot and implications.
- Missing data or blockers.

## 4. Visualization with AntV MCP

1. Prepare a chart spec summarizing one quantitative aspect (e.g., repository stars or citation counts). Example payload:
   ```json
   {
     "chartType": "bar",
     "data": [
       {"name": "Project A", "value": 1400},
       {"name": "Project B", "value": 860},
       {"name": "Project C", "value": 720}
     ],
     "encoding": {
       "x": "name",
       "y": "value",
       "color": "name"
     },
     "title": "Top Sustainability Repositories by GitHub Stars"
   }
   ```
2. Invoke the MCP chart server tool (pseudo-code; adjust to your MCP client):
   ```json
   {
     "type": "mcp-call",
     "server": "chart_mcp_server",
     "tool": "generate_bar_chart",
     "arguments": {
       "spec": { ...chart payload... },
       "format": "png",
       "background": "#ffffff"
     }
   }
   ```
3. Save the generated image under `.cache/tiangong/visuals/<descriptive-name>.png`.
4. Include the image path and a short caption in the final report.

## 5. Deliverables

- JSON outputs from each CLI command (or clear error notes).
- Human-readable synthesis (Markdown or structured text).
- Generated chart file path and description.
- Follow-up recommendations or next steps.

### CLI Shortcut

When automation should handle the entire flow end-to-end, run:

```bash
uv run tiangong-research research workflow simple --topic "<query>" --report-output reports/snapshot.md --chart-output visuals/snapshot.png
```
