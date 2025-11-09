# TianGong 自动化作战手册（中文）

此文档面向在本仓库工作的 AI 代理，所有指令必须与英文版 `AGENTS.md` 保持同步更新。

## 使命概述

- 按下文的架构蓝图实现可持续性研究 CLI。
- 保持与人类使用者文档（`README.md`）一致的行为预期，但优先确保自动化流程可复现、可审计。
- 以本文档中的“架构蓝图”章节与 `tasks/blueprint.yaml` 作为范围、模块边界与实施顺序的唯一来源。

## 必读参考

| 文档 | 路径 | 作用 |
|------|------|------|
| 架构蓝图 | `AGENTS_CN.md`（本文档） | 本体、数据源优先级、CLI 路线图、执行策略。 |
| 任务图 | `tasks/blueprint.yaml` | 关键功能之间的依赖关系。 |
| 待办登记 | `tasks/backlog.yaml` | 将研究缺口映射到确定性适配器与提示包的跟踪清单。 |
| 人类手册 | `README.md` | 面向终端用户的使用说明，需保持行为一致。 |
| 系统配置指南 | `SETUP_GUIDE.md` / `SETUP_GUIDE_CN.md` | 平台特定安装说明（macOS/Ubuntu）、前置条件、故障排除。 |
| 可视化服务 | `https://github.com/antvis/mcp-server-chart` | AntV MCP 图表服务器的使用说明与配置。 |
| 提示模板（AI） | `specs/prompts/default.md` | 仅供 Codex 使用的英文提示模版。 |
| 提示模板（人工中文） | `specs/prompts/default_CN.md` | 面向人类操作员的中文翻译，禁止直接发送给 Codex。 |
| 工作流脚本 | `tiangong_ai_for_sustainability/workflows/` | 自动化多源研究的 Python 工作流（如 `run_simple_workflow`）。 |
| 课题工作区指南 | `WORKSPACES_CN.md` | 在 `.cache/tiangong/<STUDY_ID>/` 中执行研究工作时的流程与规范。 |

> **更新要求**：凡涉及上述文档内容变更，必须同时更新对应的中文与英文版本，确保双语文档一致。

### 文档分工

- **AGENTS_CN.md / AGENTS.md**：仓库层面的架构、模块边界、开发规范。
- **WORKSPACES_CN.md / WORKSPACES.md**：课题工作区的执行规则与产物管理。
- **specs/prompts/default*.md**：提交给 Codex 的调研提示骨架，绑定 runbook 与工作区 artefacts。

## 操作原则

1. **规格优先** — 开发前校验需求是否符合下文的架构蓝图；若有冲突，先与人类确认。
2. **确定性优先** — 数据采集使用规则化适配器；仅在综合分析阶段引入 LLM 推理。
3. **CLI 优先** — 优先调用 `uv run tiangong-research …` 子命令；仅在确认 CLI 尚未覆盖能力时，记录原因并说明拟访问的 Python 模块，同时创建待办以补全 CLI。
4. **可回滚** — 未获授权不得执行破坏性 Git 命令（如 `git reset --hard`）。
5. **双语维护** — 对 `README*.md`、`AGENTS*.md`、`WORKSPACES*.md`、`SETUP_GUIDE*.md`（包括架构蓝图章节）的任何修改，必须同步更新英文与中文版本。
6. **工具依赖** — 涉及图表的工作需确认 Node.js 与 AntV MCP 图表服务器已安装并可访问。
7. **提示模版** — 所有包含 LLM 的工作流（如 Deep Research、`research synthesize`）需通过别名加载 `specs/prompts/default.md`（支持 `default`、`default-en` 等别名）；模版保持英文内容以避免多语言提示漂移。`specs/prompts/default_CN.md` 仅供人工参考，禁止直接发送给 Codex。模版占位符使用 `{{variable}}` 语法，并可通过 CLI 参数（`--prompt-template`、`--prompt-language`、`--prompt-variable`）填充，确保执行可复现。
8. **课题工作区** — 在 `.cache/tiangong/<STUDY_ID>/` 内执行研究工作时，请遵循 `WORKSPACES_CN.md` 的操作规范；课题脚本、笔记和中间产物必须保存在工作区内，不得提交到仓库。

## 架构蓝图

### 对齐原则

