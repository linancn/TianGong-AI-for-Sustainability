# TianGong 自动化作战手册（中文）

此文档面向在本仓库工作的 AI 代理，所有指令必须与英文版 `AGENTS.md` 保持同步更新。

## 使命概述

- 按 `specs/` 中的架构要求实现可持续性研究 CLI。
- 保持与人类使用者文档（`README.md`）一致的行为预期，但优先确保自动化流程可复现、可审计。
- 以 `specs/architecture.md` 与 `tasks/blueprint.yaml` 作为范围、模块边界与实施顺序的唯一来源。

## 必读参考

| 文档 | 路径 | 作用 |
|------|------|------|
| 架构规范 | `specs/architecture.md` | 本体、数据源优先级、CLI 路线图、执行策略。 |
| 任务图 | `tasks/blueprint.yaml` | 关键功能之间的依赖关系。 |
| 人类手册 | `README.md` | 面向终端用户的使用说明，需保持行为一致。 |
| 系统配置指南 | `SETUP_GUIDE.md` / `SETUP_GUIDE_CN.md` | 平台特定安装说明（macOS/Ubuntu）、前置条件、故障排除。 |
| 可视化服务 | `https://github.com/antvis/mcp-server-chart` | AntV MCP 图表服务器的使用说明与配置。 |
| 提示模板 | `specs/prompts/` | 可复用的研究提示模板（需维护中英双语版本）。 |
| 工作流脚本 | `tiangong_ai_for_sustainability/workflows/` | 自动化多源研究的 Python 工作流（如 `run_simple_workflow`）。 |

> **更新要求**：凡涉及上述文档内容变更，必须同时更新对应的中文与英文版本，确保双语文档一致。

## 操作原则

1. **规格优先** — 开发前校验需求是否符合 `specs/architecture.md`；若有冲突，先与人类确认。
2. **确定性优先** — 数据采集使用规则化适配器；仅在综合分析阶段引入 LLM 推理。
3. **可回滚** — 未获授权不得执行破坏性 Git 命令（如 `git reset --hard`）。
4. **双语维护** — 对 `README*.md`、`AGENTS*.md`、`specs/architecture*.md` 的任何修改，必须同步更新英文与中文版本。
5. **工具依赖** — 涉及图表的工作需确认 Node.js 与 AntV MCP 图表服务器已安装并可访问。

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
   ```

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

## 验证清单

提交前依次执行：

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
