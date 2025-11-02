# TianGong 可持续发展研究 CLI

本说明面向人类使用者，概述仓库目的、安装步骤与常用命令。

## 项目概览

该仓库提供一个基于规格驱动的命令行工具，用于调研可持续性相关的标准、学术文献、代码资源与碳排数据。核心能力包括：

- 维护数据源注册表（UN SDG API、Semantic Scholar、GitHub Topics、OSDG、grid-intensity CLI 等），记录优先级、认证要求与可用功能。
- 提供基于 Typer 的命令，支持列出/验证数据源、搜索可持续性代码库、将文本映射到联合国可持续发展目标（SDG）、查询碳强度。
- 暴露适配器与服务层，将确定性的数据访问与 LLM 辅助的综合分析解耦，便于自动化代理稳定地编排研究流程。

## 🚀 快速导航

| 想要... | 请阅读... |
|--------|---------|
| **立即开始** | [QUICKSTART_CN.md](./QUICKSTART_CN.md) — 5 分钟快速配置 |
| **了解项目** | [README_CN.md](./README_CN.md) — 本页面 |
| **详细安装步骤** | [SETUP_GUIDE_CN.md](./SETUP_GUIDE_CN.md) — 平台特定指南 |
| **技术架构说明** | [specs/architecture_CN.md](./specs/architecture_CN.md) — 给开发者 |
| **English users** | [QUICKSTART.md](./QUICKSTART.md) — Quick start |

## 开始使用

### ⚡ 快速开始（一键配置）

**macOS 用户：**
```bash
bash install_macos.sh
```

**Ubuntu/Debian 用户：**
```bash
bash install_ubuntu.sh
```

这两个脚本会引导您进行交互式配置，并可选择安装额外组件。

### 前置条件

- Python 3.12 或更高版本
- 用于环境与依赖管理的 [uv](https://docs.astral.sh/uv/)
- Node.js 22+（仅在使用 AntV MCP 图表服务器时需要）
- 可选依赖（用于工作流自动导出 PDF/DOCX 报告）：
  - [Pandoc](https://pandoc.org/) 3.0+
  - 若需生成 PDF，还需安装 TeX Live 等 LaTeX 引擎

**详细的平台特定配置说明请参阅：**
- **[SETUP_GUIDE_CN.md](./SETUP_GUIDE_CN.md)** — macOS 和 Ubuntu 完整安装指南
- **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** — English version (macOS and Ubuntu complete installation guides)

### 手动安装

如果您更喜欢手动配置，请运行：

```bash
uv sync
```

### CLI 使用

CLI 可执行文件名称为 `tiangong-research`。建议通过 `uv run` 调用，确保使用受管虚拟环境：

```bash
uv run tiangong-research --help
```

常用命令示例：

- `uv run tiangong-research sources list` — 查看数据源目录。
- `uv run tiangong-research sources verify <id>` — 检查指定数据源的连通性或配置。
- `uv run tiangong-research research find-code life-cycle-assessment --limit 5 --json` — 基于 GitHub Topics 搜索生命周期评估相关的可持续性代码仓库。
- `uv run tiangong-research research map-sdg <file>` — 调用 OSDG API 将文本或 PDF 映射到 SDG（需可返回 JSON 的 OSDG 端点或令牌）。
- `uv run tiangong-research research get-carbon-intensity <location>` — 通过 `grid-intensity` CLI 查询指定地区的碳强度（需确保该 CLI 已安装在 `PATH` 中）。
- `uv run tiangong-research research visuals verify` — 检查 AntV MCP 图表服务器是否可达（需安装 Node.js 并运行 `npx -y @antv/mcp-server-chart --transport streamable`）。
- `uv run tiangong-research research workflow simple --topic "<主题>" --report-output reports/snapshot.md --chart-output visuals/snapshot.png` — 运行端到端工作流，汇总数据并生成报告与 AntV 图表。

更深入的技术架构请参阅 `specs/` 目录下的 AI 规格文档。

## 仓库结构

- `src/tiangong_ai_for_sustainability/` — 应用核心代码（上下文/注册表模块、API 适配器、服务层、CLI）。
- `specs/` — 支撑自动化代理的规格文档。
- `tests/` — 基于 pytest 的测试用例，覆盖上下文、注册表、服务与 CLI 行为。
- `tasks/blueprint.yaml` — 声明式任务依赖图，供自动化代理参考。

## 开发流程

1. 使用 `uv sync` 安装或更新依赖。
2. 在 `src/` 中实现功能，同时在 `tests/` 中添加或更新测试。
3. 提交前运行测试与质量检查，确保通过后再提交。

## 测试

运行完整测试套件：

```bash
uv run pytest
```

可选的格式化与静态检查命令：

```bash
uv run ruff check
uv run black .
```

## 图表可视化支持

若需通过 [AntV MCP 图表服务器](https://github.com/antvis/mcp-server-chart) 生成图形：

1. 安装 Node.js，并通过 `npm` 或 `npx` 获取服务器包。
2. 启动服务器，例如执行 `npx -y @antv/mcp-server-chart --transport streamable`（默认端点 `http://127.0.0.1:1122/mcp`）。
3. 如使用自定义地址，可设置环境变量 `TIANGONG_CHART_MCP_ENDPOINT` 或在 `.secrets` 文件的 `[chart_mcp] endpoint` 中配置。
4. 在执行可视化流程前使用 `uv run tiangong-research research visuals verify` 确认 CLI 已连通该服务器。