- **R-Flex（灵活的数据编排）**：数据源必须可插拔。通过注册表声明优先级、认证方式与功能标签，便于新增或退役数据源而不修改核心代码。
- **R-Auto（代理自治）**：提供结构化的执行上下文、任务图与服务接口，使 Codex 等代理可在无人工干预的情况下规划并执行工作。
- **R-Robust（稳健的确定性基础）**：数据获取和解析依赖确定性适配器；LLM 推理仅在综合或歧义处理阶段使用。

### 模块职责

| 模块 | 作用 |
|------|------|
| `core.config` / `core.context` / `core.registry` | 管理秘密信息、执行上下文与数据源注册表。 |
| `adapters.api` / `adapters.environment` / `adapters.storage` | 提供确定性 API、CLI、存储访问层，返回结构化结果与验证信息。 |
| `services.research` | 在执行上下文内组合适配器（缓存、令牌查找、dry-run 处理）。 |
| `cli` | 基于 Typer 的命令行入口，与架构路线图保持一致。 |
| `domain.*`（规划中） | 存放 GRI/SDG/GHG/LCA 等本体模型。 |

> **实施提示**：扩展功能时先更新注册表和适配器，再开放服务与 CLI。这有助于保持自动化流程可预测。

### 数据源策略

#### 优先级矩阵

| 优先级 | 示例 | 状态 | 说明 |
|--------|------|------|------|
| **P0** | IPCC DDC；IPBES；世界银行（SDGs/WGI/ESG）；ILOSTAT；IMF 气候仪表板；透明国际 CPI；UN SDG API；Wikidata | 部分上线 | 气候、生物多样性、治理等权威宏观基线，作为确定性推理的“公理层”。 |
| **P1** | Google Earth Engine；ESA Copernicus；NASA Earthdata；grid-intensity CLI | 部分上线 | 遥感与观测验证层，用于佐证披露信息。已实现 Copernicus Dataspace 与 NASA Earthdata 元数据适配器，并提供 grid-intensity 与 Earth Engine CLI 可用性检测；需要凭据的完整流程仍在路线图中。 |
| **P2** | OpenAlex；Dimensions.ai；Lens.org；Semantic Scholar；Crossref；arXiv；GitHub Topics；Kaggle API；OSDG API | 已实现 | 文献计量与分类管线，支撑研究发现与代码检索。 |
| **P3** | CDP；LSEG Refinitiv；MSCI；Sustainalytics；S&P Global Sustainable1；ISS ESG | 规划中 | 需要许可的企业 ESG 绩效数据，凭证就绪后接入。 |
| **P4** | GRI Taxonomy（XBRL）；GHG 工作簿；Open Supply Hub；`tiangong_lca_remote` MCP；Tavily Web MCP | 持续接入 | 回溯企业披露与供应链节点，用于反哺 P3 分析结果。 |
| **P5** | ACM Digital Library；Scopus；Web of Science；AntV MCP 图表服务器；OpenAI Deep Research | 视凭据启用 | 高门槛/可选服务，满足依赖后用于专家级综合与可视化。 |
| **P_INT** | `tiangong_ai_remote` MCP；`dify_knowledge_base_mcp` | 已实现 | 项目专属的 RAG 上下文层，为自动化提供最终背景。 |

#### 适配器规则

1. 数据源元数据需登记在 `resources/datasources/*.yaml`。
2. HTTP 适配器使用 `httpx` + Tenacity 重试，失败时抛出 `AdapterError`。
3. CLI/MCP 适配器在缺失依赖或访问权限时，应给出明确安装/开通指引（如 `grid-intensity`、`mcp-server-chart --transport streamable`、MCP 端点或密钥）。
4. 缓存与持久化逻辑保留在服务层，保证适配器无状态。
5. Kaggle 数据集适配器依赖官方 SDK（1.7.4.5 版）；若缺少 `KAGGLE_USERNAME`/`KAGGLE_KEY` 或 `~/.kaggle/kaggle.json`，需输出明确的凭证配置提示。

