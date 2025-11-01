# TianGong 可持续性研究 CLI 架构蓝图

本蓝图在现有项目结构基础上，综合《技术规范（第 I 部分）》的要求并进行取舍，确保：

- **R-Flex**：支持数据源的快速增补与剔除，避免硬编码耦合。
- **R-Auto**：最大化 Codex 代理的自主编排能力，提供细粒度的受控执行上下文。
- **R-Robust**：区分并协调基于 Prompt 的 LLM 能力与基于规则/协议的稳定接口，前者负责推理与综合，后者负责确定性数据获取。

## 1. 项目结构对齐

现有 `src/tiangong_ai_for_sustainability` 包保持为顶层命名空间，新增子模块以插件方式组织：

| 模块                       | 职责概述 |
|----------------------------|----------|
| `core.config`              | 统一加载配置与凭据，支持多环境覆盖。 |
| `core.registry`            | 数据源、命令、代理策略的可注册式清单。 |
| `domain.ontology`          | 建模 GRI/SDG/GHG/GSF 等基础真理层，提供版本化数据模型。 |
| `adapters.sources`         | 对各 API/XLSX/Markdown 的轻量客户端，实现幂等、可替换。 |
| `adapters.storage`         | 本地缓存、向量索引、关系/图存储接口（抽象层，便于切换 SQLite / DuckDB / Graph DB）。 |
| `services.research`        | 编排各类检索、标注、图构建逻辑；与 `deep_research` 模块协同。 |
| `cli`                      | 基于 Typer / Click 的命令入口，按任务分组暴露子命令。 |

> **取舍说明**：保持单一仓库，但通过注册表 + 依赖注入避免把《第 II 部分》所有数据源一次性实现，优先覆盖 P1 核心源，其余依据需求接入。

## 2. 设计原则

1. **模块化接入 (R-Flex)**：所有数据源通过 `DatasourcePlugin` 协议注册，包含能力声明（支持的操作、数据格式、速率限制、认证方式）。新增源只需新增子类并注册元数据。
2. **双轨执行 (R-Robust)**：面向稳定数据获取的 `RulePipeline`（REST/SPARQL/XLSX 解析）与面向推理综合的 `LLMPipeline` 并行存在，由编排层根据命令需求调度。
3. **Codex 自主编排 (R-Auto)**：提供声明式任务图（JSON/YAML），Codex 可以读取任务依赖并调用 `services.research` 的管线，不必在对话中重复硬编码步骤。
4. **可观测性**：统一日志、事件总线，记录 LLM 工具调用、缓存命中、外部 API 状态，为后续调试与审计提供基础。

## 3. 数据源策略

### 3.1 分层优先级

| 层级 | 数据源示例 | 当前决策 | 备注 |
|------|------------|----------|------|
| P1   | UN SDG API、Semantic Scholar、Wikidata、GitHub Topics、Carbon Aware SDK | **立即实现** | 涵盖核心本体 + 关键检索；全部开放 API。 |
| P1 (批量) | arXiv S3/Kaggle | **规划阶段** | 需考虑存储成本；先实现接口与索引骨架，再视资源完成落地。 |
| P2   | Scopus、Web of Science、WattTime（通过 grid-intensity-cli） | **条件接入** | 以注册表标记 `requires_key=True`，由运行环境提供密钥才启用。 |
| P3   | GRI Taxonomy XLSX、GHG XLSX、Awesome Green Software、Open Sustainable Tech CSV | **逐步接入** | 通过统一的文件解析器框架处理，保留手动刷新入口。 |
| P4   | Google Scholar、ACM DL | **明确禁用** | 在注册表中加入 `blocked_reason`，调用层遇到相同请求时返回替代建议。 |

### 3.2 接入流程

1. **源清单 (`datasources/*.yaml`)**：记录元信息（优先级、认证、刷新策略、LLM 可否访问）。Codex 在运行时解析该清单，动态决定可用源。
2. **客户端抽象**：统一 `fetch()` / `search()` / `stream()` 接口；通过 `tenacity` 重试、超时与速率限制中枢提升鲁棒性。
3. **缓存策略**：P1/P3 源默认落地 SQLite/Parquet 缓存，附带 ETag/Last-Modified 校验；P2 源因授权限制只做轻量缓存或留空。
4. **校验与监控**：执行连接测试命令 `research verify-source <id>`，明确 API 运行状况；Codex 自主运行前可先调用以避免长链路失败。

## 4. 本体与数据模型

1. **核心实体**
   - `GRIStandard` / `GRIDisclosure` / `GRIIndicator`
   - `SDGGoal` / `SDGTarget` / `SDGIndicator`
   - `GHGScope` / `EmissionFactor` / `CalculationLogic`
   - `SCIMetric` / `SCIParameter`
   - 顶层分类：`SoftwareSustainability_Longevity`、`SoftwareSustainability_Environmental`

