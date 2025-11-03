# TianGong 默认调研提示（中文，仅供人工参考）

此文档提供与 `specs/prompts/default.md` 对应的中文说明，方便人工理解与编辑。请勿将本文件直接发送给 Codex，所有交付给 AI 的提示应使用英文版本 `default.md`。

## 使用说明
- 复制下方 Markdown 骨架，发送前将占位符（`<…>`）替换为实际内容。
- 先确认环境和凭据（数据源访问、AntV 图表服务、`grid-intensity`、缓存路径）已就绪。
- 按执行顺序列出 CLI 命令。除非明确授权回退，否则 Codex 必须通过 `uv run tiangong-research …` 完成操作。
- 原始输出建议保存到 `.cache/tiangong/<STUDY_ID>/` 或声明的路径，便于复现。

## 提示骨架
```markdown
# 天工调研计划 — 默认模板

## 1. 环境与准备
- [ ] 运行 `uv run tiangong-research sources list` 确认数据源。
- [ ] 使用 `uv run tiangong-research sources verify <id>` 验证关键数据源（`<SOURCE_IDS>`）。
- [ ] 若需要图表，执行 `uv run tiangong-research research visuals verify`。
- [ ] 缺失的工具或凭据：<MISSING_ITEMS_AND_REMEDIATION>

## 2. 研究背景
- 主要目标：<PRIMARY_OBJECTIVE>
- 研究范围 / 子主题：<SUBTOPICS>
- 地理或行业聚焦：<GEOGRAPHY>
- 约束或政策要求：<CONSTRAINTS>
- 期望交付物：<DATASETS_REPORTS_VISUALS>

## 3. 分阶段计划（CLI 优先）
### 阶段 0 —— 规范对齐
- 目的：确保与 `AGENTS.md`、`tasks/blueprint.yaml` 一致。
- CLI 命令：`uv run tiangong-research sources list`、`uv run tiangong-research sources verify <id>`
- 输出：就绪情况、受阻数据源、升级事项。

### 阶段 1 —— 确定性采集
- 目的：获取 SDG 映射、代码仓库、文献、碳强度或知识图谱数据。
- CLI 命令（按需选择）：
  - `uv run tiangong-research research map-sdg <PATH_OR_TEXT>`
  - `uv run tiangong-research research find-code "<KEYWORDS>"`
  - `uv run tiangong-research research find-papers "<QUERY>"`
  - `uv run --group 3rd tiangong-research research get-carbon-intensity <GRID_ID>`
  - `uv run tiangong-research research query-kg --query <PATH_OR_QUERY>`（功能上线后使用）
- 输出：将 JSON/Markdown 存于 `.cache/tiangong/<STUDY_ID>/acquisition`。

### 阶段 2 —— 证据整合
- 目的：规范化、去重并计算核心指标。
- 工具：复用缓存输出；若使用脚本需注明。
- 输出：汇总表、合并数据集、缓存路径。

### 阶段 3 —— 综合与可视化
- 目的：基于确定性证据生成洞见或图表。
- CLI 命令：
  - `uv run tiangong-research research synthesize "<QUESTION>" --prompt-template default --prompt-language en -P 键=值`
  - `uv run tiangong-research research visuals verify`
  - `npx -y @antv/mcp-server-chart --transport streamable --spec <SPEC_PATH>`（按需生成图表）
- 输出：综合报告路径、图表文件、追溯说明。

### 阶段 4 —— 收尾
- 目的：整理结果、阻碍与后续动作。
- 操作：归档输出、如有新增事项更新 `tasks/backlog.yaml`。
- 输出：总结、待办条目、环境问题。

## 4. 确定性命令序列
1. `<CLI_COMMAND>` —— 目的、关键参数、输出路径。
2. `<CLI_COMMAND>` —— 目的、关键参数、输出路径。
3. （按需扩展，保持顺序确定。）

## 5. 报告与可观测性
- 输出格式：<MARKDOWN_JSON_PDF>
- 观测标签：<TAG_LIST>
- Dry run 模式：<true|false>
- 缓存目录（可选）：<CACHE_PATH>
- 追溯要求：说明每条结论对应的 CLI 输出 `<OUTPUT_PATH>`。

## 6. 可选扩展
- 深度调研触发条件：仅在确定性步骤完成且凭据齐备时启用，注明范围与上限（<ITERATION_LIMIT>/<BUDGET>）。
- AntV 图表规格：<CHART_DESCRIPTION_AND_DESTINATION>
- 自定义提示或变量：<TEMPLATE_PATHS_AND_VALUES>

## 7. 回退与阻塞
- 缺少 CLI 能力 → 指定确定性的 Python 备用方案（`tiangong_ai_for_sustainability.<MODULE>.<FUNCTION>`），并记录待办扩展 CLI。
- 外部阻塞（限频、凭据缺失）→ <REMEDIATION_PLAN>。
- 升级联系人 / 后续行动：<STAKEHOLDER_ACTIONS>。

## 8. 交付清单
- [ ] 总结目标、方法、结果与后续建议。
- [ ] 将 CLI 原始输出（JSON/Markdown）存放在 `<CACHE_PATH>`。
- [ ] 在报告中引用图表或可视化资源。
- [ ] 针对发现的缺口更新 backlog 或 TODO。
- [ ] 记录速率限制、缺失数据或依赖失败情况。
```