> **MCP 使用提示**：`tiangong_ai_remote` 与 `dify_knowledge_base_mcp` 属于 **P_INT** RAG 上下文层，查询时需提供完整的任务意图，以便混合检索返回高价值片段。所有 `Search_*` 工具（包括 `Search_Sci_Tool`）都会返回 JSON 字符串，需先通过 `json.loads` 解析，并将 `topK` 控制在 50 以内以避免响应过大。补充检索（如 Semantic Scholar）需注意 429 节流；出现限频时可降速或改用 `OpenAlex` 数据。`tiangong_lca_remote` MCP（P4）聚焦生命周期评估，适用于微观 LCA 案例或精细排放比对；宏观文献扫描场景应优先使用 P0/P2 数据源。若需涵盖更广泛的网站或新闻，可启用 `tavily_web_mcp`（P4，需要 `Authorization: Bearer <API_KEY>`）。`openai_deep_research`（P5）用于确定性证据收集后的综合分析，请提前配置 OpenAI API Key 与 deep_research 模型。

### 本体与数据模型

目标实体（后续可采用 Pydantic/SQLAlchemy 建模）：

- **GRI**：`GRIStandard`、`GRIDisclosure`、`GRIIndicator`
- **SDG**：`SDGGoal`、`SDGTarget`、`SDGIndicator`
- **GHG Protocol**：`GHGScope`、`EmissionFactor`、`CalculationLogic`
- **生命周期评估 (LCA)**：`LCAScenario`、`LCAImpactCategory`
- **顶层分类**：`SoftwareSustainability_Longevity`、`SoftwareSustainability_Environmental`

服务层应支持将这些实体同步到图结构（NetworkX、RDF 等）以供综合分析。

### CLI 路线图

| 命令 | 阶段 | 描述与当前状态 |
|------|------|----------------|
| `research map-sdg` | Phase 1 | 调用 OSDG API，与本地 SDG 本体对齐。**已实现**（需 JSON 能力 OSDG 端点/令牌）。 |
| `research find-code` | Phase 1 | 结合种子清单与 GitHub Topics。**已实现**（种子清单摄取待加入）。 |
| `research get-carbon-intensity` | Phase 1 | 调用 `grid-intensity` CLI。**已实现**（依赖 CLI 安装）。 |
| `research query-kg` | Phase 1 | 计划封装 `wdq`/`wikidata-dl` 执行 SPARQL。 |
| `research find-papers` | Phase 1 | 聚合 Semantic Scholar 与（可选）OpenAlex 数据，并支持 `--limit`、`--citation-graph` 等参数。**已实现**。 |
| `research map-gri` | Phase 2 | 解析报告、比对 GRI 本体，可结合 LLM 进行评分。 |
| `research synthesize` | Phase 3 | LLM 控制器按用户需求协调其它命令。**已实现**（支持提示模版）。 |
| `research visuals verify` | Phase 2 | 检查 AntV MCP 图表服务器可用性。**已实现**。 |
| `research workflow simple` | Phase 2 | 自动化执行 SDG 匹配、代码/文献检索、碳强度采集与 AntV 图表生成。**已实现**。 |
| `research workflow citation-scan --profile <slug>` | Phase 2 | 基于 Profile 的确定性引文模版（默认 `lca`）。**已实现**。 |
| `research workflow deep-report --profile <slug>` | Phase 3 | 在引文模版上叠加 Deep Research 综合；当前默认 profile 为 LCA，可扩展到其它领域。**已实现**。 |

功能推进必须遵循 `tasks/blueprint.yaml` 中的依赖顺序。

### 自动化指南