2. **实现策略**
   - 解析器由 `adapters.sources` 提供，输出统一的 `pydantic` 模型。
   - 持久化采用 `duckdb` + `parquet`（轻量、易扩展）；后续如需图查询则同步一份到 `networkx` 或 `rdflib`。
   - 提供版本标签（例如 `gri.taxonomy.version`），允许多版本并存，便于未来标准更新。

3. **语义链接**
   - 引入 `GraphService`，将标准实体与论文、代码、实时数据节点关联。
   - 支持导出 Graphviz DOT、JSON-LD，满足规范中 `--build-network` 等需求。

## 5. CLI 命令矩阵（阶段化）

| 命令原型 | 阶段 | 说明 |
|----------|------|------|
| `research map-sdg` | Phase 1 | 使用本地 SDG 模型 + osdg.ai API（封装在 `RulePipeline`），落地 JSON 结果。 |
| `research map-gri` | Phase 2 | 构建 GRI 检索索引 + 本地 LLM 提示模板；允许 Codex 调用 `deep_research` 进行补充。 |
| `research find-papers` | Phase 1 | 组合本地 arXiv（若已落地）与 Semantic Scholar；缺失源时自动回退。 |
| `research find-code` | Phase 1 | 先查种子清单，再调用 GitHub Topics；提供 `--evade-acm` fallback。 |
| `research get-carbon-intensity` | Phase 1 | 包装 `grid-intensity-cli` 子进程，内置 JSON 解析与错误提示。 |
| `research query-kg` | Phase 1 | 调用 `wdq`/`wikidata-dl`，若未安装则输出安装指引。 |
| `research synthesize` | Phase 3 | 通过任务图调度各命令，LLM 负责计划生成与总结。 |

> **权衡**：先保障 Phase 1 命令的端到端闭环，满足核心用例；Phase 2 执行复杂解析（GRI/GHG）；Phase 3 引入跨命令编排与报告生成功能。

> **当前进展**：已实现数据源注册/验证框架，并交付 Phase 1 命令：`research get-carbon-intensity`、`research find-code`、`research map-sdg`（需可用的 OSDG API）。缺失的 CLI 工具或 API 凭据会给出安装/配置提示。

## 6. Codex 自主执行策略

1. **任务图 (`tasks/blueprint.yaml`)**：列出命令依赖（如 `map-gri` 依赖 `ontology.gri`、`pdf.extractor`），Codex 可通过读取任务图决定先执行哪些准备步骤。
2. **执行上下文**：引入 `ExecutionContext` 对象，持有启用的数据源、缓存目录、活跃代理等；Codex 可在单次对话中共享。
3. **调试模式**：允许 `--dry-run` 模式输出计划而不执行，便于 Codex 预演。
4. **LLM Guardrails**：为 `LLMPipeline` 提供结构化 Prompt 模板，嵌入所有关键定义（R1.1-R1.4），确保输出始终对齐规范。

## 7. LLM 与规则协同

| 场景 | 首选管线 | 备选/协同 |
|------|----------|-----------|
| 结构化指标抓取（SDG 列表、GRI Taxonomy 元数据） | `RulePipeline`（API/XLSX） | LLM 仅用于解析失败时的语义补救。 |
| 非结构化报告映射（map-gri） | `LLMPipeline`（本地/远程 LLM） | 使用 `RulePipeline` 预先提取报告文本，提供上下文片段。 |
| 引用网络构建 | `RulePipeline` 调用 Semantic Scholar/Scopus | LLM 用于总结网络结构、建议后续探索。 |
| 跨域综合（synthesize） | `LLMPipeline` 作为调度器 | 通过命令执行结果的结构化日志（JSON）保持可验证性。 |

## 8. 演进与治理

1. **源生命周期管理**：每个数据源在注册表中声明 `status`（active/deprecated/trial），支持通过 CLI `research sources list` 检视。
2. **配置热加载**：`core.config` 支持环境变量 + TOML 合并，Codex 可在运行时切换不同配置（例如仅启用离线源）。
3. **测试策略**：为解析器与客户端编写契约测试，使用存根数据（XLSX/JSON Fixtures）；LLM 相关逻辑使用 `golden answer` + `jsonschema` 验证。
4. **安全与凭据**：沿用 `.secrets/` 体系，并提供 `secrets template` 命令生成示例配置。

## 9. 实施路线（建议）

1. **Phase 0**：落地注册表骨架、配置系统、命令行框架；实现 `research sources list/verify` 以验证环境。
2. **Phase 1**：实现 P1 数据源适配器与基础命令（map-sdg、find-code、get-carbon-intensity、query-kg）。构建 SDG/GRI/GSF 基本本体。
3. **Phase 2**：引入 XLSX 解析（GRI/GHG）、arXiv 批量索引、Scopus 及种子清单解析。完成 map-gri 与 find-papers `--build-network`。
4. **Phase 3**：实现跨命令综合（synthesize）、Graph 导出、LLM 自主任务图执行，扩展实时数据与政府数据源客户端。

该路线兼顾规范严谨性与实现成本，确保在任一阶段都可直接为 Codex 自主调研提供可靠工具链。