## 对齐检查
- 确认任务在架构蓝图范围内，并遵循依赖顺序。
- 若使用尚未开放的功能，请在执行前标注并寻求确认。
- 记录涉及的本体或注册表，保证自动化可复现。

## 证据与追溯
- 要求将确定性输出（JSON/Markdown）存放于指定路径。
- 在报告中注明每条洞见对应的 CLI 输出或 MCP 调用。
- 记录缺失数据或重试信息，方便后续参考。

## 可选扩展与降级策略
- `--deep-research` 仅在确定性步骤完成后启用，并明确预算与限制。
- 如缺少可选工具（AntV 图表、`grid-intensity`、PDF 工具链），需给出安装指引或说明降级行为。

## CLI 快速参考
| 命令 | 用途 | 常用参数 / 说明 |
|------|------|----------------|
| `uv run tiangong-research research map-sdg <PATH_OR_TEXT>` | 将文本映射至 SDG。 | `--json`、可选 `--prompt-language en`、`--prompt-variable 键=值` |
| `uv run tiangong-research research find-code "<KEYWORDS>"` | 搜索代码实现案例。 | `--limit <N>`、`--json`、`--topics-cache <PATH>` |
| `uv run tiangong-research research find-papers "<QUERY>"` | 聚合学术文献。 | `--limit <N>`、`--openalex/--no-openalex`、`--citation-graph`、`--arxiv` |
| `uv run --group 3rd tiangong-research research get-carbon-intensity <GRID_ID>` | 获取碳强度信息。 | `--json`、`--as-of <TIMESTAMP>`、`--timezone <TZ>` |
| `uv run tiangong-research research query-kg --query <PATH_OR_QUERY>` | 规划中的 SPARQL/MCP 查询。 | `--json`，功能开放后可补充 Header。 |
| `uv run tiangong-research research synthesize "<QUESTION>"` | 综合确定性证据。 | `--prompt-template default`、可选 `--prompt-language en`、可重复 `-P 键=值`、可选 `--deep-research`。 |
| `uv run tiangong-research research visuals verify` | 检查 AntV 图表服务。 | 可配合 `npx -y @antv/mcp-server-chart --transport streamable --version` 排查。 |
| `uv run tiangong-research research workflow simple --topic "<TOPIC>"` | 运行阶段二组合流程。 | `--report-output <PATH>`、`--chart-output <PATH>`、可选 `--prompt-language en`。 |
| `uv run tiangong-research research workflow lca-deep-report --prompt-template default` | 执行 LCA + 深度调研工作流。 | 可重复 `-P 键=值`、可选 `--prompt-language en`，记录综合报告路径。 |

---

保持本文件与 `default.md` 内容一致，仅用于人工查阅与维护，勿直接发送给 AI。
