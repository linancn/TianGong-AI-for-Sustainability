# TianGong 可持续性研究 CLI —— 架构蓝图（中文）

本文件是自动化代理的权威中文规范，与英文版 `specs/architecture.md` 保持一致。

## 1. 对齐原则

- **R-Flex（灵活的数据编排）**：数据源必须可插拔。通过注册表声明优先级、认证方式与功能标签，便于新增或退役数据源而不修改核心代码。
- **R-Auto（代理自治）**：提供结构化的执行上下文、任务图与服务接口，使 Codex 等代理可在无人工干预的情况下规划并执行工作。
- **R-Robust（稳健的确定性基础）**：数据获取和解析依赖确定性适配器；LLM 推理仅在综合或歧义处理阶段使用。

## 2. 模块职责

| 模块 | 作用 |
|------|------|
| `core.config` / `core.context` / `core.registry` | 管理秘密信息、执行上下文与数据源注册表。 |
| `adapters.api` / `adapters.environment` / `adapters.storage` | 提供确定性 API、CLI、存储访问层，返回结构化结果与验证信息。 |
| `services.research` | 在执行上下文内组合适配器（缓存、令牌查找、dry-run 处理）。 |
| `cli` | 基于 Typer 的命令行入口，与规格中的路线图保持一致。 |
| `domain.*`（规划中） | 存放 GRI/SDG/GHG/SCI 等本体模型。 |

> **实施提示**：扩展功能时先更新注册表和适配器，再开放服务与 CLI。这有助于保持自动化流程可预测。

## 3. 数据源策略

### 3.1 优先级矩阵

| 优先级 | 示例 | 状态 | 说明 |
|--------|------|------|------|
| **P1** | UN SDG API、Semantic Scholar、GitHub Topics、Wikidata、grid-intensity CLI | 已实现 | 构成本体与检索基础。 |
| **P1（批量）** | arXiv S3 / Kaggle | 规划中 | 待解决存储成本后引入全文索引。 |
| **P2** | Scopus、Web of Science、WattTime（通过 grid-intensity）、AntV MCP 图表服务器 | 视凭据/环境启用 | 需提供密钥或运行时依赖（Node.js）。 |
| **P3** | GRI taxonomy、GHG 工作簿、Open Sustainable Tech CSV、Awesome Green Software | 持续接入 | 通过统一的文件解析框架处理。 |
| **P4** | Google Scholar、ACM Digital Library | 禁用 | 强制使用替代方案（如 Semantic Scholar、Crossref）。 |

### 3.2 适配器规则

1. 数据源元数据需登记在 `resources/datasources/*.yaml`。
2. HTTP 适配器使用 `httpx` + Tenacity 重试，失败时抛出 `AdapterError`。
3. CLI 适配器使用子进程调用，应在缺失依赖时给出明确安装指引（如 `grid-intensity`、`mcp-server-chart`）。
4. 缓存与持久化逻辑保留在服务层，保证适配器无状态。

## 4. 本体与数据模型

目标实体（后续可采用 Pydantic/SQLAlchemy 建模）：

- **GRI**：`GRIStandard`、`GRIDisclosure`、`GRIIndicator`
- **SDG**：`SDGGoal`、`SDGTarget`、`SDGIndicator`
- **GHG Protocol**：`GHGScope`、`EmissionFactor`、`CalculationLogic`
- **Green Software (SCI)**：`SCIMetric`、`SCIParameter`
- **顶层分类**：`SoftwareSustainability_Longevity`、`SoftwareSustainability_Environmental`

服务层应支持将这些实体同步到图结构（NetworkX、RDF 等）以供综合分析。

## 5. CLI 路线图

| 命令 | 阶段 | 描述与当前状态 |
|------|------|----------------|
| `research map-sdg` | Phase 1 | 调用 OSDG API，与本地 SDG 本体对齐。**已实现**（需 JSON 能力 OSDG 端点/令牌）。 |
| `research find-code` | Phase 1 | 结合种子清单与 GitHub Topics。**已实现**（种子清单摄取待加入）。 |
| `research get-carbon-intensity` | Phase 1 | 调用 `grid-intensity` CLI。**已实现**（依赖 CLI 安装）。 |
| `research query-kg` | Phase 1 | 计划封装 `wdq`/`wikidata-dl` 执行 SPARQL。 |
| `research find-papers` | Phase 1 | 计划聚合 Semantic Scholar、arXiv、本地索引与 Scopus。 |
| `research map-gri` | Phase 2 | 解析报告、比对 GRI 本体，可结合 LLM 进行评分。 |
| `research synthesize` | Phase 3 | LLM 控制器按用户需求协调其它命令。 |
| `research visuals verify` | Phase 2 | 检查 AntV MCP 图表服务器可用性。**已实现**。 |

必须遵循 `tasks/blueprint.yaml` 中的依赖顺序推进功能。

## 6. 自动化指南

1. **执行上下文**：使用 `ExecutionContext.build_default()` 获取缓存路径、启用数据源、秘密信息；尊重 `dry_run` 与 `background_tasks` 选项。
2. **任务图**：实现功能前先对照 `tasks/blueprint.yaml`，确认所需前置任务已完成。
3. **Dry-Run 支持**：服务与 CLI 在 `dry_run` 模式下应返回执行计划而非真正操作。
4. **前置依赖提示**：缺少外部工具或凭据时（如 OSDG 令牌、`grid-intensity` CLI、Node.js + MCP 图表服务器）需输出明确指导，不得默默失败。

## 7. 测试策略

- 适配器测试采用 mock，隔离真实网络调用。
- 服务层测试需验证缓存及 dry-run 行为。
- CLI 测试使用 `typer.testing.CliRunner`，通过补丁替换外部依赖。
- 对规范化逻辑保持较高覆盖率，修复缺陷时引入回归测试。

## 8. 治理与演进

- 通过 `DataSourceStatus` 追踪生命周期（`active`、`trial`、`deprecated`、`blocked`）；被阻止的数据源必须给出原因。
- 上游数据更新时（如 GRI taxonomy、SDG 列表），保持版本记录并同步本地存储。
- 面向人类的说明保留在 `README.md`，自动化指令集中在 `AGENTS.md` 与本文件。
- 若新增规范，请放置于 `specs/`，确保中英双语同步。

## 9. 当前进度

- 完成注册表、执行上下文、数据源验证命令。
- Phase 1 命令 `research map-sdg`、`research find-code`、`research get-carbon-intensity` 已上线。
- `uv run pytest` 覆盖核心模块与 CLI 操作。
- 下一步重点：摄取 SDG/GRI 本体数据、完善其余 Phase 1 命令，并扩展引文/图谱工具。
