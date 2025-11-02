# TianGong 调研提示模板（中文）

当需要指挥自动化代理完成一个涵盖多数据源并最终使用 AntV MCP 图表服务器的端到端研究流程时，请参考此模板。

## 0. 前提条件

- 依赖：已执行 `uv sync`，安装 Node.js 22+，并启动 `npx -y @antv/mcp-server-chart --transport streamable`。
- 凭据：在 `.secrets/secrets.toml` 中配置必要的 API Token（如 Semantic Scholar、OSDG 可选）。
- CLI：确认可以通过 `uv run tiangong-research` 调用命令行工具。

## 1. 环境检查

1. `uv run tiangong-research sources list`
2. `uv run tiangong-research sources verify un_sdg_api`
3. `uv run tiangong-research sources verify semantic_scholar`
4. `uv run tiangong-research sources verify github_topics`
5. `uv run tiangong-research research visuals verify`

若任一步骤失败，需记录错误、给出解决方案并暂停流程。

## 2. 数据采集

1. **SDG 本体映射**
   ```bash
   uv run tiangong-research research map-sdg path/to/input.txt --json
   ```
   - 输入文本需≥50词，描述目标研究主题。
   - 若 OSDG API 不可用，应记录限制并继续后续步骤。

2. **代码资源发现**
   ```bash
   uv run tiangong-research research find-code sustainability --limit 5 --json
   ```
   - 关注与主题紧密相关的仓库，记录 star 数及简介。

3. **文献查询**（目前处于路线图规划阶段，执行前需确认命令已上线）
   ```bash
   uv run tiangong-research research find-papers "<关键词>" --json
   ```
   - 执行前先确认 `tiangong-research research find-papers --help` 可用（该命令仍在规划中）。
   - 若命令尚未上线，请记录该限制，并在本地 arXiv 索引缺失时改用 Semantic Scholar API 结果。
   - 如具备 Scopus 凭据，可追加 `--link-sdg`。

4. **碳强度背景**
   ```bash
   uv run tiangong-research research get-carbon-intensity CAISO_NORTH --json
   ```
   - 根据研究区域替换 `CAISO_NORTH`。

## 3. 分析摘要

整理以下要点形成结构化说明：

- 主题定义与 SDG 对应关系（组合 map-sdg 结果）。
- 关键代码项目及其作用。
- 代表性论文及引用框架。
- 当前碳强度数据及其启示。
- 数据缺口或潜在风险。

## 4. 使用 AntV MCP 生成图表

1. 准备一个量化数据的图表配置示例：
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
     "title": "可持续项目 GitHub Star 数对比"
   }
   ```
2. 通过 MCP 客户端调用（示例 JSON，需根据实际客户端调整）：
   ```json
   {
     "type": "mcp-call",
     "server": "chart_mcp_server",
     "tool": "generate_bar_chart",
     "arguments": {
       "spec": { ...图表配置... },
       "format": "png",
       "background": "#ffffff"
     }
   }
   ```
3. 将返回的图像保存至 `.cache/tiangong/visuals/<描述性文件名>.png`。
4. 在最终报告中引用图像路径并附简要说明。

## 5. 交付内容

- 每个 CLI 命令的 JSON 结果（或清晰的错误记录）。
- 面向人类的总结（Markdown 或结构化文本）。
- 生成的图表文件路径与说明。
- 后续建议或待办事项。

### CLI 快捷方式

若需一次性触发完整流程，可执行：

```bash
uv run tiangong-research research workflow simple --topic "<主题>" --report-output reports/snapshot.md --chart-output visuals/snapshot.png
```