1. **执行上下文**：使用 `ExecutionContext.build_default()` 获取缓存路径、启用数据源、秘密信息；尊重 `dry_run` 与 `background_tasks` 选项。
2. **任务图**：实现功能前先对照 `tasks/blueprint.yaml`，确认所需前置任务已完成。
3. **Dry-Run 支持**：服务与 CLI 在 `dry_run` 模式下应返回执行计划而非真正操作。
4. **前置依赖提示**：缺少外部工具或凭据时（如 OSDG 令牌、`grid-intensity` CLI、Node.js + MCP 图表服务器）需输出明确指导，不得默默失败。
5. **提示模版配置**：当命令未显式提供指令时，应通过 `ResearchServices.load_prompt_template` 加载 `specs/prompts/default.md`。模版支持 `{{placeholder}}` 占位符替换（来自 `ExecutionOptions.prompt_variables`），CLI 可通过 `--prompt-template`、`--prompt-language`、`--prompt-variable` 设定参数，后续 `research synthesize` 亦复用相同机制。中文文件 `specs/prompts/default_CN.md` 仅供人工阅读，请勿传递给 Codex。
6. **工作流 Profile**：引用扫描与深度报告工作流均采用“模版 + Profile”架构。新增领域时只需在 `workflows/profiles.py` 注册 `CitationProfile`/`DeepResearchProfile`，然后通过 `--profile <slug>` 复用现有 CLI。 
7. **课题工作区规范**：课题专用的脚本、笔记、临时数据集和草稿必须存放在 `.cache/tiangong/<STUDY_ID>/` 及其下属目录（`acquisition/`、`processed/`、`docs/`、`models/`、`figures/`、`scripts/`、`logs/`）。仓库层面仅接受通用能力（CLI、services、workflows），不得将特定课题的代码或数据提交到仓库。
8. **Runbook 真源**：所有命令队列、产出路径与重试策略须写入 `<study>/docs/runbook.md`。执行时严格按照 runbook 顺序推进，临时操作需先更新 runbook 再执行。
9. **流程与溯源**：在 `<study>/processed/` 记录流水线清单、指标表和参考索引，deliverable 中必须引用这些确定性产物，确保可复现。
10. **异常记录**：遭遇速率限制、凭据缺失或降级处理时，先在 `<study>/logs/exceptions.md` 记录情况，并在 `docs/gaps.md` 总结，再决定是否重试或切换数据源，避免在脚本中写死一次性逻辑。

### 测试策略

- 适配器测试采用 mock，隔离真实网络调用。
- 服务层测试需验证缓存及 dry-run 行为。
- CLI 测试使用 `typer.testing.CliRunner`，通过补丁替换外部依赖。
- 对规范化逻辑保持较高覆盖率，修复缺陷时引入回归测试。

### 治理与演进

- 通过 `DataSourceStatus` 追踪生命周期（`active`、`trial`、`deprecated`、`blocked`）；被阻止的数据源必须给出原因。
- 上游数据更新时（如 GRI taxonomy、SDG 列表），保持版本记录并同步本地存储。
- 面向人类的说明保留在 `README.md`，自动化指令集中在本文档。
- 若扩展架构内容，请在本章节中记录，确保 AI 协作者有统一的真源。

### 当前进度

- 已完成注册表、执行上下文与数据源验证命令。
- Phase 1 命令 `research map-sdg`、`research find-code`、`research get-carbon-intensity` 已上线。
- Phase 1 命令 `research find-papers` 已可用，可汇总 Semantic Scholar 结果并按需启用 OpenAlex/Citation Graph 输出。
- P1 遥感数据现已覆盖 Copernicus Dataspace、NASA Earthdata 元数据适配器，并加入 Earth Engine CLI 可用性检测，便于提示安装与认证步骤。
- `uv run pytest` 覆盖核心模块与 CLI 操作。
- Phase 3 的 `research synthesize` 已上线，并支持提示模版驱动的 LLM 综合分析。
- 下一步重点：摄取 SDG/GRI 本体数据、完善其余 Phase 1 命令，并扩展引文/图谱工具。

## 环境与系统要求

执行自动化任务前，需验证部署环境满足以下条件：

### 核心要求（强制）
- **Python 3.12+** — 用 `python3 --version` 验证（所有操作必需）
- **uv 包管理器** — 用 `uv --version` 验证（依赖管理必需）
- **Git** — 用 `git --version` 验证（仓库操作必需）

### 运行时依赖（按功能划分）
| 功能 | 依赖 | 检查命令 | 影响 |
|------|------|---------|------|
| 图表可视化 | Node.js 22+ | `node --version` | AntV MCP 图表服务器必需 |
| PDF/DOCX 导出 | Pandoc 3.0+ | `pandoc --version` | 报告格式转换必需 |
| PDF 生成 | LaTeX (TeX Live) | `pdflatex --version` | 需要 PDF 输出时必需 |
| 碳排指标 | `grid-intensity` CLI | `grid-intensity --help` | 碳强度查询必需 |

### AI 智能体的环境配置

1. **激活项目环境**：所有命令必须通过 `uv run` 执行以确保使用受管虚拟环境：
   ```bash
   uv run <command>
   ```

2. **验证数据源**：工作流执行前检查数据源可用性：
   ```bash
   uv run tiangong-research sources list
   uv run tiangong-research sources verify <source_id>
   uv run tiangong-research sources verify all
   uv run tiangong-research sources audit [--json] [--show-blocked] [--no-fail-on-error]
   ```
   - `--json`：以 JSON 形式输出巡检汇总，便于 CI 或后续解析。
   - `--show-blocked`：在报告中包含注册表中标记为 `blocked` 的数据源，便于人工复核封禁原因。
   - `--no-fail-on-error`：即使存在失败也返回 0，适用于探索性巡检或希望持续执行后续步骤的场景。

3. **检查可选功能**：检测已安装的可选依赖：
   ```bash
   # 图表支持
   npx -y @antv/mcp-server-chart --transport streamable --version

   # PDF 支持
   pandoc --version && pdflatex --version

   # 碳排指标
   grid-intensity --help
   ```

4. **配置文件**：按优先级顺序加载配置（优先级从高到低）：
   - 环境变量（如 `TIANGONG_CHART_MCP_ENDPOINT`、API 密钥）
   - `.secrets/secrets.toml` — 密钥包（API 密钥、认证令牌）
   - `.env` — 本地环境覆盖
   - `config.py` — 默认应用设置

5. **自动化配置**：使用提供的安装脚本确保环境一致性配置：
   - **macOS**: `bash install_macos.sh --full`（安装所有可选组件）
   - **Ubuntu**: `bash install_ubuntu.sh --full`（安装所有可选组件）

### 执行上下文

所有操作必须尊重 `ExecutionContext` 设置：
- **enabled_sources**: 可用的数据源集合
- **dry_run**: 规划模式（无副作用，如不调用外部 API）
- **background_tasks**: 异步/延迟操作支持
- **cache_dir**: 结果本地缓存目录

### 可观测性与日志

- 统一通过 `tiangong_ai_for_sustainability.core.logging.get_logger` 或 `ExecutionContext.get_logger` 获取记录器，确保日志格式和标签一致。
- 使用 `extra` 参数传递结构化上下文，避免将 JSON 直接拼接进消息字符串，从而保持日志可解析、可复现。
- 通过环境变量 `TIANGONG_LOG_LEVEL`（默认 `INFO`）调整日志级别；排查问题时可以升至 `DEBUG`，批量任务需要静默时可降至 `WARNING`。
- 当自动化任务需要溯源时，可在 `ExecutionOptions.observability_tags` 中写入计划标识，以便后续关联日志。

### 优雅降级

当可选依赖不可用时：
- **图表**：若 AntV 服务器不可达，工作流应以纯文本输出完成
- **PDF 导出**：若 Pandoc/LaTeX 缺失，降级为 Markdown 或 JSON 输出
- **碳排指标**：若 `grid-intensity` 不可用，工作流应跳过碳计算
- **速率限制**：实现指数退避和检查点机制

## 开发流程

1. 当锁文件变化时执行 `uv sync`。
2. 编写或更新测试，保持覆盖率。
3. 按模块划分提交内容（`core`、`adapters`、`services`、`cli` 等）。
4. 使用注册表与执行上下文暴露配置需求（包括 MCP 端点），严禁硬编码秘密信息。
5. 执行可视化任务前，需启动 `npx -y @antv/mcp-server-chart --transport streamable` 并在 `.secrets` 的 `[chart_mcp] endpoint` 或环境变量 `TIANGONG_CHART_MCP_ENDPOINT` 中记录端点。
6. 扩展自动化流程时，可复用或扩展 `workflows/simple.py`，并同步更新测试用例。
7. 为新增的服务与工作流接入集中式日志工具，并在日志行为影响功能时补充回归测试。
8. 通用脚本统一放在 `scripts/ops/`、`scripts/integrations/`、`scripts/tooling/`、`scripts/examples/` 下；课题专属脚本应保存在 `.cache/tiangong/<STUDY_ID>/scripts/`，详细要求见 `WORKSPACES_CN.md`。

## 验证清单

每次修改程序后，必须依次执行：

```bash
uv run black .
uv run ruff check
uv run pytest
```

若修改或新增 Python 模块，还需确保编译通过：

```bash
uv run python -m compileall src scripts
```

## 沟通准则

- 汇报更改时引用具体文件与行号。
- 说明残余风险（外部依赖、凭据缺失、沙箱限制等）。
- 若因环境缺陷无法继续（如缺少 `grid-intensity` CLI 或 OSDG API 令牌），明确指出所需前置条件。

保持与英文版一致是强制要求，如内容存在差异，请立即同步。
